from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class ReportCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="보고서 본문 내용")
    event_ids: Optional[List[int]] = Field(default=[], description="연결된 이벤트 ID 목록")
    action_history_ids: List[int] = Field(
        default_factory=list,
        description="연결된 조치 이력 ID 목록",
    )

    @field_validator("action_history_ids")
    @classmethod
    def validate_action_history_ids(cls, values: List[int]) -> List[int]:
        if any(value <= 0 for value in values):
            raise ValueError("action_history_ids는 양의 정수여야 합니다.")
        if len(values) != len(set(values)):
            raise ValueError("action_history_ids에 중복값을 사용할 수 없습니다.")
        return values

class ReportUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="수정할 보고서 제목")

class ReportDetailResponse(BaseModel):
    report_id: int
    company_id: int
    uid: Optional[int] = None
    path: str
    title: str
    created_at: datetime
    event_ids: List[int] = []
    action_history_ids: List[int] = Field(default_factory=list)
    writer: Optional[str] = None

    class Config:
        from_attributes = True

class ReportListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ReportDetailResponse]
