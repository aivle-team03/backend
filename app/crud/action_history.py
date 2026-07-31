from datetime import datetime
from math import ceil
from typing import Dict, List, Optional

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Query, Session, joinedload

from app.models import (
    ActionHistory,
    Board,
    Event,
    EventCategory,
    InspectionHistory,
    User,
)
from app.schemas.action_history import (
    ActionHistoryCreateRequest,
    ActionStatus,
    ApprovalStatus,
    SourceType,
)


HANDLER_ROLES = ("현장관리자", "일반유저")


class ActionHistoryNotFoundError(Exception):
    pass


class ActionHistoryForbiddenError(Exception):
    pass


class ActionHistoryStateError(Exception):
    pass


class ActionHistoryValidationError(Exception):
    pass


def _with_relations(query: Query) -> Query:
    return query.options(
        joinedload(ActionHistory.category),
        joinedload(ActionHistory.handler),
        joinedload(ActionHistory.approver),
        joinedload(ActionHistory.board),
        joinedload(ActionHistory.event).joinedload(Event.cctv),
        joinedload(ActionHistory.inspection_history).joinedload(
            InspectionHistory.inspection
        ),
    )


def _get_action(
    db: Session,
    action_history_id: int,
    company_id: int,
) -> Optional[ActionHistory]:
    return (
        _with_relations(db.query(ActionHistory))
        .filter(
            ActionHistory.action_history_id == action_history_id,
            ActionHistory.company_id == company_id,
            ActionHistory.is_deleted == False,
        )
        .first()
    )


def _get_category(
    db: Session,
    category_id: int,
    company_id: int,
) -> EventCategory:
    category = (
        db.query(EventCategory)
        .filter(
            EventCategory.category_id == category_id,
            EventCategory.company_id == company_id,
            EventCategory.is_deleted == False,
        )
        .first()
    )
    if not category:
        raise ActionHistoryNotFoundError(
            "같은 회사에 속한 조치 카테고리를 찾을 수 없습니다."
        )
    return category


def _get_handler(db: Session, handler_uid: int, company_id: int) -> User:
    handler = (
        db.query(User)
        .filter(
            User.uid == handler_uid,
            User.company_id == company_id,
            User.role.in_(HANDLER_ROLES),
        )
        .first()
    )
    if not handler:
        raise ActionHistoryNotFoundError(
            "같은 회사에 속한 조치 가능 담당자를 찾을 수 없습니다."
        )
    return handler


def _source_id(action: ActionHistory) -> Optional[int]:
    if action.type == SourceType.BOARD.value:
        return action.board_id
    if action.type == SourceType.EVENT.value:
        return action.event_id
    if action.type == SourceType.INSPECTION_HISTORY.value:
        return action.inspection_history_id
    return None


def _serialize_action(
    action: ActionHistory,
    include_detail: bool = False,
) -> Dict:
    category = action.category
    data = {
        "action_history_id": action.action_history_id,
        "source_type": action.type,
        "source_id": _source_id(action),
        "action_name": action.action_name,
        "category_id": action.category_id,
        "category": category.category if category else None,
        "category_name": category.category_name if category else "",
        "category_level": category.level if category else 0,
        "location": action.location,
        "created_at": action.created_at,
        "completed_at": action.completed_at,
        "handler_uid": action.handler_uid,
        "handler_name": action.handler.name if action.handler else None,
        "action_status": action.action_status,
        "image_url": action.image_url,
        "approval_status": action.approval_status,
        "approver_uid": action.approver_uid,
        "approver_name": action.approver.name if action.approver else None,
        "approval_date": action.approval_date,
    }

    if include_detail:
        data.update(
            {
                "board_id": action.board_id,
                "event_id": action.event_id,
                "inspection_history_id": action.inspection_history_id,
                "content": action.content,
                "rejection_reason": action.rejection_reason,
            }
        )

    return data


