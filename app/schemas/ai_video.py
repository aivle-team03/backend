from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class VideoGenerateResponse(BaseModel):
    task_id: str
    status: str
    message: str


class VideoStatusResponse(BaseModel):
    task_id: str
    status: str
    progress_percent: int
    video_url: Optional[str] = None
    education_id: Optional[int] = None
    extracted_text: Optional[str] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    document_analysis: Optional[Dict[str, Any]] = None
    learning_objectives: Optional[List[str]] = None
    storyboard: Optional[List[Dict[str, Any]]] = None
    quality_report: Optional[Dict[str, Any]] = None
