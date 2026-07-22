from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class DashboardSummaryResponse(BaseModel):
    detected_count: int
    violation_count: int
    pending_action_count: int
    completed_action_count: int


class RecentEventResponse(BaseModel):
    event_id: int
    category_name: str
    camera_name: str
    location: str
    date: datetime
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


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
    uid: int
    content: str
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReportSummaryResponse(BaseModel):
    report_id: int
    summary: str
    ai_analysis: str
