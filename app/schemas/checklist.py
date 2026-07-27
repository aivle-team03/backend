from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

class ChecklistResponse(BaseModel):
    checklist_id: int
    event_id: Optional[int] = None
    date: datetime
    status: str
    uid: int
    camera_id: int
    content: str
    image_url: Optional[str] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def make_full_url(cls, v):
        if v and isinstance(v, str) and v.startswith("/static/"):
            return f"{BACKEND_URL}{v}"
        return v

    class Config:
        orm_mode = True

class ManagerSearchResponse(BaseModel):
    uid: int
    user_id: str
    name: str

    class Config:
        orm_mode = True

class AssignManagerRequest(BaseModel):
    user_id: str

class StatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None

class ChecklistCreate(BaseModel):
    event_id: Optional[int] = None
    camera_id: Optional[int] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
