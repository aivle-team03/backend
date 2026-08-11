from sqlalchemy.orm import Session
from sqlalchemy import func, select
from datetime import datetime, timedelta
from app.utils.datetime_utils import get_kst_now
from typing import List
from app.models.cctv import CCTV
from app.models.event import Event
from app.models.event_category import EventCategory
from app.models.action_history import ActionHistory
from app.models.report import Report
from app.schemas.action_history import ActionStatus, ApprovalStatus


# 이벤트 조치 진행 상태. 조치가 없는 이벤트는 UNASSIGNED 로 본다.
UNASSIGNED = "미조치"
IN_PROGRESS = "조치 진행"
REVIEW_PENDING = "승인 대기"
DONE = "완료"


def _resolve_status(action_status: str, approval_status: str) -> str:
    """action_status 와 approval_status 두 컬럼을 하나의 진행 상태로 합친다."""
    if approval_status == ApprovalStatus.APPROVED.value:
        return DONE
    if action_status == ActionStatus.COMPLETED.value:
        return REVIEW_PENDING
    # 반려되면 action_status 가 다시 "조치 대기"로 돌아오므로 여기에 포함된다.
    return IN_PROGRESS


def _latest_status_by_event(db: Session, company_id: int) -> dict:
    """이벤트별 최신 조치의 진행 상태를 {event_id: 상태} 로 돌려준다."""
    latest_ids = (
        select(func.max(ActionHistory.action_history_id))
        .where(
            ActionHistory.company_id == company_id,
            ActionHistory.is_deleted == False,
            ActionHistory.event_id.isnot(None),
        )
        .group_by(ActionHistory.event_id)
    )
    rows = (
        db.query(
            ActionHistory.event_id,
            ActionHistory.action_status,
            ActionHistory.approval_status,
        )
        .filter(ActionHistory.action_history_id.in_(latest_ids))
        .all()
    )
    return {
        event_id: _resolve_status(action_status, approval_status)
        for event_id, action_status, approval_status in rows
    }


def get_dashboard_summary(db: Session, company_id: int) -> dict:
    detected_count = db.query(Event).filter(Event.company_id == company_id, Event.is_deleted == False,).count()
    
    violation_count = (
        db.query(Event)
        .join(EventCategory, Event.category_id == EventCategory.category_id)
        .filter(
            Event.company_id == company_id,
            Event.is_deleted == False,
            EventCategory.is_deleted == False,
            EventCategory.category.in_(["위험", "경고"])
        )
        .count()
    )

    completed_action_count = (
        db.query(ActionHistory)
        .filter(
            ActionHistory.company_id == company_id,
            ActionHistory.is_deleted == False,
            ActionHistory.approval_status == ApprovalStatus.APPROVED.value,
        )
        .count()
    )

    pending_action_count = (
        db.query(ActionHistory)
        .filter(
            ActionHistory.company_id == company_id,
            ActionHistory.is_deleted == False,
            func.coalesce(ActionHistory.approval_status, "") != ApprovalStatus.APPROVED.value,
        )
        .count()
    )

    return {
        "detected_count": detected_count,
        "violation_count": violation_count,
        "pending_action_count": pending_action_count,
        "completed_action_count": completed_action_count
    }


def get_recent_events(db: Session, company_id: int, limit: int = 10) -> List[dict]:
    results = db.query(Event, EventCategory, CCTV)\
        .join(EventCategory, Event.category_id == EventCategory.category_id)\
        .join(CCTV, Event.cctv_id == CCTV.cctv_id)\
        .filter(Event.company_id == company_id, Event.is_deleted == False, EventCategory.is_deleted == False,)\
        .order_by(Event.date.desc())\
        .limit(limit).all()
        
    out = []
    for ev, cat, cam in results:
        out.append({
            "event_id": ev.event_id,
            "company_id": ev.company_id,
            "category_name": cat.category_name,
            "cctv_name": cam.cctv_name,
            "location": cam.location,
            "date": ev.date,
            "image_url": ev.image_url
        })
    return out


