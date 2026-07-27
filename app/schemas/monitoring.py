from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class EventCategoryInfo(BaseModel):
    category_id: int
    category: str
    category_name: str

    class Config:
        from_attribute = True
        orm_mode = True

class CCTVInfo(BaseModel):
    cctv_id: int = Field(None, validation_alias="camera_id")
    cctv_name: str = Field(None, validation_alias="camera_name")
    location: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class EventDetailResponse(BaseModel):
    event_id: int = Field(None, validation_alias="camera_id")
    category_id: int
    cctv_id: int
    date: datetime
    image_url: Optional[str] = None
    category: Optional[EventCategoryInfo] = None
    cctv: Optional[CCTVInfo] = None
    current_status: str = "미조치"

    class Config:
        from_attribute = True
        orm_mode = True
        allow_population_by_field_name = True

class ActionRequest(BaseModel):
    target_uid: int
    message: str

class ActionRequestResponse(BaseModel):
    checklist_id: int
    event_id: int
    date: datetime
    status: str
    uid: int
    camera_id: int
    content: str
    image_url: Optional[str] = None

    class Config:
        from_attribute = True
        orm_mode = True
