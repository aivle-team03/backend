from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models import Notification
from app.schemas.notification import NotificationCreate


def create_notification(
    db: Session,
    company_id: int,
    category: str,
    title: str,
    message: str,
    path: Optional[str] = None,
    user_id: Optional[int] = None
) -> Notification:
    """새로운 알림을 생성하여 DB에 저장합니다."""
    db_noti = Notification(
        company_id=company_id,
        user_id=user_id,
        category=category,
        title=title,
        message=message,
        path=path,
        is_read=False
    )
    db.add(db_noti)
    db.commit()
    db.refresh(db_noti)
    return db_noti


def get_user_notifications(
    db: Session,
    company_id: int,
    user_id: int,
    user_role: str,
    limit: int = 20
) -> List[Notification]:
    """유저 권한에 맞춰 알림 목록을 최신순으로 조회합니다."""
    query = db.query(Notification).filter(Notification.company_id == company_id)

    if user_role == "안전관리자":
        # 안전관리자: 본인 타겟 알림 + 전체 공통 알림(user_id가 None인 것)
        query = query.filter(or_(Notification.user_id == user_id, Notification.user_id == None))
    else:
        # 일반 작업자: 본인에게 배정된 알림만 조회
        query = query.filter(Notification.user_id == user_id)

    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_as_read(
    db: Session,
    notification_id: int,
    company_id: int
) -> Optional[Notification]:
    """특정 알림 1건을 읽음(is_read=True) 처리합니다."""
    noti = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.company_id == company_id
    ).first()
    
    if noti:
        noti.is_read = True
        db.commit()
        db.refresh(noti)
    return noti


def mark_all_notifications_as_read(
    db: Session,
    company_id: int,
    user_id: int,
    user_role: str
) -> int:
    """해당 유저의 모든 미확인 알림을 읽음 처리합니다."""
    query = db.query(Notification).filter(
        Notification.company_id == company_id,
        Notification.is_read == False
    )

    if user_role == "안전관리자":
        query = query.filter(or_(Notification.user_id == user_id, Notification.user_id == None))
    else:
        query = query.filter(Notification.user_id == user_id)

    updated_count = query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return updated_count


def delete_notification(
    db: Session,
    notification_id: int,
    company_id: int
) -> bool:
    """특정 알림을 삭제합니다."""
    noti = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.company_id == company_id
    ).first()

    if noti:
        db.delete(noti)
        db.commit()
        return True
    return False