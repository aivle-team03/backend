import os
from datetime import datetime
import traceback

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
    """위험성평가표 자동 생성 API - 정밀 디버깅 로깅 포함"""
    print("\n" + "=" * 60)
    print(f"🚀 [위험성평가표 생성 시작] User UID: {current_user.uid}")

    # 1. 히스토리 데이터 빌드
    try:
        history_column = build_history_column(db, current_user.uid)
        row_count = len(history_column.get("final_history_rows", []))
        print(f"👉 [1] history_column 생성 완료: 총 {row_count}건 데이터")
    except Exception as e:
        print(f"❌ [1-ERROR] history_column 빌드 실패: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"히스토리 데이터 추출 중 오류: {e}"
        )

    # 2. 에이전트 요청
    target_url = f"{REPORT_AGENT_URL}/api/report/risk-assessment/form/generate"
    print(f"👉 [2] 에이전트 요청 URL: {target_url}")

    resp = None
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(target_url, json=history_column)
            print(f"👉 [3] 에이전트 응답 코드: {resp.status_code}")
    except httpx.ConnectError as e:
        print(
            f"❌ [2-ERROR] 에이전트 연결 실패 (서버 꺼짐 또는 포트 막힘): {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Report Agent({REPORT_AGENT_URL})에 연결할 수 없습니다. 에이전트 프로세스가 켜져 있는지 확인하세요. Error: {e}",
        )
    except httpx.TimeoutException as e:
        print(f"❌ [2-ERROR] 에이전트 응답 시간 초과 (Timeout 300s): {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Report Agent 처리 시간이 300초를 초과했습니다. Error: {e}",
        )
    except Exception as e:
        print(f"❌ [2-ERROR] 에이전트 요청 중 기타 HTTP 예외: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"위험성평가표 생성 서비스 통신 에러: {e}",
        )

    # 에이전트가 200이 아닌 코드를 반환한 경우 (예: 500 내부 에러)
    if resp.status_code != status.HTTP_200_OK:
        print(f"❌ [3-ERROR] 에이전트 비정상 응답 본문:\n{resp.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"위험성평가표 생성 서비스 오류 (status={resp.status_code}): {resp.text[:300]}",
        )

    # 3. 응답 파싱
    try:
        result = resp.json()
        print(
            f"👉 [4] 에이전트 응답 파싱 성공 (status={result.get('status', 'N/A')})"
        )
    except Exception as e:
        print(f"❌ [4-ERROR] JSON 파싱 실패: {resp.text}")
        raise HTTPException(
            status_code=502, detail="에이전트 응답이 유효한 JSON이 아닙니다."
        )

    # 4. DB 저장 처리 (트랜잭션 격리 및 로깅)
    try:
        # (1) 단일 S3 경로 저장
        s3_output_path = result.get("s3_output_path")
        if s3_output_path:
            print(f"💾 [DB 저장] 메인 s3_output_path 저장 시도: {s3_output_path}")
            create_report_path(
                db,
                uid=current_user.uid,
                company_id=current_user.company_id,
                s3_output_path=s3_output_path,
            )

        # (2) 일자별 업로드 내역 저장
        daily_uploads = result.get("daily_uploads") or []
        print(f"💾 [DB 저장] daily_uploads 항목 수: {len(daily_uploads)}개")

        for idx, daily_upload in enumerate(daily_uploads):
            daily_docx_path = daily_upload.get("s3_docx_output_path")
            if daily_docx_path:
                docx_filename = daily_docx_path.rsplit("/", 1)[-1]
                print(
                    f"   ├─ [{idx+1}] Word 리포트 DB 저장: {docx_filename} ({daily_docx_path})"
                )
                create_report_path(
                    db,
                    uid=current_user.uid,
                    company_id=current_user.company_id,
                    s3_output_path=daily_docx_path,
                    summary=f"{docx_filename}",
                )

            daily_json_path = daily_upload.get("s3_json_output_path")
            if daily_json_path:
                date_str = daily_upload.get("date")
                parsed_date = (
                    datetime.strptime(date_str, "%Y-%m-%d")
                    if date_str
                    else datetime.now()
                )
                print(
                    f"   └─ [{idx+1}] JSON 서브 리포트 DB 저장: {parsed_date.date()} ({daily_json_path})"
                )
                create_sub_report_path(
                    db,
                    company_id=current_user.company_id,
                    path=daily_json_path,
                    date=parsed_date,
                )

        # (3) 알림 생성
        print(f"🔔 [알림 생성] 사용자({current_user.uid}) 완료 알림 생성 중...")
        create_notification(
            db=db,
            company_id=current_user.company_id,
            category="complete",
            title="위험성평가표 생성 완료",
            message="요청하신 위험성평가표 생성이 완료되었습니다.",
            path="/report",
            user_id=current_user.uid,
        )

        # 명시적 커밋 확인 (함수 내부에 commit이 없거나 롤백 방지용)
        db.commit()
        print("✅ [DB Commit 완료] 모든 리포트 및 알림 DB 저장 성공!")

    except Exception as e:
        db.rollback()
        print(f"❌ [DB-ERROR] DB 저장/알림 생성 중 예외 발생 (Rollback): {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"보고서는 생성되었으나 DB 저장 중 오류가 발생했습니다: {e}",
        )

    print("🎉 [위험성평가표 API 완료] 응답 반환\n" + "=" * 60 + "\n")
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

