from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from app.models.report import Report
from app.models.report_event_map import ReportEventMap
from app.models.report_checklist_map import ReportChecklistMap
from app.models.report_inspection_map import ReportInspectionMap
from app.models.report_action_map import ReportActionMap
from app.models.action_history import ActionHistory
from app.models.user import User

def create_report(
    db: Session,
    company_id: int,
    uid: int,
    content: str,
    event_ids: Optional[List[int]] = None,
    checklist_ids: Optional[List[int]] = None,
    inspection_history_ids: Optional[List[int]] = None,
    action_history_ids: Optional[List[int]] = None,
    writer: Optional[str] = None,
) -> Report:
    if action_history_ids:
        action_count = (
            db.query(ActionHistory)
            .filter(
                ActionHistory.company_id == company_id,
                ActionHistory.action_history_id.in_(action_history_ids),
                ActionHistory.is_deleted == False,
            )
            .count()
        )
        if action_count != len(action_history_ids):
            raise ValueError(
                "연결할 조치 이력을 찾을 수 없거나 다른 회사의 조치 이력입니다."
            )
    if not writer and uid:
        user = db.query(User).filter(User.uid == uid).first()
        if user:
            writer = user.name

    summary = content[:50] + "..." if len(content) > 50 else content
    report = Report(
        company_id=company_id,
        uid=uid,
        writer=writer,
        content=content,
        summary=summary,
        created_at=datetime.utcnow(),
        is_deleted=False,
    )
    db.add(report)
    db.flush() 

    if event_ids:
        db.add_all([ReportEventMap(report_id=report.report_id, event_id=eid) for eid in event_ids])
            
    if checklist_ids:
        db.add_all([ReportChecklistMap(report_id=report.report_id, checklist_id=cid) for cid in checklist_ids])
        
    if inspection_history_ids:
        db.add_all(
            [
                ReportInspectionMap(
                    report_id=report.report_id, inspection_history_id=ihid
                )
                for ihid in inspection_history_ids
            ]
        )

    if action_history_ids:
        db.add_all(
            [
                ReportActionMap(
                    report_id=report.report_id,
                    action_history_id=action_history_id,
                )
                for action_history_id in action_history_ids
            ]
        )

    try:
        db.commit()
        db.refresh(report)
    except Exception:
        db.rollback()
        raise

    return report

def get_reports(
    db: Session,
    company_id: int,
    page: int = 1,
    size: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    writer: Optional[str] = None,
    keyword: Optional[str] = None
):
    query = (
        db.query(Report, User.name.label("writer_name"))
        .outerjoin(User, Report.uid == User.uid)
        .filter(Report.company_id == company_id, Report.is_deleted == False,)
    )

    if start_date:
        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(Report.created_at >= s_dt)
    if end_date:
        e_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        query = query.filter(Report.created_at <= e_dt)
    if writer:
        query = query.filter(
            or_(
                Report.writer.like(f"%{writer}%"),
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
    rows = query.order_by(Report.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for report, writer_name in rows:
        writer_display = report.writer or writer_name or "알 수 없음"
        item_dict = {
            "report_id": report.report_id,
            "company_id": report.company_id,
            "uid": report.uid,
            "content": report.content,
            "summary": report.summary,
            "created_at": report.created_at,
            "writer": writer_display,
            "action_history_ids": report.action_history_ids,
        }
        items.append(item_dict)

    return total, items

def get_report_by_id(db: Session, report_id: int, company_id: int) -> Optional[Report]:
    return (
        db.query(Report)
        .filter(
            Report.report_id == report_id,
            Report.company_id == company_id,
            Report.is_deleted == False,
        )
        .first()
    )

def update_report(db: Session, report_id: int, uid: int, company_id: int, content: str) -> Optional[Report]:
    report = (
        db.query(Report)
        .filter(
            Report.report_id == report_id,
            Report.company_id == company_id,
            Report.uid == uid,
            Report.is_deleted == False,
        )
        .first()
    )
    if not report:
        return None
        
    report.content = content
    report.summary = content[:50] + "..." if len(content) > 50 else content
    db.commit()
    db.refresh(report)
    return report

def delete_report(db: Session, report_id: int, uid: int, company_id: int) -> bool:
    report = (
        db.query(Report)
        .filter(
            Report.report_id == report_id,
            Report.company_id == company_id,
            Report.uid == uid,
            Report.is_deleted == False,
        )
        .first()
    )
    if not report:
        return False
        
    report.is_deleted = True
    db.commit()
    return True
