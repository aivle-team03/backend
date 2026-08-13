import re
from pydantic import ConfigDict, BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    user_id: str
    name: str
    company_id: Optional[int] = None
    role: Optional[str] = None
    category: Optional[str] = None
    company_code: Optional[str] = None


class UserResponse(UserBase):
    uid: int
    company_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserName(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: str
    code: Optional[str] = None  # 회원가입 코드

    @field_validator('password')
    @classmethod
    def validate_password_rules(cls, v: str) -> str:
        # 1. 최소 길이 검증 (10자리 이상)
        if len(v) < 10:
            raise ValueError('비밀번호는 최소 10자리 이상이어야 합니다.')

        # 2. 문자 종류 수 계산 (영대문자, 영소문자, 숫자, 특수문자)
        types_count = 0
        if re.search(r'[A-Z]', v):          # 영대문자
            types_count += 1
        if re.search(r'[a-z]', v):          # 영소문자
            types_count += 1
        if re.search(r'\d', v):              # 숫자
            types_count += 1
        if re.search(r'[^A-Za-z0-9()<>"\'\;]', v):
            types_count += 1

        # 3. 3종류 이상 조합 검증
        if types_count < 3:
            raise ValueError('비밀번호는 영대문자, 영소문자, 숫자, 특수문자 중 3종류 이상을 조합해야 합니다.')

        return v


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

class UserDeleteRequest(BaseModel):
    password: str = Field(..., description="본인 확인용 현재 비밀번호")