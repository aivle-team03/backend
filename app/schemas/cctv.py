from pydantic import ConfigDict, BaseModel, Field
from typing import Optional


class CCTVCreate(BaseModel):
    cctv_name: str
    location: str
    stream_url: str
    status: Optional[str] = "정상"


class CCTVResponse(BaseModel):
    cctv_id: int
    company_id: int
    cctv_name: str
    location: str
    stream_url: str
    status: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
