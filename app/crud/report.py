from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from app.models.report import Report
from app.models.report_event_map import ReportEventMap
from app.models.report_checklist_map import ReportChecklistMap
from app.models.user import User

def create_report(
    db: Session,
    uid: int,
    content: str,
    event_ids: Optional[List[int]] = None,
    checklist_ids: Optional[List[int]] = None
) -> Report:
    summary = content[:50] + "..." if len(content) > 50 else content
    report = Report(
        uid=uid,
        content=content,
        summary=summary,
        created_at=datetime.utcnow()
    )
    db.add(report)
    db.flush() 

    if event_ids:
        db.add_all([ReportEventMap(report_id=report.report_id, event_id=eid) for eid in event_ids])
            
    if checklist_ids:
        db.add_all([ReportChecklistMap(report_id=report.report_id, checklist_id=cid) for cid in checklist_ids])

    db.commit()
    db.refresh(report)
    return report

def get_reports(
    db: Session,
    page: int = 1,
    size: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    writer: Optional[str] = None,
    keyword: Optional[str] = None
):
    query = db.query(Report)

    if start_date:
        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(Report.created_at >= s_dt)
    if end_date:
        e_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        query = query.filter(Report.created_at <= e_dt)
    if writer:
        query = query.join(User, Report.uid == User.uid).filter(
            or_(
                User.name.like(f"%{writer}%"),
                User.user_id.like(f"%{writer}%")
            )
        )
    if keyword:
        query = query.filter(
            or_(
                Report.content.like(f"%{keyword}%"),
                Report.summary.like(f"%{keyword}%")
            )
        )

    total = query.count()
    items = query.order_by(Report.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return total, items

def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
    return db.query(Report).filter(Report.report_id == report_id).first()

def update_report(db: Session, report_id: int, uid: int, content: str) -> Optional[Report]:
    report = db.query(Report).filter(Report.report_id == report_id, Report.uid == uid).first()
    if not report:
        return None
        
    report.content = content
    report.summary = content[:50] + "..." if len(content) > 50 else content
    db.commit()
    db.refresh(report)
    return report

def delete_report(db: Session, report_id: int, uid: int) -> bool:
    report = db.query(Report).filter(Report.report_id == report_id, Report.uid == uid).first()
    if not report:
        return False
        
    db.delete(report)
    db.commit()
    return True