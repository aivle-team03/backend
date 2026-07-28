from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Inspection, InspectionHistory
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionHistoryCreate,
    InspectionHistoryUpdate,
)

# ==========================================
# 1. Inspection (점검 항목 Master) CRUD
# ==========================================


def get_inspections_by_company(
    db: Session, company_id: int, skip: int = 0, limit: int = 100
) -> List[Inspection]:
    """해당 회사의 전체 점검 목록 조회"""
    return (
        db.query(Inspection)
        .filter(Inspection.company_id == company_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_inspection_by_id(
    db: Session, inspection_id: int, company_id: int
) -> Optional[Inspection]:
    """해당 회사의 특정 점검 항목 단건 조회"""
    return (
        db.query(Inspection)
        .filter(
            Inspection.inspection_id == inspection_id,
            Inspection.company_id == company_id,
        )
        .first()
    )


def create_inspection(
    db: Session, inspection_in: InspectionCreate, company_id: int
) -> Inspection:
    data = (
        inspection_in.model_dump()
        if hasattr(inspection_in, "model_dump")
        else inspection_in.dict()
    )

    db_obj = Inspection(**data, company_id=company_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_inspection(
    db: Session,
    inspection_id: int,
    company_id: int,
    inspection_in: InspectionUpdate,
) -> Optional[Inspection]:
    """점검 항목 정보 수정"""
    db_obj = get_inspection_by_id(db, inspection_id, company_id)
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
    return db_obj


def delete_inspection(
    db: Session, inspection_id: int, company_id: int
) -> bool:
    """점검 항목 삭제 (관련 이력도 삭제)"""
    db_obj = get_inspection_by_id(db, inspection_id, company_id)
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
) -> List[InspectionHistory]:
    """특정 점검 항목의 이력 목록 조회"""
    return (
        db.query(InspectionHistory)
        .filter(
            InspectionHistory.inspection_id == inspection_id,
            InspectionHistory.company_id == company_id,
        )
        .order_by(InspectionHistory.inspected_at.desc())
        .all()
    )


def create_inspection_history(
    db: Session, history_in: InspectionHistoryCreate, company_id: int
) -> InspectionHistory:
    """점검 수행 이력 추가"""
    # 1. 해당 점검 항목이 우리 회사 항목인지 먼저 검증
    inspection = get_inspection_by_id(db, history_in.inspection_id, company_id)
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
    return db_obj


def update_inspection_history(
    db: Session,
    history_id: int,
    company_id: int,
    history_in: InspectionHistoryUpdate,
) -> Optional[InspectionHistory]:
    """점검 이력 수정"""
    db_obj = (
        db.query(InspectionHistory)
        .filter(
            InspectionHistory.history_id == history_id,
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
    return db_obj