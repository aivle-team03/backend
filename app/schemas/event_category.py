from pydantic import BaseModel
from typing import List


class EventCategoryCreate(BaseModel):
    category: str
    category_name: str
    level: int = 1


class EventCategoryLevelUpdate(BaseModel):
    level: int


class RiskFactorResponse(BaseModel):
    category_id: int
    category: str           # 유형 (예: 소방)
    category_name: str      # 항목 (예: 화재)
    risk_level: str         # 위험도 ('상', '중', '하')
    level: int              # 강도
    frequency: int          # 빈도 (해당 카테고리의 Event 수)

    class Config:
        from_attributes = True


class CategoryGraphData(BaseModel):
    category: str           # 유형명 (소방, 시설, 안전 등)
    count: int              # 해당 유형에 속한 총 이벤트 건수


class RiskManagementDashboardResponse(BaseModel):
    total_risk_count: int                   # 전체 위험 요인 갯수 (총 이벤트 건수)
    graph_data: List[CategoryGraphData]     # 유형별 차트 데이터
    risk_factors: List[RiskFactorResponse]   # 위험 요인 리스트