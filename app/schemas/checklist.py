from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ChecklistResponse(BaseModel):
    checklist_id: int
    event_id: Optional[int] = None
    date: datetime
    status: str
    uid: int
    camera_id: int
    content: str
    image_url: Optional[str] = None

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
