from pydantic import BaseModel
from typing import List

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
