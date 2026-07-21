from pydantic import BaseModel, Field

class CCTVResponse(BaseModel):
    cctv_id: int = Field(..., alias="camera_id")
    camera_name: str
    location: str
    stream_url: str
    status: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class CCTVStreamResponse(BaseModel):
    stream_url: str
