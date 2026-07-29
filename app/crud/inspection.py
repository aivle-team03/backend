from datetime import datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models import Inspection, InspectionHistory, EventCategory, User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionHistoryCreate,
    InspectionHistoryUpdate,
)

# ==========================================
# 헬퍼 함수: 카테고리 문자열 주입 직렬화
# ==========================================

def _serialize_inspection(inspection: Inspection) -> dict:
    """Inspection 객체에 EventCategory.category 문자열 주입"""
    category_str = "기타"
    if hasattr(inspection, "category") and inspection.category:
        category_str = inspection.category.category or inspection.category.category_name
    elif hasattr(inspection, "event_category") and inspection.event_category:
        category_str = inspection.event_category.category or inspection.event_category.category_name

    return {
        "inspection_id": inspection.inspection_id,
        "company_id": inspection.company_id,
        "name": inspection.name,
        "category_id": inspection.category_id,
        "category": category_str,  # 🚀 "소방안전", "시설안전" 등의 문자열 전달
        "location": inspection.location,
        "cycle": inspection.cycle,
        "content": inspection.content,
    }


def _serialize_history(history: InspectionHistory) -> dict:
    """InspectionHistory 객체에 카테고리명 및 담당자 이름 주입"""
    category_str = "기타"
    if hasattr(history, "inspection") and history.inspection:
        insp = history.inspection
        if hasattr(insp, "category") and insp.category:
            category_str = insp.category.category
        elif hasattr(insp, "event_category") and insp.event_category:
            category_str = insp.event_category.category

    user_name = None
    if hasattr(history, "user") and history.user:
        user_name = history.user.name

    return {
        "inspection_history_id": history.inspection_history_id,
        "inspection_id": history.inspection_id,
        "company_id": history.company_id,
        "name": history.name,
        "date": history.date,
        "location": history.location,
        "uid": history.uid,
        "user_name": user_name,
        "status": history.status,
        "is_action_required": history.is_action_required,
        "content": history.content,
        "category_name": category_str,
    }


# ==========================================
# 1. Inspection (점검 항목 Master) CRUD
# ==========================================


