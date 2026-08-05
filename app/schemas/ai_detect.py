from pydantic import BaseModel
from typing import List, Optional

from datetime import datetime

from pydantic import BaseModel


class BBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

class DetectionResult(BaseModel):
    label: str
    confidence: float
    bbox: BBox

class FacilityDetectionResponse(BaseModel):
    status: str
    detections: List[DetectionResult]

class HazardDetectionResponse(BaseModel):
    risk_level: str
    detections: List[DetectionResult]
    description: str

class FireDetectionResponse(BaseModel):
    fire_detected: bool
    smoke_detected: bool
    confidence: float
    message: str

class VerifyActionResponse(BaseModel):
    similarity_score: float
    status: str
    description: str


class AIEventCreate(BaseModel):
    cctv_id: int
    category_id: int
    image_url: Optional[str] = None


class AIEventResponse(BaseModel):
    event_id: int
    company_id: int
    category_id: int
    cctv_id: int
    date: datetime
    image_url: Optional[str] = None
    is_deleted: int