from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    user_id: str
    name: str
    role: str
    company_code: Optional[str] = None

class UserResponse(UserBase):
    uid: int
    created_at: datetime
    class Config:
        orm_mode = True 

class UserName(BaseModel):
    name: str
    class Config:
        orm_mode = True

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    user_id: str
    password: str