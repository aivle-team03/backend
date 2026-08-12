from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class EventCategoryInfo(BaseModel):
    category_id: int
    company_id: int
    category: str
    category_name: str

    model_config = ConfigDict(from_attributes=True)

class CCTVInfo(BaseModel):
    cctv_id: int
    company_id: int
    cctv_name: str
    location: str

    model_config = ConfigDict(from_attributes=True)

class EventDetailResponse(BaseModel):
    event_id: int
    company_id: int
    category_id: Optional[int] = None
    cctv_id: Optional[int] = None
    date: datetime
    image_url: Optional[str] = None
    category: Optional[EventCategoryInfo] = None
    cctv: Optional[CCTVInfo] = None
    current_status: str = "미조치"

    model_config = ConfigDict(from_attributes=True)

class ActionRequest(BaseModel):
    target_uid: int
    message: str

class ActionRequestResponse(BaseModel):
    action_history_id: int
    company_id: int
    event_id: Optional[int] = None
    created_at: datetime
    action_status: str
    handler_uid: Optional[int] = None
    location: str
    content: str
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
