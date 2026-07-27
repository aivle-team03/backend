from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    user_id: str
    name: str
    role: Optional[str] = None
    category: Optional[str] = None
    company_code: Optional[str] = None


class UserResponse(UserBase):
    uid: int
    company_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserName(BaseModel):
    name: str

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str
    code: Optional[str] = None                                                # 회원가입 코드 (입력 시 역할/카테고리 자동 부여)


class UserLogin(BaseModel):
    user_id: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class PasswordReset(BaseModel):
    user_id: str
    name: str
    new_password: str


class NotificationToggleRequest(BaseModel):
    is_alert_enabled: bool
    item: str


class PasswordFindResponse(BaseModel):
    user_id: str
    name: str
    message: str


class UserRoleUpdateRequest(BaseModel):
    role: Optional[str] = None
    category: Optional[str] = None
