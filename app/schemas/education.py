from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class EducationProgressStatus(str, Enum):
    INCOMPLETE = "미이수"
    IN_PROGRESS = "진행중"
    COMPLETED = "이수"


class EducationCompletionFilter(str, Enum):
    INCOMPLETE = "미이수"
    COMPLETED = "이수"


class EducationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    education_id: int
    title: str
    role: str
    video_url: str
    category: str
    type: str

class EducationStatusResponse(EducationResponse):
    status: EducationProgressStatus
    completed_date: Optional[date] = None


class UserEducationResponse(BaseModel):
    uid: int
    user_id: str
    name: str
    role: str
    educations: List[EducationStatusResponse]


class EducationStatusCount(BaseModel):
    status: EducationProgressStatus
    count: int


class EducationStatusSummaryResponse(BaseModel):
    education_id: int
    title: str
    role: str
    category: str
    type: str
    target_count: int
    status_counts: List[EducationStatusCount]
    completion_rate: float


class EducationCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: int
    education_id: int
    status: EducationProgressStatus
    completed_date: date
