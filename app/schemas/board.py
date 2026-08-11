# app/schemas/board.py
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

from app.utils.media import public_url

# 게시글 응답 기본 스키마
class BoardResponse(BaseModel):
    board_id: int
    company_id: int
    uid: Optional[int] = None
    writer: Optional[str] = "알 수 없음"
    title: str
    board_contents: str
    event_category_id: Optional[int] = None
    status: str
    location: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("image_url", mode="before")
    @classmethod
    def make_full_image_url(cls, value):
        return public_url(value)

    class Config:
        from_attributes = True

# 목록 조회 시 페이징 응답 스키마
class BoardListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[BoardResponse]

# 상태 변경 요청 스키마
class BoardStatusUpdateRequest(BaseModel):
    status: str
