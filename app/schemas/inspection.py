from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# ==========================================
# 1. Inspection (점검 항목 Master) 스키마
# ==========================================


# 공통 필드 (Base)
class InspectionBase(BaseModel):
    name: str
    category_id: int
    location: str  # 예: "A동 1층, B동 3층"
    cycle: str
    content: Optional[str] = None


# 점검 생성 (POST Request)
class InspectionCreate(InspectionBase):
    pass  # company_id는 로그인한 유저 정보(JWT)에서 주입받으므로 생략 가능


# 점검 수정 (PATCH / PUT Request)
class InspectionUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    location: Optional[str] = None
    cycle: Optional[str] = None
    content: Optional[str] = None


# 점검 단건 응답 (Response)
class InspectionResponse(InspectionBase):
    inspection_id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. InspectionHistory (점검 수행 이력) 스키마
# ==========================================


# 공통 필드 (Base)
class InspectionHistoryBase(BaseModel):
    name: str
    date: datetime
    location: str  # 예: "A동 1층" (개별 구역)
    uid: Optional[int] = None
    status: str  # "점검 대기", "점검 완료"
    is_action_required: bool = False
    content: Optional[str] = None


# 점검 이력 등록 (POST Request)
class InspectionHistoryCreate(InspectionHistoryBase):
    inspection_id: int


# 점검 이력 상태 및 내용 수정 (PATCH Request)
class InspectionHistoryUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    uid: Optional[str] = None
    status: Optional[str] = None
    is_action_required: Optional[bool] = None
    content: Optional[str] = None


# 점검 이력 응답 (Response)
class InspectionHistoryResponse(InspectionHistoryBase):
    inspection_history_id: int
    inspection_id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. 상세 조회용 중첩 스키마 (Inspection + Histories)
# ==========================================


# 점검 항목 상세 조회 시 해당 점검의 전체 이력 목록까지 한 번에 반환할 때 사용
class InspectionDetailResponse(InspectionResponse):
    histories: List[InspectionHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)