def get_inspections_by_company(
    db: Session, company_id: int, skip: int = 0, limit: int = 100
) -> List[dict]:
    """해당 회사의 전체 점검 목록 조회 (카테고리 문자열 포함)"""
    inspections = (
        db.query(Inspection)
        .options(joinedload(Inspection.category))  # EventCategory 미리 로드
        .filter(Inspection.company_id == company_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_inspection(insp) for insp in inspections]


def get_inspection_by_id(
    db: Session, inspection_id: int, company_id: int
) -> Optional[dict]:
    """해당 회사의 특정 점검 항목 단건 조회"""
    insp = (
        db.query(Inspection)
        .options(joinedload(Inspection.category))
        .filter(
            Inspection.inspection_id == inspection_id,
            Inspection.company_id == company_id,
        )
        .first()
    )
    if not insp:
        return None
    return _serialize_inspection(insp)


def create_inspection(
    db: Session, inspection_in: InspectionCreate, company_id: int
) -> dict:
    """새로운 점검 항목 생성"""
    data = (
        inspection_in.model_dump()
        if hasattr(inspection_in, "model_dump")
        else inspection_in.dict()
    )

    db_obj = Inspection(**data, company_id=company_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    created = (
        db.query(Inspection)
        .options(joinedload(Inspection.category))
        .filter(Inspection.inspection_id == db_obj.inspection_id)
        .first()
    )
    return _serialize_inspection(created)


def update_inspection(
    db: Session,
    inspection_id: int,
    company_id: int,
    inspection_in: InspectionUpdate,
) -> Optional[dict]:
    """점검 항목 정보 수정"""
    db_obj = (
        db.query(Inspection)
        .filter(
            Inspection.inspection_id == inspection_id,
            Inspection.company_id == company_id,
        )
        .first()
    )
    if not db_obj:
        return None

    update_data = (
        inspection_in.model_dump(exclude_unset=True)
        if hasattr(inspection_in, "model_dump")
        else inspection_in.dict(exclude_unset=True)
    )

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.commit()
    db.refresh(db_obj)

    updated = (
        db.query(Inspection)
        .options(joinedload(Inspection.category))
        .filter(Inspection.inspection_id == inspection_id)
        .first()
    )
    return _serialize_inspection(updated)


def delete_inspection(
    db: Session, inspection_id: int, company_id: int
) -> bool:
    """점검 항목 삭제 (관련 이력도 삭제)"""
    db_obj = (
        db.query(Inspection)
        .filter(
            Inspection.inspection_id == inspection_id,
            Inspection.company_id == company_id,
        )
        .first()
    )
    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True


# ==========================================
# 2. InspectionHistory (점검 이력) CRUD
# ==========================================


def get_histories_by_inspection(
    db: Session, inspection_id: int, company_id: int
) -> List[dict]:
    """특정 점검 항목의 이력 목록 조회 (최신순 정렬)"""
    histories = (
        db.query(InspectionHistory)
        .options(
            joinedload(InspectionHistory.inspection).joinedload(Inspection.category),
            joinedload(InspectionHistory.user),
        )
        .filter(
            InspectionHistory.inspection_id == inspection_id,
            InspectionHistory.company_id == company_id,
        )
        .order_by(InspectionHistory.date.desc())
        .all()
    )
    return [_serialize_history(h) for h in histories]


def get_history_by_id(
    db: Session, inspection_history_id: int, company_id: int
) -> Optional[InspectionHistory]:
    """특정 점검 이력 단건 조회"""
    return (
        db.query(InspectionHistory)
        .filter(
            InspectionHistory.inspection_history_id == inspection_history_id,
            InspectionHistory.company_id == company_id,
        )
        .first()
    )


def get_all_histories_by_company(
    db: Session,
    company_id: int,
    status: Optional[str] = None,
    is_action_required: Optional[bool] = None,
    date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[dict]:
    """회사 전체 점검 이력 목록 조회 (조건별 필터링 지원)"""
    query = (
        db.query(InspectionHistory)
        .options(
            joinedload(InspectionHistory.inspection).joinedload(Inspection.category),
            joinedload(InspectionHistory.user),
        )
        .filter(InspectionHistory.company_id == company_id)
    )

    if status:
        query = query.filter(InspectionHistory.status == status)

    if is_action_required is not None:
        query = query.filter(
            InspectionHistory.is_action_required == is_action_required
        )

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(
                func.date(InspectionHistory.date) == target_date
            )
        except ValueError:
            pass

    histories = (
        query.order_by(InspectionHistory.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_history(h) for h in histories]


def get_histories_by_user(
    db: Session,
    company_id: int,
    uid: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[dict]:
    """특정 유저에게 배정되거나 완료한 점검 이력 목록 조회"""
    query = (
        db.query(InspectionHistory)
        .options(
            joinedload(InspectionHistory.inspection).joinedload(Inspection.category),
            joinedload(InspectionHistory.user),
        )
        .filter(
            InspectionHistory.company_id == company_id,
            InspectionHistory.uid == uid,
        )
    )

    if status:
        query = query.filter(InspectionHistory.status == status)

    histories = (
        query.order_by(InspectionHistory.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_history(h) for h in histories]


def create_inspection_history(
    db: Session, history_in: InspectionHistoryCreate, company_id: int
) -> dict:
    """점검 수행 이력 추가"""
    inspection = (
        db.query(Inspection)
        .filter(
            Inspection.inspection_id == history_in.inspection_id,
            Inspection.company_id == company_id,
        )
        .first()
    )
    if not inspection:
        raise ValueError("유효하지 않거나 접근 권한이 없는 점검 항목입니다.")

    data = (
        history_in.model_dump()
        if hasattr(history_in, "model_dump")
        else history_in.dict()
    )

    db_obj = InspectionHistory(**data, company_id=company_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    created = (
        db.query(InspectionHistory)
        .options(
            joinedload(InspectionHistory.inspection).joinedload(Inspection.category),
            joinedload(InspectionHistory.user),
        )
        .filter(InspectionHistory.inspection_history_id == db_obj.inspection_history_id)
        .first()
    )
    return _serialize_history(created)


def update_inspection_history(
    db: Session,
    inspection_history_id: int,
    company_id: int,
    history_in: InspectionHistoryUpdate,
) -> Optional[dict]:
    """점검 이력 수정"""
    db_obj = (
        db.query(InspectionHistory)
        .filter(
            InspectionHistory.inspection_history_id == inspection_history_id,
            InspectionHistory.company_id == company_id,
        )
        .first()
    )

    if not db_obj:
        return None

    update_data = (
        history_in.model_dump(exclude_unset=True)
        if hasattr(history_in, "model_dump")
        else history_in.dict(exclude_unset=True)
    )

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.commit()
    db.refresh(db_obj)

    updated = (
        db.query(InspectionHistory)
        .options(
            joinedload(InspectionHistory.inspection).joinedload(Inspection.category),
            joinedload(InspectionHistory.user),
        )
        .filter(InspectionHistory.inspection_history_id == inspection_history_id)
        .first()
    )
    return _serialize_history(updated)


def delete_inspection_history(
    db: Session, inspection_history_id: int, company_id: int
) -> bool:
    """점검 이력 삭제"""
    db_obj = (
        db.query(InspectionHistory)
        .filter(
            InspectionHistory.inspection_history_id == inspection_history_id,
            InspectionHistory.company_id == company_id,
        )
        .first()
    )
    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True