from datetime import date
from enum import Enum
from typing import List, Optional, Dict # Dict 추가

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
    due_date: Optional[date] = None 


class EducationStatusResponse(EducationResponse):
    status: EducationProgressStatus
    completed_date: Optional[date] = None

# UI기반작성
# 유저 상단 요약 카운트 응답
class UserEducationSummaryResponse(BaseModel):
    due_this_week_count: int
    in_progress_count: int
    completed_count: int


# 유저 이수율 현황 (차트용)
class UserCompletionRatesResponse(BaseModel):
    essential_rate: float    # 필수 교육 이수율
    regular_rate: float      # 정기 교육 이수율
    total_rate: float        # 전체 이수율

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
    due_date: Optional[date] = None
    target_count: int
    status_counts: List[EducationStatusCount]
    completion_rate: float


class EducationCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: int
    education_id: int
    status: EducationProgressStatus
    completed_date: date


# 관리자용 직군별 이수 현황 통계
class AdminRoleCompletionItem(BaseModel):
    role: str
    completion_rate: float
    target_count: int
    completed_count: int


class AdminRoleCompletionResponse(BaseModel):
    roles: List[AdminRoleCompletionItem]
    total_completion_rate: float


# AI 교육 자료 생성 요청/응답
class AIEducationGenerateRequest(BaseModel):
    work_type: str        # 작업 유형 (예: 용접/절단)
    equipment: str        # 사용 장비 (예: 지게차)
    risk_factor: str      # 위험 요인 (예: 충돌, 지침, 낙하)


class AIEducationGenerateResponse(BaseModel):
    education_id: Optional[int] = None
    title: str
    summary: str
    safety_guideline: List[str]
    generated_video_url: Optional[str] = None
