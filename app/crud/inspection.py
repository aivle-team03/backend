import calendar
from datetime import datetime
from typing import List, Optional
from sqlalchemy import func, extract
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
        
    user_name = None
    if hasattr(inspection, "user") and inspection.user:
        user_name = inspection.user.name

    return {
        "inspection_id": inspection.inspection_id,
        "company_id": inspection.company_id,
        "name": inspection.name,
        "category_id": inspection.category_id,
        "category": category_str,
        "location": inspection.location,
        "cycle": inspection.cycle,
        "content": inspection.content,
        "uid": inspection.uid,
        "user_name": user_name,
    }


def _serialize_history(history: InspectionHistory) -> dict:
    """InspectionHistory 객체에 카테고리명 및 담당자 이름 주입"""
    category_str = "기타"
    
    if hasattr(history, "inspection") and history.inspection:
        insp = history.inspection

    # Inspection 모델에 category 관계가 맺혀있는 경우
    if hasattr(insp, "category") and insp.category:
        cat_obj = insp.category
        # EventCategory/Category 테이블의 실제 컬럼명들을 차례대로 확인
        if hasattr(cat_obj, "category") and cat_obj.category:
            category_str = cat_obj.category
        elif hasattr(cat_obj, "category_name") and cat_obj.category_name:
            category_str = cat_obj.category_name
        elif hasattr(cat_obj, "name") and cat_obj.name:
            category_str = cat_obj.name

    user_name = history.user_name
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
        .options(joinedload(Inspection.category), joinedload(Inspection.user),)  # EventCategory 미리 로드
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
        .options(joinedload(Inspection.category),
                joinedload(Inspection.user),)
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
        db.query(InspectionHistory)
        .options(
            joinedload(InspectionHistory.inspection).joinedload(
                Inspection.category
            ),
            joinedload(InspectionHistory.user),
        )
        .filter(
            InspectionHistory.inspection_history_id
            == db_obj.inspection_history_id
        )
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
        .options(joinedload(Inspection.category),joinedload(Inspection.user),)
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
    
    if data.get("uid") and not data.get("user_name"):
        user = db.query(User).filter(User.uid == data["uid"]).first()
        if user:
            data["user_name"] = user.name

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
    
    if "uid" in update_data:
        if update_data["uid"]:
            user = db.query(User).filter(User.uid == update_data["uid"]).first()
            update_data["user_name"] = user.name if user else None
        else:
            update_data["user_name"] = None

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

def generate_scheduled_inspection_histories(db: Session, company_id: int = None):
    """
    모든 조건(주말 포함, 2월/월말 고려, ID 해시 분산, uid 상속, 구역(,) 분할)이 적용된 점검 이력 자동 생성 스케줄러
    """
    now = datetime.now()
    today_date = now.date()

    weekday = now.weekday()  # 0: 월 ~ 6: 일 (주말 포함)
    day_of_month = now.day   # 1 ~ 31일

    # 해당 달의 마지막 날짜 구하기 (2월: 28/29일, 4월: 30일 등)
    _, last_day_of_month = calendar.monthrange(now.year, now.month)
    is_last_day_of_month = day_of_month == last_day_of_month

    # 1. 대상 회사의 전체 Inspection 목록 조회
    query = db.query(Inspection)
    if company_id:
        query = query.filter(Inspection.company_id == company_id)

    inspections = query.all()
    created_count = 0

    for insp in inspections:
        should_create = False

        # ----------------------------------------------------
        # 💡 [1] 주말 포함 & 월말 예외 처리된 해시 분산 로직
        # ----------------------------------------------------
        if insp.cycle == '매일':
            should_create = True

        elif insp.cycle == '매주':
            if (insp.inspection_id % 7) == weekday:
                should_create = True

        elif insp.cycle == '매월':
            target_day = (insp.inspection_id % 28) + 1
            if day_of_month == target_day:
                should_create = True
            elif is_last_day_of_month and target_day > last_day_of_month:
                should_create = True

        # ----------------------------------------------------
        # 💡 [2] 구역(,) 분할 및 이력 생성 (중복 방지)
        # ----------------------------------------------------
        if should_create:
            # 쉼표(,) 기준으로 location 분할 및 공백 제거
            if insp.location:
                locations = [loc.strip() for loc in insp.location.split(',') if loc.strip()]
            else:
                locations = ['구역 미지정']

            # 매월: 이번 달(Year, Month) 중복 체크 / 매일·매주: 오늘(Year, Month, Day) 중복 체크
            if insp.cycle == '매월':
                existing_histories = (
                    db.query(InspectionHistory)
                    .filter(
                        InspectionHistory.inspection_id == insp.inspection_id,
                        InspectionHistory.company_id == insp.company_id,
                        extract('year', InspectionHistory.date) == now.year,
                        extract('month', InspectionHistory.date) == now.month,
                    )
                    .all()
                )
            else:
                existing_histories = (
                    db.query(InspectionHistory)
                    .filter(
                        InspectionHistory.inspection_id == insp.inspection_id,
                        InspectionHistory.company_id == insp.company_id,
                        InspectionHistory.date >= datetime.combine(today_date, datetime.min.time()),
                        InspectionHistory.date <= datetime.combine(today_date, datetime.max.time()),
                    )
                    .all()
                )

            existing_locations = {h.location for h in existing_histories}
            
            user_name_snapshot = insp.user.name if insp.user else None

            for loc in locations:
                if loc not in existing_locations:
                    new_history = InspectionHistory(
                        company_id=insp.company_id,
                        inspection_id=insp.inspection_id,
                        uid=insp.uid,
                        user_name=user_name_snapshot,
                        name=insp.name,
                        location=loc,
                        date=now,
                        status='점검 대기',
                        is_action_required=False,
                        content=f'[{insp.cycle}] 정기 점검 자동 생성 건입니다.',
                    )
                    db.add(new_history)
                    created_count += 1

    db.commit()
    return created_count
