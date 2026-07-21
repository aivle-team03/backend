from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReportCreateRequest(BaseModel):
    # [Refactor] 빈 문자열 방지 및 길이 제한 추가 (DB 사이즈에 맞춰 max_length 조절)
    content: str = Field(..., min_length=1, max_length=5000, description="보고서 본문 내용")
    event_ids: Optional[List[int]] = Field(default=[], description="연결된 이벤트 ID 목록")
    checklist_ids: Optional[List[int]] = Field(default=[], description="연결된 체크리스트 ID 목록")


class ReportUpdateRequest(BaseModel):
    # [Refactor] 수정 시에도 동일한 유효성 검사 적용
    content: str = Field(..., min_length=1, max_length=5000, description="수정할 보고서 본문 내용")


class ReportDetailResponse(BaseModel):
    report_id: int
    uid: int
    content: str
    summary: Optional[str] = None
    created_at: datetime
    event_ids: List[int] = []
    checklist_ids: List[int] = []

    class Config:
        from_attributes = True # ORM 객체를 이 스키마로 자동 변환 (V2 표준)


class ReportListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ReportDetailResponse]