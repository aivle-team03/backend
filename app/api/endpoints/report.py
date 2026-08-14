import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from typing import Optional

from app.db.db import get_db
from app.crud.auth import get_current_user
from app.models import User
from app.utils.s3_utils_report import generate_presigned_url
from app.schemas.report import (
    ReportCreateRequest,
    ReportUpdateRequest,
    ReportDetailResponse,
    ReportListResponse
)
from app.crud.report import (
    create_report, get_reports, get_report_by_id, update_report, delete_report, build_history_column,
    create_report_path,create_sub_report_path, build_board_column,create_sub_report
)
from app.crud.notification import create_notification

router = APIRouter()
REPORT_AGENT_URL = os.getenv("REPORT_AGENT_URL", "http://127.0.0.1:8004").rstrip("/")


@router.post("", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
def post_create_report(
    req: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """선택한 이벤트, 점검 이력, 조치 이력을 기반으로 보고서 생성 API"""
    try:
        report = create_report(
            db=db,
            company_id=current_user.company_id,
            uid=current_user.uid,
            writer=current_user.name,
            content=req.content,
            event_ids=req.event_ids,
            inspection_history_ids=getattr(req, "inspection_history_ids", None),
            action_history_ids=req.action_history_ids,
        )
        
        create_notification(
            db=db,
            company_id=current_user.company_id,
            category="complete",
            title="보고서 생성 완료",
            message=f"'{getattr(report, 'title', '안전 보고서')}' 생성이 완료되었습니다.",
            path="/report",
            user_id=current_user.uid,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return report

@router.get("", response_model=ReportListResponse)
def read_reports(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    writer: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """보고서 목록 조회 API"""
    total, items = get_reports(
        db=db, company_id=current_user.company_id, page=page, size=size, start_date=start_date,
        end_date=end_date, writer=writer, keyword=keyword
    )
        
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }

@router.get("/{report_id}", response_model=ReportDetailResponse)
def read_report_detail(report_id: int = Path(..., ge=1), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """보고서 상세 조회 API"""
    r = get_report_by_id(db, report_id=report_id, company_id=current_user.company_id)
    if not r:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
        
    return r

@router.put("/{report_id}", response_model=ReportDetailResponse)
def put_update_report(
    req: ReportUpdateRequest,
    report_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """보고서 제목 수정 API"""
    r = update_report(
        db,
        report_id=report_id,
        uid=current_user.uid,
        company_id=current_user.company_id,
        title=req.title
    )
    if not r:
        raise HTTPException(status_code=403, detail="보고서가 존재하지 않거나 수정 권한이 없습니다.")
        
    return r

@router.delete("/{report_id}")
def delete_report_endpoint(
    report_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """보고서 삭제 API"""
    success = delete_report(db, report_id=report_id, uid=current_user.uid, company_id=current_user.company_id)
    if not success:
        raise HTTPException(status_code=403, detail="보고서가 존재하지 않거나 삭제 권한이 없습니다.")
    return {"message": "보고서가 성공적으로 삭제되었습니다."}

@router.get("/{report_id}/download")
def download_report_pdf(
    report_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """보고서를 PDF 형태로 다운로드 API"""
    r = get_report_by_id(db, report_id=report_id, company_id=current_user.company_id)
    if not r:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    pdf_content = (
        f"%PDF-1.4\n1 0 obj\n<< /Title (Safety Report {r.report_id}) /Author (AIVLE Team 03) >>\nendobj\n"
        f"Title:\n{r.title}\nPath:\n{r.path}\nCreated At:\n{r.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    ).encode("utf-8")

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=safety_report_{report_id}.pdf"}
    )



@router.get("/{report_id}/file-url")
def read_report_file_url(
    report_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """보고서에 저장된 S3 파일의 다운로드 URL 발급 API"""
    r = get_report_by_id(db, report_id=report_id, company_id=current_user.company_id)
    if not r:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    if r.path.startswith("s3://"):
        s3_key = r.path[len("s3://"):].split("/", 1)[1]
    else:
        s3_key = r.path

    file_url = generate_presigned_url(s3_key)
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="파일 URL을 생성할 수 없습니다. S3 설정을 확인해주세요."
        )

    return {"report_id": r.report_id, "file_url": file_url}


@router.post("/risk-assessment/form/generate")
async def post_generate_risk_assessment_form(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """위험성평가표 자동 생성 API - report_agent에 생성을 요청하고 결과를 Report 테이블에 저장한다."""
    history_column = build_history_column(db, current_user.uid)
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{REPORT_AGENT_URL}/api/report/risk-assessment/form/generate", json=history_column)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"위험성평가표 생성 서비스에 연결할 수 없습니다: {e}"
        )

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"위험성평가표 생성 서비스가 요청을 거부했습니다 (status={resp.status_code})."
        )

    result = resp.json()
    s3_output_path = result.get("s3_output_path")
    if s3_output_path:
        create_report_path(
            db,
            uid=current_user.uid,
            company_id=current_user.company_id,
            s3_output_path=s3_output_path,
        )

    for daily_upload in result.get("daily_uploads") or []:
        daily_docx_path = daily_upload.get("s3_docx_output_path")
        if daily_docx_path:
            docx_filename = daily_docx_path.rsplit("/", 1)[-1]
            create_report_path(
                db,
                uid=current_user.uid,
                company_id=current_user.company_id,
                s3_output_path=daily_docx_path,
                summary=f"{docx_filename}",
            )

        daily_json_path = daily_upload.get("s3_json_output_path")
        if daily_json_path:
            create_sub_report_path(
                db,
                company_id=current_user.company_id,
                path=daily_json_path,
                date=datetime.strptime(daily_upload["date"], "%Y-%m-%d"),
            )
    
    create_notification(
        db=db,
        company_id=current_user.company_id,
        category="complete",
        title="위험성평가표 생성 완료",
        message="요청하신 위험성평가표 생성이 완료되었습니다.",
        path="/report",
        user_id=current_user.uid,
    )

    return result



@router.post("/worker-feedback/generate")
async def post_generate_worker_feedback_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """근로자 피드백 개선 보고서 자동 생성 API - report_agent에 생성을 요청하고 결과를 Report 테이블에 저장한다."""
    board_column = build_board_column(db, current_user.uid)
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{REPORT_AGENT_URL}/api/report/worker-feedback/generate", json=board_column)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"근로자 피드백 보고서 생성 서비스에 연결할 수 없습니다: {e}"
        )

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"근로자 피드백 보고서 생성 서비스가 요청을 거부했습니다 (status={resp.status_code})."
        )

    result = resp.json()
    for s3_path in result.get("s3_output_paths") or []:
        filename = s3_path.rsplit("/", 1)[-1]
        create_report_path(
            db,
            uid=current_user.uid,
            company_id=current_user.company_id,
            s3_output_path=s3_path,
            summary=f"{filename}",
        )
        
    create_notification(
        db=db,
        company_id=current_user.company_id,
        category="complete",
        title="근로자 피드백 보고서 생성 완료",
        message="근로자 피드백 개선 보고서 생성이 완료되었습니다.",
        path="/report",
        user_id=current_user.uid,
    )

    return result

#경영책임자 지시 보고서
@router.post("/management-review-order/generate")
async def post_generate_management_review_order(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """경영책임자 검토 지시서 자동 생성 API - report_agent에 생성을 요청한다."""
    sub_reports = create_sub_report(db, start_date, end_date)

    final_history_rows = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for sub_report in sub_reports:
            if sub_report.path.startswith("s3://"):
                s3_key = sub_report.path[len("s3://"):].split("/", 1)[1]
            else:
                s3_key = sub_report.path

            file_url = generate_presigned_url(s3_key)
            if not file_url:
                continue

            file_resp = await client.get(file_url)
            if file_resp.status_code != status.HTTP_200_OK:
                continue

            daily_payload = file_resp.json()
            final_history_rows.extend(daily_payload.get("final_history_rows") or [])

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{REPORT_AGENT_URL}/api/report/management-review-order/generate",
                json={
                    "start_date": start_date,
                    "end_date": end_date,
                    "final_history_rows": final_history_rows,
                },
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"경영책임자 검토 지시서 생성 서비스에 연결할 수 없습니다: {e}"
        )

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"경영책임자 검토 지시서 생성 서비스가 요청을 거부했습니다 (status={resp.status_code})."
        )
    result = resp.json()
    s3_output_path = result.get("s3_output_path")
    if s3_output_path:
        filename = s3_output_path.rsplit("/", 1)[-1]
        create_report_path(
            db,
            uid=current_user.uid,
            company_id=current_user.company_id,
            s3_output_path=s3_output_path,
            summary=f"{filename}",
        )
        
    create_notification(
        db=db,
        company_id=current_user.company_id,
        category="complete",
        title="검토 지시서 생성 완료",
        message="경영책임자 검토 지시서 생성이 완료되었습니다.",
        path="/report",
        user_id=current_user.uid,
    )
    
    return result


#위험성평가 보고서
@router.post("/risk-assessment/report/generate")
async def post_generate_risk_assessment_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """위험성평가 보고서 자동 생성 API - report_agent에 생성을 요청한다."""
    sub_reports = create_sub_report(db, start_date, end_date)

    final_history_rows = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for sub_report in sub_reports:
            if sub_report.path.startswith("s3://"):
                s3_key = sub_report.path[len("s3://"):].split("/", 1)[1]
            else:
                s3_key = sub_report.path

            file_url = generate_presigned_url(s3_key)
            if not file_url:
                continue

            file_resp = await client.get(file_url)
            if file_resp.status_code != status.HTTP_200_OK:
                continue

            daily_payload = file_resp.json()
            final_history_rows.extend(daily_payload.get("final_history_rows") or [])

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{REPORT_AGENT_URL}/api/report/risk-assessment/report/generate",
                json={
                    "start_date": start_date,
                    "end_date": end_date,
                    "final_history_rows": final_history_rows,
                },
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"위험성평가 보고서 생성 서비스에 연결할 수 없습니다: {e}"
        )

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"위험성평가 보고서 생성 서비스가 요청을 거부했습니다 (status={resp.status_code})."
        )

    result = resp.json()
    s3_output_path = result.get("s3_output_path")
    if s3_output_path:
            filename = s3_output_path.rsplit("/", 1)[-1]
            create_report_path(
                db,
                uid=current_user.uid,
                company_id=current_user.company_id,
                s3_output_path=s3_output_path,
                summary=f"{filename}",
            )
            
    create_notification(
        db=db,
        company_id=current_user.company_id,
        category="complete",
        title="위험성평가 보고서 생성 완료",
        message="위험성평가 보고서 생성이 완료되었습니다.",
        path="/report",
        user_id=current_user.uid,
    )        
    
    return result