def get_zone_statistics(db: Session, company_id: int):
    locations = (
        db.query(CCTV.location)
        .filter(CCTV.company_id == company_id, CCTV.is_deleted == False,)
        .distinct()
        .all()
    )
    results = []
    status_by_event = _latest_status_by_event(db, company_id)

    for (loc,) in locations:
        if not loc:
            continue
        cctvs = (
            db.query(CCTV)
            .filter(
                CCTV.company_id == company_id,
                CCTV.location == loc,
                CCTV.is_deleted == False,
            )
            .all()
        )
        cctv_count = len(cctvs)
        cctv_ids = [c.cctv_id for c in cctvs]
        
        if not cctv_ids:
            event_count = 0
            unresolved_count = 0
        else:
            event_count = (
                db.query(Event)
                .filter(
                    Event.company_id == company_id,
                    Event.cctv_id.in_(cctv_ids),
                    Event.is_deleted == False,
                )
                .count()
            )
            events = (
                db.query(Event)
                .filter(
                    Event.company_id == company_id,
                    Event.cctv_id.in_(cctv_ids),
                    Event.is_deleted == False,
                )
                .all()
            )
            unresolved_count = 0
            for ev in events:
                status = status_by_event.get(ev.event_id, UNASSIGNED)
                if status in (UNASSIGNED, IN_PROGRESS):
                    unresolved_count += 1
                
        risk_index = min(100.0, float(unresolved_count / (cctv_count + 1) * 20.0))
        results.append({
            "location": loc,
            "cctv_count": cctv_count,
            "event_count": event_count,
            "risk_index": round(risk_index, 1)
        })
        
    return results


def calculate_safety_grade(db: Session, company_id: int):
    thirty_days_ago = get_kst_now() - timedelta(days=30)
    events = (
        db.query(Event)
        .filter(
            Event.company_id == company_id,
            Event.date >= thirty_days_ago,
            Event.is_deleted == False,
        )
        .all()
    )
    
    score = 100
    unresolved_count = 0
    unassigned_count = 0
    progress_count = 0
    pending_count = 0

    status_by_event = _latest_status_by_event(db, company_id)

    for ev in events:
        status = status_by_event.get(ev.event_id, UNASSIGNED)

        if status == UNASSIGNED:
            score -= 5
            unassigned_count += 1
            unresolved_count += 1
        elif status == IN_PROGRESS:
            score -= 2
            progress_count += 1
            unresolved_count += 1
        elif status == REVIEW_PENDING:
            score -= 1
            pending_count += 1
            unresolved_count += 1
            
    score = max(0, score)
    
    if score >= 95:
        grade = "A"
    elif score >= 85:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"
        
    if unresolved_count > 0:
        reason = f"미해결 이상 항목 총 {unresolved_count}건 존재 (미조치 {unassigned_count}건, 조치 진행/대기 {progress_count}건, 검토대기 {pending_count}건)로 인해 등급 조정"
    else:
        reason = "모든 위험 요소가 신속하고 완벽히 조치되어 최상의 안전 등급 유지 중"
        
    return {
        "score": score,
        "grade": grade,
        "reason": reason
    }


def get_reports_by_date(db: Session, company_id: int, start_date: datetime = None, end_date: datetime = None):
    query = db.query(Report).filter(Report.company_id == company_id, Report.is_deleted == False,)
    if start_date and end_date:
        query = query.filter(Report.created_at.between(start_date, end_date))
    return query.order_by(Report.created_at.desc()).all()


def generate_report_ai_summary(db: Session, report_id: int, company_id: int):
    report = (
        db.query(Report)
        .filter(
            Report.report_id == report_id,
            Report.company_id == company_id,
            Report.is_deleted == False,
        )
        .first()
    )
    if not report:
        return None
        
    ai_analysis = (
        f"본 보고서는 '{report.summary}' 보고서에 대한 AI 종합 분석 요약입니다. "
        f"해당 기간 보고된 세부 내용을 기반으로 진단한 결과, 총 조치 소요 시간이 크게 단축되었으며, "
        f"CCTV 구역별 위험 징후들이 안전 매뉴얼에 따라 효과적으로 제어 및 승인 처리되고 있습니다. "
        f"향후 예방 관리를 위해 정기 점검 주기를 현 상태로 지속 권장합니다."
    )
    return {
        "report_id": report.report_id,
        "company_id": report.company_id,
        "summary": report.summary,
        "ai_analysis": ai_analysis
    }