def _apply_filters(
    query: Query,
    *,
    keyword: Optional[str] = None,
    source_type: Optional[str] = None,
    category_id: Optional[int] = None,
    action_status: Optional[str] = None,
    approval_status: Optional[str] = None,
    handler_uid: Optional[int] = None,
    unassigned: Optional[bool] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    completed_from: Optional[datetime] = None,
    completed_to: Optional[datetime] = None,
) -> Query:
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                ActionHistory.action_name.ilike(pattern),
                ActionHistory.location.ilike(pattern),
                ActionHistory.content.ilike(pattern),
                ActionHistory.handler_name.ilike(pattern),
                ActionHistory.approver_name.ilike(pattern),
                ActionHistory.handler.has(User.name.ilike(pattern)),
                ActionHistory.handler.has(User.user_id.ilike(pattern)),
                ActionHistory.category.has(
                    EventCategory.category_name.ilike(pattern)
                ),
            )
        )
    if source_type:
        query = query.filter(ActionHistory.type == source_type)
    if category_id is not None:
        query = query.filter(ActionHistory.category_id == category_id)
    if action_status:
        query = query.filter(ActionHistory.action_status == action_status)
    if approval_status:
        query = query.filter(ActionHistory.approval_status == approval_status)
    if handler_uid is not None:
        query = query.filter(ActionHistory.handler_uid == handler_uid)
    if unassigned is True:
        query = query.filter(ActionHistory.handler_uid.is_(None))
    elif unassigned is False:
        query = query.filter(ActionHistory.handler_uid.is_not(None))
    if created_from:
        query = query.filter(ActionHistory.created_at >= created_from)
    if created_to:
        query = query.filter(ActionHistory.created_at <= created_to)
    if completed_from:
        query = query.filter(ActionHistory.completed_at >= completed_from)
    if completed_to:
        query = query.filter(ActionHistory.completed_at <= completed_to)
    return query


def create_action_history(
    db: Session,
    request: ActionHistoryCreateRequest,
    company_id: int,
    creator: User,
) -> Dict:
    source_type = request.source_type.value
    source_columns = {
        "board_id": None,
        "event_id": None,
        "inspection_history_id": None,
    }
    category_id = request.category_id
    action_name = request.action_name
    location = request.location
    inspection_history = None

    if request.source_type == SourceType.BOARD:
        if creator.role != "안전관리자":
            raise ActionHistoryForbiddenError(
                "게시판 조치는 안전관리자만 등록할 수 있습니다."
            )
        board = (
            db.query(Board)
            .filter(
                Board.board_id == request.source_id,
                Board.company_id == company_id,
                Board.is_deleted == False,
            )
            .first()
        )
        if not board:
            raise ActionHistoryNotFoundError("게시글을 찾을 수 없습니다.")
        source_columns["board_id"] = board.board_id
        category_id = board.event_category_id or category_id
        action_name = action_name or board.title
        location = board.location or location

    elif request.source_type == SourceType.EVENT:
        if creator.role not in ("안전관리자", "관제사"):
            raise ActionHistoryForbiddenError(
                "이벤트 조치는 안전관리자 또는 관제사만 등록할 수 있습니다."
            )
        event = (
            db.query(Event)
            .options(joinedload(Event.category), joinedload(Event.cctv))
            .filter(
                Event.event_id == request.source_id,
                Event.company_id == company_id,
                Event.is_deleted == False,
            )
            .first()
        )
        if not event:
            raise ActionHistoryNotFoundError("이벤트를 찾을 수 없습니다.")
        source_columns["event_id"] = event.event_id
        category_id = event.category_id
        action_name = action_name or event.category.category_name
        location = event.cctv.location

    elif request.source_type == SourceType.INSPECTION_HISTORY:
        inspection_history = (
            db.query(InspectionHistory)
            .options(joinedload(InspectionHistory.inspection))
            .filter(
                InspectionHistory.inspection_history_id == request.source_id,
                InspectionHistory.company_id == company_id,
                InspectionHistory.is_deleted == False,
            )
            .first()
        )
        if not inspection_history:
            raise ActionHistoryNotFoundError("점검 이력을 찾을 수 없습니다.")
        if (
            creator.role != "안전관리자"
            and inspection_history.uid != creator.uid
        ):
            raise ActionHistoryForbiddenError(
                "해당 점검 담당자만 조치를 등록할 수 있습니다."
            )
        source_columns[
            "inspection_history_id"
        ] = inspection_history.inspection_history_id
        category_id = inspection_history.inspection.category_id
        action_name = action_name or inspection_history.name
        location = inspection_history.location

    elif request.source_type == SourceType.ADMIN_CREATED:
        if creator.role != "안전관리자":
            raise ActionHistoryForbiddenError(
                "직접추가 조치는 안전관리자만 등록할 수 있습니다."
            )

    if not category_id:
        raise ActionHistoryValidationError("조치 카테고리를 확인할 수 없습니다.")
    if not action_name:
        raise ActionHistoryValidationError("조치 이름을 확인할 수 없습니다.")
    if not location:
        raise ActionHistoryValidationError("조치 위치를 확인할 수 없습니다.")

    _get_category(db, category_id, company_id)
    handler_name = None
    if request.handler_uid is not None:
        handler = _get_handler(db, request.handler_uid, company_id)
        handler_name = handler.name

    action = ActionHistory(
        company_id=company_id,
        category_id=category_id,
        handler_uid=request.handler_uid,
        handler_name=handler_name,
        action_name=action_name,
        type=source_type,
        location=location,
        content=request.content,
        action_status=ActionStatus.WAITING.value,
        approval_status=None,
        is_deleted=False,
        **source_columns,
    )

    try:
        db.add(action)
        if inspection_history is not None:
            inspection_history.is_action_required = True
        db.commit()
    except Exception:
        db.rollback()
        raise

    created = _get_action(db, action.action_history_id, company_id)
    return _serialize_action(created, include_detail=True)


