from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models import Notification, User
from app.schemas.notification import NotificationCreate


def create_notification(
    db: Session,
    company_id: int,
    category: str,
    title: str,
    message: str,
    path: Optional[str] = None,
    user_id: Optional[int] = None
):
    """
    새로운 알림을 생성하여 DB에 저장합니다.
    - user_id 지정 시: 해당 사용자에게만 1개 생성
    - user_id=None 시: 해당 회사의 모든 관리자에게 각각 1:1 독립 레코드 생성
    """
    if user_id is not None:
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

    admin_query = db.query(User).filter(
        User.company_id == company_id,
        User.role.in_(["안전관리자"])
    )
    if hasattr(User, "is_deleted"):
        admin_query = admin_query.filter(User.is_deleted == False)
    
    admins = admin_query.all()
    created_notis = []

    for admin in admins:
        noti = Notification(
            company_id=company_id,
            user_id=admin.uid,
            category=category,
            title=title,
            message=message,
            path=path,
            is_read=False
        )
        db.add(noti)
        created_notis.append(noti)

    db.commit()
    return created_notis


def get_user_notifications(
    db: Session,
    company_id: int,
    user_id: int,
    user_role: str,
    limit: int = 20
) -> List[Notification]:
    """해당 유저에게 온 독립 알림 목록을 최신순으로 조회합니다."""
    return (
        db.query(Notification)
        .filter(
            Notification.company_id == company_id,
            Notification.user_id == user_id
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(
    db: Session,
    notification_id: int,
    company_id: int,
    user_id: int,
) -> Optional[Notification]:
    """특정 알림 1건을 읽음 처리합니다 (본인 알림만 가능)."""
    noti = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.company_id == company_id,
            Notification.user_id == user_id,
        )
        .first()
    )

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
    db: Session, notification_id: int, company_id: int, user_id: int
) -> bool:
    """특정 알림을 삭제합니다 (본인 알림만 가능)."""
    noti = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.company_id == company_id,
            Notification.user_id == user_id,
        )
        .first()
    )

    if noti:
        db.delete(noti)
        db.commit()
        return True
    return False

def delete_all_notifications(
    db: Session,
    company_id: int,
    user_id: int
) -> int:
    """사용자가 조회 가능한 모든 알림(본인 알림 + 공통 알림)을 일괄 삭제합니다."""
    query = db.query(Notification).filter(
        Notification.company_id == company_id,
        or_(Notification.user_id == user_id, Notification.user_id.is_(None))
    )
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    return deleted_count