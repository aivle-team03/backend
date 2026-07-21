from pydantic import BaseModel
from datetime import datetime
from typing import List

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
        orm_mode = True

class ReportSummaryResponse(BaseModel):
    report_id: int
    summary: str
    ai_analysis: str
