from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class EventCategoryInfo(BaseModel):
    category_id: int
    company_id: int
    category: str
    category_name: str

    class Config:
        from_attribute = True
        orm_mode = True

class CCTVInfo(BaseModel):
    cctv_id: int = Field(None, validation_alias="camera_id")
    company_id: int
    cctv_name: str = Field(None, validation_alias="camera_name")
    location: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class EventDetailResponse(BaseModel):
    event_id: int = Field(None, validation_alias="camera_id")
    company_id: int
    category_id: Optional[int] = None
    cctv_id: Optional[int] = None
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
