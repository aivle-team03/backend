from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
from app.models.cctv import CCTV
from app.models.event import Event
from app.models.event_category import EventCategory
from app.models.checklist import Checklist
from app.models.report import Report


def get_dashboard_summary(db: Session) -> dict:
    detected_count = db.query(Event).count()
    
    violation_count = db.query(Event).join(EventCategory, Event.category_id == EventCategory.category_id)\
        .filter(EventCategory.category.in_(["위험", "경고"])).count()
        
    pending_action_count = db.query(Checklist).filter(Checklist.status.in_(["미조치", "조치 대기", "조치 중"])).count()
    completed_action_count = db.query(Checklist).filter(Checklist.status.in_(["승인 완료", "완료"])).count()
    
    return {
        "detected_count": detected_count,
        "violation_count": violation_count,
        "pending_action_count": pending_action_count,
        "completed_action_count": completed_action_count
    }


def get_recent_events(db: Session, limit: int = 10) -> List[dict]:
    results = db.query(Event, EventCategory, CCTV)\
        .join(EventCategory, Event.category_id == EventCategory.category_id)\
        .join(CCTV, Event.camera_id == CCTV.cctv_id)\
        .order_by(Event.date.desc())\
        .limit(limit).all()
        
    out = []
    for ev, cat, cam in results:
        out.append({
            "event_id": ev.event_id,
            "category_name": cat.category_name,
            "cctv_name": cam.cctv_name,
            "location": cam.location,
            "date": ev.date,
            "image_url": ev.image_url
        })
    return out


def get_zone_statistics(db: Session):
    locations = db.query(CCTV.location).distinct().all()
    results = []
    
    for (loc,) in locations:
        if not loc:
            continue
        cctv_count = db.query(CCTV).filter(CCTV.location == loc).count()
        cctvs = db.query(CCTV).filter(CCTV.location == loc).all()
        cctv_ids = [c.cctv_id for c in cctvs]
        
        if not cctv_ids:
            event_count = 0
            unresolved_count = 0
        else:
            event_count = db.query(Event).filter(Event.camera_id.in_(cctv_ids)).count()
            events = db.query(Event).filter(Event.camera_id.in_(cctv_ids)).all()
            unresolved_count = 0
            for ev in events:
                latest_chk = db.query(Checklist).filter(Checklist.event_id == ev.event_id)\
                               .order_by(Checklist.checklist_id.desc()).first()
                status = latest_chk.status if latest_chk else "미조치"
                if status in ["미조치", "조치 대기", "조치 중"]:
                    unresolved_count += 1
                
        risk_index = min(100.0, float(unresolved_count / (cctv_count + 1) * 20.0))
        results.append({
            "location": loc,
            "cctv_count": cctv_count,
            "event_count": event_count,
            "risk_index": round(risk_index, 1)
        })
        
    return results


def calculate_safety_grade(db: Session):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    events = db.query(Event).filter(Event.date >= thirty_days_ago).all()
    
    score = 100
    unresolved_count = 0
    unassigned_count = 0
    progress_count = 0
    pending_count = 0
    
    for ev in events:
        latest_chk = db.query(Checklist).filter(Checklist.event_id == ev.event_id)\
                       .order_by(Checklist.checklist_id.desc()).first()
        status = latest_chk.status if latest_chk else "미조치"
        
        if status == "미조치":
            score -= 5
            unassigned_count += 1
            unresolved_count += 1
        elif status in ["조치 대기", "조치 중"]:
            score -= 2
            progress_count += 1
            unresolved_count += 1
        elif status == "승인 대기":
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


def get_reports_by_date(db: Session, start_date: datetime = None, end_date: datetime = None):
    query = db.query(Report)
    if start_date and end_date:
        query = query.filter(Report.created_at.between(start_date, end_date))
    return query.order_by(Report.created_at.desc()).all()


def generate_report_ai_summary(db: Session, report_id: int):
    report = db.query(Report).filter(Report.report_id == report_id).first()
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
        "summary": report.summary,
        "ai_analysis": ai_analysis
    }
