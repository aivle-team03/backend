from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.action_history import ActionHistory
from app.models.event import Event
from app.models.user import User
from app.schemas.action_history import ActionStatus, SourceType


def _latest_event_actions(db: Session, company_id: int):
    """One latest action_history row per CCTV event."""
    return (
        db.query(
            ActionHistory.event_id.label("event_id"),
            func.max(ActionHistory.action_history_id).label("action_history_id"),
        )
        .filter(
            ActionHistory.company_id == company_id,
            ActionHistory.type == SourceType.EVENT.value,
            ActionHistory.is_deleted == False,
            ActionHistory.event_id.isnot(None),
        )
        .group_by(ActionHistory.event_id)
        .subquery()
    )


def get_monitoring_events(
    db: Session,
    company_id: int,
    cctv_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
):
    latest_actions = _latest_event_actions(db, company_id)
    query = (
        db.query(Event, ActionHistory)
        .join(latest_actions, Event.event_id == latest_actions.c.event_id)
        .join(ActionHistory, ActionHistory.action_history_id == latest_actions.c.action_history_id)
        .options(joinedload(Event.category), joinedload(Event.cctv))
        .filter(Event.company_id == company_id, Event.is_deleted == False)
    )

    if cctv_id is not None:
        query = query.filter(Event.cctv_id == cctv_id)
    if status is not None:
        query = query.filter(ActionHistory.action_status == status)

    # 화면에 노출하는 시각과 같은 action_history.created_at(KST)을 기준으로
    # 정렬해야 UTC로 저장된 과거 event.date 때문에 순서가 섞이지 않는다.
    rows = query.order_by(ActionHistory.created_at.desc()).offset(skip).limit(limit).all()
    events = []
    for event, action in rows:
        # event.date는 과거 seed 및 DB NOW()로 UTC인 행이 존재한다. CCTV 감지
        # 목록의 기준 시각은 실제 조치 생성 시각(action_history.created_at, KST)이다.
        event.date = action.created_at
        event.current_status = action.action_status
        event.action_history_id = action.action_history_id
        events.append(event)
    return events


def get_monitoring_event_by_id(db: Session, event_id: int, company_id: int):
    latest_actions = _latest_event_actions(db, company_id)
    row = (
        db.query(Event, ActionHistory)
        .join(latest_actions, Event.event_id == latest_actions.c.event_id)
        .join(ActionHistory, ActionHistory.action_history_id == latest_actions.c.action_history_id)
        .options(joinedload(Event.category), joinedload(Event.cctv))
        .filter(
            Event.event_id == event_id,
            Event.company_id == company_id,
            Event.is_deleted == False,
        )
        .first()
    )
    if not row:
        return None
    event, action = row
    event.date = action.created_at
    event.current_status = action.action_status
    event.action_history_id = action.action_history_id
    return event


def create_action_request(db: Session, event_id: int, target_uid: int, message: str, company_id: int):
    """Create a manual event action without using the legacy checklist table."""
    event = (
        db.query(Event)
        .options(joinedload(Event.category), joinedload(Event.cctv))
        .filter(
            Event.event_id == event_id,
            Event.company_id == company_id,
            Event.is_deleted == False,
        )
        .first()
    )
    if not event or not event.category or not event.cctv:
        return None

    handler = (
        db.query(User)
        .filter(User.uid == target_uid, User.company_id == company_id)
        .first()
    )
    action = ActionHistory(
        company_id=company_id,
        event_id=event_id,
        category_id=event.category_id,
        handler_uid=target_uid,
        handler_name=handler.name if handler else None,
        action_name=f"{event.category.category_name} action",
        type=SourceType.EVENT.value,
        location=event.cctv.location,
        content=message,
        action_status=ActionStatus.WAITING.value,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
