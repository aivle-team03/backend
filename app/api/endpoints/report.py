from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.db import get_db
from app.crud.auth import get_current_user
from app.models import User
from app.models.report import Report
from app.schemas.report import (
    ReportCreateRequest,
    ReportUpdateRequest,
    ReportDetailResponse,
    ReportListResponse
)
from app.crud.report import (
    create_report,
    get_reports,
    get_report_by_id,
    update_report,
    delete_report
)

router = APIRouter()

# [Refactor] 반복되는 응답 DTO 변환 로직을 헬퍼 함수로 추상화 (DRY 원칙)
def format_report_response(report: Report) -> dict:
    event_ids = [m.event_id for m in report.event_maps] if report.event_maps else []
    checklist_ids = [m.checklist_id for m in report.checklist_maps] if report.checklist_maps else []
    return {
        "report_id": report.report_id,
        "uid": report.uid,
        "content": report.content,
        "summary": report.summary,
        "created_at": report.created_at,
        "event_ids": event_ids,
        "checklist_ids": checklist_ids
    }


@router.post("", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
def post_create_report(
    req: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """선택한 이벤트와 체크리스트를 기반으로 보고서 생성 API"""
    report = create_report(
        db=db,
        uid=current_user.uid,
        content=req.content,
        event_ids=req.event_ids,
        checklist_ids=req.checklist_ids
    )
    return format_report_response(report)


@router.get("", response_model=ReportListResponse)
def read_reports(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    writer: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """보고서 목록 조회 API"""
    total, items = get_reports(
        db=db, page=page, size=size, start_date=start_date,
        end_date=end_date, writer=writer, keyword=keyword
    )
    
    # 헬퍼 함수를 통한 깔끔한 변환
    formatted = [format_report_response(r) for r in items]
        
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": formatted
    }


@router.get("/{report_id}", response_model=ReportDetailResponse)
def read_report_detail(report_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """보고서 상세 조회 API"""
    r = get_report_by_id(db, report_id=report_id)
    if not r:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
        
    return format_report_response(r)


@router.put("/{report_id}", response_model=ReportDetailResponse)
def put_update_report(
    req: ReportUpdateRequest,
    report_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user), # [Refactor] 인가 로직 추가
    db: Session = Depends(get_db)
):
    """보고서 내용 수정 API"""
    r = update_report(db, report_id=report_id, uid=current_user.uid, content=req.content)
    if not r:
        raise HTTPException(status_code=403, detail="보고서가 존재하지 않거나 수정 권한이 없습니다.")
        
    return format_report_response(r)


@router.delete("/{report_id}")
def delete_report_endpoint(
    report_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user), # [Refactor] 인가 로직 추가
    db: Session = Depends(get_db)
):
    """보고서 삭제 API"""
    success = delete_report(db, report_id=report_id, uid=current_user.uid)
    if not success:
        raise HTTPException(status_code=403, detail="보고서가 존재하지 않거나 삭제 권한이 없습니다.")
    return {"message": "보고서가 성공적으로 삭제되었습니다."}


@router.get("/{report_id}/download")
def download_report_pdf(
    report_id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    """보고서를 PDF 형태로 다운로드 API"""
    r = get_report_by_id(db, report_id=report_id)
    if not r:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    pdf_content = (
        f"%PDF-1.4\n1 0 obj\n<< /Title (Safety Report {r.report_id}) /Author (AIVLE Team 03) >>\nendobj\n"
        f"Content:\n{r.content}\nSummary:\n{r.summary}\nCreated At:\n{r.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    ).encode("utf-8")

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=safety_report_{report_id}.pdf"}
    )