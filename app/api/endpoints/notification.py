from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.db import get_db
from app.models import User
from app.schemas.notification import NotificationResponse, NotificationActionResponse
from app.crud.auth import get_current_user
from app.crud.notification import (
    get_user_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification,
)

router = APIRouter()


def format_relative_time(dt: datetime) -> str:
    """생성 시간을 '방금 전', '10분 전', '1시간 전' 문자열로 변환"""
    if not dt:
        return "방금 전"
    now = datetime.now()
    diff = now - (dt.replace(tzinfo=None) if dt.tzinfo else dt)
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "방금 전"
    elif seconds < 3600:
        return f"{seconds // 60}분 전"
    elif seconds < 86400:
        return f"{seconds // 3600}시간 전"
    elif diff.days < 7:
        return f"{diff.days}일 전"
    else:
        return dt.strftime("%Y-%m-%d")


# 1. 알림 목록 조회 (GET /api/notifications)
@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notis = get_user_notifications(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.uid,
        user_role=current_user.role,
        limit=20
    )

    return [
        {
            "id": n.id,
            "category": n.category,
            "title": n.title,
            "message": n.message,
            "time": format_relative_time(n.created_at),
            "path": n.path,
            "read": n.is_read,
        }
        for n in notis
    ]


# 2. 전체 알림 읽음 처리 (PATCH /api/notifications/read-all)
@router.patch("/read-all", response_model=NotificationActionResponse)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = mark_all_notifications_as_read(
        db=db,
        company_id=current_user.company_id,
        user_id=current_user.uid,
        user_role=current_user.role
    )
    return {"status": "success", "message": f"{count}개의 알림을 읽음 처리했습니다."}


# 3. 단일 알림 읽음 처리 (PATCH /api/notifications/{notification_id}/read)
@router.patch("/{notification_id}/read", response_model=NotificationActionResponse)
def read_single_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    noti = mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        company_id=current_user.company_id
    )
    if not noti:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    return {"status": "success", "message": "알림을 읽음 처리했습니다."}


# 4. 단일 알림 삭제 (DELETE /api/notifications/{notification_id})
@router.delete("/{notification_id}", response_model=NotificationActionResponse)
def remove_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = delete_notification(
        db=db,
        notification_id=notification_id,
        company_id=current_user.company_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    return {"status": "success", "message": "알림이 삭제되었습니다."}