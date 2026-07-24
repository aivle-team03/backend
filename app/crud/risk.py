from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Tuple, Dict

from app.models import EventCategory, Event
from app.schemas.event_category import (
    RiskFactorResponse,
    CategoryGraphData,
    RiskManagementDashboardResponse,
    EventCategoryCreate,
    EventCategoryLevelUpdate
)


def calculate_risk_level(level: int, frequency: int) -> str:
    """
    위험도 산출 공식: 강도(level: 1~10) + 빈도(frequency) * 0.05
    - 8.0 이상: '상'
    - 4.0 이상 ~ 8.0 미만: '중'
    - 4.0 미만: '하'
    """
    score = level + (frequency * 0.05)
    
    if score >= 8.0:
        return "상"
    elif score >= 4.0:
        return "중"
    else:
        return "하"

def get_risk_category_list(db: Session) -> List[RiskFactorResponse]:
    """
    복잡한 대시보드 객체 대신, 단순 카테고리 리스트 배열만 반환
    """
    categories = db.query(EventCategory).all()

    # Event 카운트 집계
    event_counts = (
        db.query(Event.category_id, func.count(Event.event_id).label("cnt"))
        .group_by(Event.category_id)
        .all()
    )
    freq_map: Dict[int, int] = {cat_id: cnt for cat_id, cnt in event_counts}

    risk_factors = []
    for cat in categories:
        frequency = freq_map.get(cat.category_id, 0)
        risk_str = calculate_risk_level(cat.level, frequency)

        risk_factors.append(
            RiskFactorResponse(
                category_id=cat.category_id,
                category=cat.category,
                category_name=cat.category_name,
                risk_level=risk_str,
                level=cat.level,
                frequency=frequency,
            )
        )

    return risk_factors


def get_risk_dashboard_data(db: Session) -> RiskManagementDashboardResponse:
    categories = db.query(EventCategory).all()

    # 1. 카테고리별 Event 빈도(count) 집계
    event_counts = (
        db.query(Event.category_id, func.count(Event.event_id).label("cnt"))
        .group_by(Event.category_id)
        .all()
    )
    freq_map: Dict[int, int] = {cat_id: cnt for cat_id, cnt in event_counts}

    risk_factors: List[RiskFactorResponse] = []
    graph_dict: Dict[str, int] = {}
    total_risk_count = 0

    for cat in categories:
        frequency = freq_map.get(cat.category_id, 0)
        total_risk_count += frequency

        risk_str = calculate_risk_level(cat.level, frequency)

        risk_factors.append(
            RiskFactorResponse(
                category_id=cat.category_id,
                category=cat.category,
                category_name=cat.category_name,
                risk_level=risk_str,
                level=cat.level,
                frequency=frequency,
            )
        )

        graph_dict[cat.category] = graph_dict.get(cat.category, 0) + frequency

    graph_data = [
        CategoryGraphData(category=k, count=v) for k, v in graph_dict.items()
    ]

    return RiskManagementDashboardResponse(
        total_risk_count=total_risk_count,
        graph_data=graph_data,
        risk_factors=risk_factors,
    )


def update_event_category_level(db: Session, category_id: int, new_level: int) -> EventCategory:
    category = db.query(EventCategory).filter(EventCategory.category_id == category_id).first()
    if category:
        category.level = new_level
        db.commit()
        db.refresh(category)
    return category


def create_event_category(db: Session, payload: EventCategoryCreate) -> EventCategory:
    new_cat = EventCategory(
        category=payload.category,
        category_name=payload.category_name,
        level=payload.level,
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


def delete_event_category(db: Session, category_id: int) -> bool:
    category = db.query(EventCategory).filter(EventCategory.category_id == category_id).first()
    if not category:
        return False
    
    db.delete(category)
    db.commit()
    return True