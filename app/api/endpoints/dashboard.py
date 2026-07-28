from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.db import get_db
from app.crud.auth import get_current_user
from app.models import User
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    RecentEventResponse,
    ZoneStatsResponse,
    SafetyGradeResponse,
    ReportResponse,
    ReportSummaryResponse
)
from app.crud.dashboard import (
    get_dashboard_summary,
    get_recent_events,
    get_zone_statistics,
    calculate_safety_grade,
    get_reports_by_date,
    generate_report_ai_summary
)

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def read_dashboard_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """감지, 위반, 조치 대기/완료 건수 요약 API - 명세서 URL /api/dashboard/summary"""
    return get_dashboard_summary(db, company_id=current_user.company_id)


@router.get("/recentevents", response_model=List[RecentEventResponse])
def read_recent_events(limit: int = Query(10, ge=1, le=100), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """최근 발생한 이상 항목 리스트 조회 API - 명세서 URL /api/dashboard/recentevents"""
    return get_recent_events(db, company_id=current_user.company_id, limit=limit)


@router.get("/zones/stats", response_model=List[ZoneStatsResponse])
def read_zone_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """구역별 위험도 통계 API - 명세서 URL /api/dashboard/zones/stats"""
    return get_zone_statistics(db, company_id=current_user.company_id)


@router.get("/safetygrade", response_model=SafetyGradeResponse)
def read_safety_grade(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """종합 안전 등급 조회 API - 명세서 URL /api/dashboard/safetygrade"""
    return calculate_safety_grade(db, company_id=current_user.company_id)


@router.get("/reports", response_model=List[ReportResponse])
def read_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """통계 리포트 기간별 조회 API - 명세서 URL /api/dashboard/reports"""
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 포맷은 YYYY-MM-DD 여야 합니다.")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 포맷은 YYYY-MM-DD 여야 합니다.")
            
    return get_reports_by_date(db, company_id=current_user.company_id, start_date=start_dt, end_date=end_dt)


@router.get("/reports/summary", response_model=ReportSummaryResponse)
def read_report_summary(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """리포트 AI 요약 조회 API - 명세서 URL /api/dashboard/reports/summary"""
    summary_data = generate_report_ai_summary(
        db, 
        report_id=report_id, 
        company_id=current_user.company_id
    )
    if summary_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 리포트를 찾을 수 없습니다."
        )
    return summary_data
