import re
from pydantic import ConfigDict, BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


def validate_password_strength(v: str) -> str:
    """비밀번호 정책. 가입·변경·재설정이 모두 이 함수를 쓴다.

    한 곳에만 걸어두면 다른 경로로 우회된다. 실제로 재설정에는 검증이 없어
    가입 때 막히는 값이 그대로 통과했다.
    """
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
        return validate_password_strength(v)


class UserLogin(BaseModel):
    user_id: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordReset(BaseModel):
    user_id: str
    name: str
    code: str            # 관리자가 발급한 1회용 재설정 코드
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordResetCodeResponse(BaseModel):
    code: str
    target_uid: int
    target_name: str
    expires_in_hours: int


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