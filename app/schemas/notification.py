from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# 1. 알림 생성 요청 스키마 (필요 시 사용)
class NotificationCreate(BaseModel):
    category: str                    # 'schedule', 'danger', 'complete'
    title: str                       # 알림 제목 (예: '조치 완료', '위험 신고 접수')
    message: str                     # 알림 상세 내용
    path: Optional[str] = None       # 클릭 시 이동할 URL 경로 (예: '/actions', '/board')
    user_id: Optional[int] = None    # 특정 유저 지정 시 uid, 전체/공통 알림 시 None


# 2. 헤더 알림 목록 응답 스키마 (Header 드롭다운 전용)
class NotificationResponse(BaseModel):
    id: int
    category: str                    # 'schedule', 'danger', 'complete'
    title: str
    message: str
    time: str                        # 상대 시간 ('방금 전', '10분 전', '1시간 전' 등)
    path: Optional[str] = None
    read: bool

    class Config:
        from_attributes = True        # Pydantic V2 (V1인 경우 orm_mode = True)


# 3. 알림 처리 결과 응답 스키마 (읽음 처리 완료 등)
class NotificationActionResponse(BaseModel):
    status: str
    message: Optional[str] = None