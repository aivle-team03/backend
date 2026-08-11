from pydantic import ConfigDict, BaseModel
from datetime import datetime
from typing import List, Optional


class DashboardSummaryResponse(BaseModel):
    detected_count: int
    violation_count: int
    pending_action_count: int
    completed_action_count: int


class RecentEventResponse(BaseModel):
    event_id: int
    company_id: int
    category_name: str
    cctv_name: str
    location: str
    date: datetime
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ZoneStatsResponse(BaseModel):
    location: str
    cctv_count: int
    event_count: int
    risk_index: float


class SafetyGradeResponse(BaseModel):
    score: int
    grade: str
    reason: str


class ReportResponse(BaseModel):
    report_id: int
    company_id: int
    uid: int
    content: str
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportSummaryResponse(BaseModel):
    report_id: int
    company_id: int
    summary: str
    ai_analysis: str
