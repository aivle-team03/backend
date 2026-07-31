import os
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


class SourceType(str, Enum):
    BOARD = "게시판"
    EVENT = "이벤트"
    INSPECTION_HISTORY = "점검이력"
    ADMIN_CREATED = "직접추가"


class ActionStatus(str, Enum):
    WAITING = "조치 대기"
    COMPLETED = "조치 완료"


class ApprovalStatus(str, Enum):
    PENDING = "승인 대기"
    APPROVED = "승인 완료"
    REJECTED = "반려"


class ActionHistoryCreateRequest(BaseModel):
    source_type: SourceType
    source_id: Optional[int] = Field(default=None, gt=0)
    action_name: Optional[str] = Field(default=None, max_length=200)
    category_id: Optional[int] = Field(default=None, gt=0)
    location: Optional[str] = Field(default=None, max_length=255)
    content: str
    handler_uid: Optional[int] = Field(default=None, gt=0)

    @field_validator("action_name", "location")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("조치 내용은 필수입니다.")
        return stripped

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_type == SourceType.ADMIN_CREATED:
            if self.source_id is not None:
                raise ValueError("직접추가 조치는 source_id를 사용할 수 없습니다.")

            missing_fields = [
                field_name
                for field_name in ("action_name", "category_id", "location")
                if getattr(self, field_name) is None
            ]
            if missing_fields:
                raise ValueError(
                    "직접추가 조치에는 action_name, category_id, location이 필수입니다."
                )
        elif self.source_id is None:
            raise ValueError("연결된 출처가 있는 조치는 source_id가 필수입니다.")

        return self


class ActionHistoryAssignRequest(BaseModel):
    action_history_ids: List[int] = Field(min_length=1)
    handler_uid: Optional[int] = Field(default=None, gt=0)

    @field_validator("action_history_ids")
    @classmethod
    def validate_action_history_ids(cls, values: List[int]) -> List[int]:
        if any(value <= 0 for value in values):
            raise ValueError("action_history_ids는 양의 정수여야 합니다.")
        if len(values) != len(set(values)):
            raise ValueError("action_history_ids에 중복값을 사용할 수 없습니다.")
        return values


class ActionHistoryRejectRequest(BaseModel):
    rejection_reason: str = Field(max_length=2000)

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("반려 사유는 필수입니다.")
        return stripped


class ActionHistoryListItem(BaseModel):
    action_history_id: int
    source_type: SourceType
    source_id: Optional[int] = None
    action_name: str
    category_id: Optional[int] = None
    category: Optional[str] = None
    category_name: str
    category_level: int
    location: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    handler_uid: Optional[int] = None
    handler_name: Optional[str] = None
    action_status: ActionStatus
    image_url: Optional[str] = None
    approval_status: Optional[ApprovalStatus] = None
    approver_uid: Optional[int] = None
    approver_name: Optional[str] = None
    approval_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("image_url", mode="before")
    @classmethod
    def make_full_image_url(cls, value):
        if value and isinstance(value, str) and value.startswith("/static/"):
            return f"{BACKEND_URL}{value}"
        return value


class ActionHistoryDetailResponse(ActionHistoryListItem):
    board_id: Optional[int] = None
    event_id: Optional[int] = None
    inspection_history_id: Optional[int] = None
    content: str
    rejection_reason: Optional[str] = None


class ActionHistorySummary(BaseModel):
    total_count: int
    waiting_count: int
    completed_count: int
    unassigned_count: int
    pending_approval_count: int
    approved_count: int
    approval_rate: float


class ActionHistoryListResponse(BaseModel):
    items: List[ActionHistoryListItem]
    page: int
    size: int
    total_items: int
    total_pages: int
    summary: ActionHistorySummary


class HandlerListItem(BaseModel):
    uid: int
    user_id: str
    name: str
    role: str
    category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HandlerListResponse(BaseModel):
    items: List[HandlerListItem]
    page: int
    size: int
    total_items: int
    total_pages: int
