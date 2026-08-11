from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime
from app.utils.datetime_utils import get_kst_now
from app.models.report import Report
from app.models.sub_report import SubReport
from app.models.report_event_map import ReportEventMap
from app.models.report_checklist_map import ReportChecklistMap
from app.models.report_inspection_map import ReportInspectionMap
from app.models.report_action_map import ReportActionMap
from app.models.action_history import ActionHistory
from app.models.inspection import Inspection
from app.models.inspection_history import InspectionHistory
from app.models.event_category import EventCategory
from app.models.board import Board
from app.models.event import Event
from app.models.user import User
from app.crud.risk import calculate_risk_level

INSPECTION_DONE = "점검 완료"
APPROVED = "승인 완료"
TYPE_INSPECTION = "점검이력"
TYPE_DIRECT = "직접추가"
TYPE_BOARD = "게시판"
TYPE_EVENT = "이벤트"


def _iso(value):
    return value.isoformat() if value else None

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
        created_at=get_kst_now(),
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

def create_report_path(
    db: Session,
    uid: int,
    company_id: int,
    s3_output_path: str,
    summary: str = "위험성평가표 자동 생성",
) -> Report:
    """위험성평가표 자동 생성 결과(S3 경로)를 Report 테이블에 저장한다."""
    writer = None
    user = db.query(User).filter(User.uid == uid).first()
    if user:
        writer = user.name

    report = Report(
        company_id=company_id,
        uid=uid,
        writer=writer,
        content=s3_output_path,
        summary=summary,
        created_at=get_kst_now(),
        is_deleted=False,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

def create_sub_report_path(
        db: Session, 
        company_id: int, 
        path: str, 
        date: datetime) -> SubReport:
    """일자별 자동 생성 리포트 부속 파일(S3 경로)을 SubReport 테이블에 저장한다."""
    sub_report = SubReport(
        company_id=company_id,
        date=date,
        path=path,
    )
    db.add(sub_report)
    db.commit()
    db.refresh(sub_report)
    return sub_report

def create_sub_report(db: Session, start_date: str, end_date: str) -> List[SubReport]:
    """start_date ~ end_date 기간의 SubReport 목록을 조회한다."""
    query = db.query(SubReport)
    if start_date:
        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(SubReport.date >= s_dt)
    if end_date:
        e_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        query = query.filter(SubReport.date <= e_dt)
    return query.order_by(SubReport.date).all()

def build_history_column(db: Session, uid: int) -> dict:
    """report_agent(/api/report/risk-assessment/form/generate)에 넘길 DB 데이터를 조합한다."""
    category_by_id = {
        c.category_id: c
        for c in db.query(EventCategory).filter(
            EventCategory.is_deleted == False,
        )
    }
    inspection_by_id = {
        i.inspection_id: i
        for i in db.query(Inspection).filter(
            Inspection.is_deleted == False,
        )
    }
    board_by_id = {
        b.board_id: b
        for b in db.query(Board).filter(
            Board.is_deleted == False,
        )
    }
    event_by_id = {
        e.event_id: e
        for e in db.query(Event).filter(
            Event.is_deleted == False,
        )
    }
    event_counts = dict(
        db.query(Event.category_id, func.count(Event.event_id))
        .filter(Event.is_deleted == False)
        .group_by(Event.category_id)
        .all()
    )

    approved_actions = (
        db.query(ActionHistory)
        .filter(
            ActionHistory.approval_status == APPROVED,
            ActionHistory.is_deleted == False,
        )
        .all()
    )
    approved_action_by_inspection_history_id = {
        action.inspection_history_id: action
        for action in approved_actions
        if action.type == TYPE_INSPECTION and action.inspection_history_id is not None
    }

    inspection_histories = (
        db.query(InspectionHistory)
        .filter(
            InspectionHistory.is_deleted == False,
            InspectionHistory.status == INSPECTION_DONE,
        )
        .all()
    )

    def category_part(category_id):
        category = category_by_id.get(category_id)
        if not category:
            return {"category": None, "risk": None, "category_name": None}
        frequency = event_counts.get(category_id, 0)
        return {
            "category": category.category,
            "risk": calculate_risk_level(category.level, frequency),
            "category_name": category.category_name,
        }

    def inspection_part(history):
        if not history:
            return {
                "inspection_location": None,
                "inspection_date": None,
                "inspection_user_name": None,
                "inspection_content": None,
            }
        return {
            "inspection_location": history.location,
            "inspection_date": _iso(history.date),
            "inspection_user_name": history.user_name,
            "inspection_content": history.content,
        }

    def action_part(action):
        if not action:
            return {
                "action_name": None,
                "action_location": None,
                "completed_at": None,
                "handler_name": None,
                "content": None,
                "approver_name": None,
                "type": None,
            }
        return {
            "action_name": action.action_name,
            "action_location": action.location,
            "completed_at": _iso(action.completed_at),
            "handler_name": action.handler_name,
            "content": action.content,
            "approver_name": action.approver_name,
            "type": action.type,
        }

    def inspection_image_url_for_action(action):
        if not action:
            return None
        if action.type == TYPE_BOARD and action.board_id is not None:
            board = board_by_id.get(action.board_id)
            return board.image_url if board else None
        if action.type == TYPE_EVENT and action.event_id is not None:
            event = event_by_id.get(action.event_id)
            return event.image_url if event else None
        return None

    rows: List[dict] = []

    for history in inspection_histories:
        inspection = inspection_by_id.get(history.inspection_id)
        category_id = inspection.category_id if inspection else None
        action = approved_action_by_inspection_history_id.get(history.inspection_history_id)

        rows.append({
            **category_part(category_id),
            **inspection_part(history),
            "image_url": action.image_url if action else None,
            "inspection_image_url": None,
            **action_part(action),
        })

    for action in approved_actions:
        if action.type == TYPE_INSPECTION:
            continue
        if action.type not in (TYPE_DIRECT, TYPE_BOARD, TYPE_EVENT):
            continue

        rows.append({
            **category_part(action.category_id),
            **inspection_part(None),
            "image_url": action.image_url,
            "inspection_image_url": inspection_image_url_for_action(action),
            **action_part(action),
        })

    return {"final_history_rows": rows}


def build_board_column(db: Session, uid: int) -> dict:
    """report_agent(worker-feedback/generate)에 넘길 worker_feedback_rows를 직접 조립한다.

    AI 레포 table_builder.py(build_worker_feedback_table)와 동일한 로직을
    DB 직접 조회로 재현해서, report_agent가 그 노드를 완전히 건너뛰도록 한다.
    """
    event_counts = dict(
        db.query(Event.category_id, func.count(Event.event_id))
        .filter(Event.is_deleted == False)
        .group_by(Event.category_id)
        .all()
    )

    category_by_id = {
        c.category_id: c
        for c in db.query(EventCategory).filter(EventCategory.is_deleted == False)
    }

    board_by_id = {
        board.board_id: (board, writer_name)
        for board, writer_name in (
            db.query(Board, User.name.label("writer_name"))
            .outerjoin(User, Board.uid == User.uid)
            .filter(Board.is_deleted == False)
        )
    }

    actions = (
        db.query(ActionHistory)
        .filter(
            ActionHistory.type == TYPE_BOARD,
            ActionHistory.approval_status == APPROVED,
            ActionHistory.is_deleted == False,
        )
        .all()
    )

    rows: List[dict] = []
    for action in actions:
        board, writer_name = board_by_id.get(action.board_id, (None, None))
        category = category_by_id.get(action.category_id)
        writer = (writer_name or "알 수 없음") if board else None

        rows.append({
            "board_id": action.board_id,
            "category": category.category if category else None,
            "risk": calculate_risk_level(category.level, event_counts.get(action.category_id, 0)) if category else None,
            "category_name": category.category_name if category else None,
            "user": writer,
            "board_writer": writer,
            "board_created_at": _iso(board.created_at) if board else None,
            "board_contents": board.board_contents if board else None,
            "status": board.status if board else None,
            "board_image_url": board.image_url if board else None,
            "action_name": action.action_name,
            "location": action.location,
            "completed_at": _iso(action.completed_at),
            "action_status": action.action_status,
            "handler_name": action.handler_name,
            "content": action.content,
            "image_url": action.image_url,
            "approver_name": action.approver_name,
            "source_type": action.type,
        })

    rows.sort(key=lambda row: (
        row.get("board_created_at") or "",
        row.get("completed_at") or "",
        row.get("category") or "",
        row.get("category_name") or "",
    ))

    return {"worker_feedback_rows": rows}