def get_action_histories(
    db: Session,
    *,
    company_id: int,
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    source_type: Optional[str] = None,
    category_id: Optional[int] = None,
    action_status: Optional[str] = None,
    approval_status: Optional[str] = None,
    handler_uid: Optional[int] = None,
    unassigned: Optional[bool] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    completed_from: Optional[datetime] = None,
    completed_to: Optional[datetime] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Dict:
    query = db.query(ActionHistory).filter(
        ActionHistory.company_id == company_id,
        ActionHistory.is_deleted == False,
    )
    query = _apply_filters(
        query,
        keyword=keyword,
        source_type=source_type,
        category_id=category_id,
        action_status=action_status,
        approval_status=approval_status,
        handler_uid=handler_uid,
        unassigned=unassigned,
        created_from=created_from,
        created_to=created_to,
        completed_from=completed_from,
        completed_to=completed_to,
    )

    totals = (
        query.order_by(None)
        .with_entities(
            func.count(ActionHistory.action_history_id),
            func.coalesce(
                func.sum(
                    case(
                        (ActionHistory.action_status == ActionStatus.WAITING.value, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ActionHistory.action_status
                            == ActionStatus.COMPLETED.value,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((ActionHistory.handler_uid.is_(None), 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ActionHistory.approval_status
                            == ApprovalStatus.PENDING.value,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ActionHistory.approval_status
                            == ApprovalStatus.APPROVED.value,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .one()
    )

    total_items = int(totals[0])
    completed_count = int(totals[2])
    approved_count = int(totals[5])
    approval_rate = (
        round(approved_count / completed_count * 100, 1)
        if completed_count
        else 0.0
    )

    sort_columns = {
        "created_at": ActionHistory.created_at,
        "completed_at": ActionHistory.completed_at,
        "approval_date": ActionHistory.approval_date,
    }
    sort_column = sort_columns[sort_by]
    order_expression = (
        sort_column.asc() if sort_order == "asc" else sort_column.desc()
    )
    actions = (
        _with_relations(query)
        .order_by(order_expression, ActionHistory.action_history_id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "items": [_serialize_action(action) for action in actions],
        "page": page,
        "size": size,
        "total_items": total_items,
        "total_pages": ceil(total_items / size) if total_items else 0,
        "summary": {
            "total_count": total_items,
            "waiting_count": int(totals[1]),
            "completed_count": completed_count,
            "unassigned_count": int(totals[3]),
            "pending_approval_count": int(totals[4]),
            "approved_count": approved_count,
            "approval_rate": approval_rate,
        },
    }


def get_action_history_detail(
    db: Session,
    action_history_id: int,
    company_id: int,
) -> Optional[Dict]:
    action = _get_action(db, action_history_id, company_id)
    if not action:
        return None
    return _serialize_action(action, include_detail=True)


def search_action_handlers(
    db: Session,
    *,
    company_id: int,
    keyword: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> Dict:
    query = db.query(User).filter(
        User.company_id == company_id,
        User.role.in_(HANDLER_ROLES),
    )
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(pattern),
                User.user_id.ilike(pattern),
                User.category.ilike(pattern),
            )
        )

    total_items = query.count()
    users = (
        query.order_by(User.name.asc(), User.uid.asc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "items": users,
        "page": page,
        "size": size,
        "total_items": total_items,
        "total_pages": ceil(total_items / size) if total_items else 0,
    }


def assign_action_handlers(
    db: Session,
    *,
    action_history_ids: List[int],
    handler_uid: Optional[int],
    company_id: int,
) -> List[Dict]:
    handler_name = None
    if handler_uid is not None:
        handler = _get_handler(db, handler_uid, company_id)
        handler_name = handler.name

    actions = (
        db.query(ActionHistory)
        .filter(
            ActionHistory.action_history_id.in_(action_history_ids),
            ActionHistory.company_id == company_id,
            ActionHistory.is_deleted == False,
        )
        .all()
    )
    if len(actions) != len(action_history_ids):
        raise ActionHistoryNotFoundError(
            "배정할 조치 중 찾을 수 없는 항목이 있습니다."
        )
    if any(
        action.action_status != ActionStatus.WAITING.value for action in actions
    ):
        raise ActionHistoryStateError(
            "조치 대기 상태인 항목만 담당자를 배정하거나 변경할 수 있습니다."
        )

    try:
        for action in actions:
            action.handler_uid = handler_uid
            action.handler_name = handler_name
        db.commit()
    except Exception:
        db.rollback()
        raise

    refreshed = {
        action_id: _get_action(db, action_id, company_id)
        for action_id in action_history_ids
    }
    return [
        _serialize_action(refreshed[action_id])
        for action_id in action_history_ids
    ]


def get_my_action_histories(
    db: Session,
    *,
    company_id: int,
    uid: int,
    action_status: Optional[str] = None,
    approval_status: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> Dict:
    return get_action_histories(
        db,
        company_id=company_id,
        handler_uid=uid,
        action_status=action_status,
        approval_status=approval_status,
        page=page,
        size=size,
        sort_by="created_at",
        sort_order="desc",
    )


def complete_action_history(
    db: Session,
    *,
    action_history_id: int,
    company_id: int,
    handler_uid: int,
    content: str,
    image_url: str,
) -> Dict:
    action = _get_action(db, action_history_id, company_id)
    if not action:
        raise ActionHistoryNotFoundError("조치를 찾을 수 없습니다.")
    if action.handler_uid != handler_uid:
        raise ActionHistoryForbiddenError(
            "배정된 담당자만 조치를 완료할 수 있습니다."
        )
    if action.action_status != ActionStatus.WAITING.value:
        raise ActionHistoryStateError("조치 대기 상태에서만 완료할 수 있습니다.")
    if action.approval_status not in (None, ApprovalStatus.REJECTED.value):
        raise ActionHistoryStateError(
            "승인 대기 또는 승인 완료 상태의 조치는 다시 완료할 수 없습니다."
        )

    if action.handler:
        action.handler_name = action.handler.name

    action.content = content
    action.image_url = image_url
    action.action_status = ActionStatus.COMPLETED.value
    action.approval_status = ApprovalStatus.PENDING.value
    action.completed_at = datetime.now()
    action.approver_uid = None
    action.approver_name = None
    action.approval_date = None

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _serialize_action(
        _get_action(db, action_history_id, company_id),
        include_detail=True,
    )


def approve_action_history(
    db: Session,
    *,
    action_history_id: int,
    company_id: int,
    approver_user: User,
) -> Dict:
    action = _get_action(db, action_history_id, company_id)
    if not action:
        raise ActionHistoryNotFoundError("조치를 찾을 수 없습니다.")
    if (
        action.action_status != ActionStatus.COMPLETED.value
        or action.approval_status != ApprovalStatus.PENDING.value
    ):
        raise ActionHistoryStateError(
            "조치 완료 및 승인 대기 상태에서만 승인할 수 있습니다."
        )

    action.approval_status = ApprovalStatus.APPROVED.value
    action.approver_uid = approver_user.uid
    action.approver_name = approver_user.name
    action.approval_date = datetime.now()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _serialize_action(
        _get_action(db, action_history_id, company_id),
        include_detail=True,
    )


def reject_action_history(
    db: Session,
    *,
    action_history_id: int,
    company_id: int,
    approver_user: User,
    rejection_reason: str,
) -> Dict:
    action = _get_action(db, action_history_id, company_id)
    if not action:
        raise ActionHistoryNotFoundError("조치를 찾을 수 없습니다.")
    if (
        action.action_status != ActionStatus.COMPLETED.value
        or action.approval_status != ApprovalStatus.PENDING.value
    ):
        raise ActionHistoryStateError(
            "조치 완료 및 승인 대기 상태에서만 반려할 수 있습니다."
        )

    action.action_status = ActionStatus.WAITING.value
    action.approval_status = ApprovalStatus.REJECTED.value
    action.completed_at = None
    action.approver_uid = approver_user.uid
    action.approver_name = approver_user.name
    action.approval_date = datetime.now()
    action.rejection_reason = rejection_reason

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _serialize_action(
        _get_action(db, action_history_id, company_id),
        include_detail=True,
    )
