from pydantic import BaseModel
from typing import List, Optional

from datetime import datetime

from pydantic import BaseModel

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