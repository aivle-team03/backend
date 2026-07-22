from pydantic import BaseModel, Field
from typing import Optional


class CCTVCreate(BaseModel):
    camera_name: str
    location: str
    stream_url: str
    status: Optional[str] = "정상"


class CCTVResponse(BaseModel):
    cctv_id: int = Field(..., alias="camera_id")
    camera_name: str
    location: str
    stream_url: str
    status: str

    class Config:
        from_attributes = True
        populate_by_name = True


class CCTVStreamResponse(BaseModel):
    stream_url: str
