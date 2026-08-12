from pydantic import ConfigDict, BaseModel
from datetime import datetime
from typing import Optional, List


class SignupCodeCreate(BaseModel):
    role: str                                                                  # 안전관리자, 관제사, 현장관리자, 일반유저
    category: Optional[str] = None                                             # 일반유저 선택 시 카테고리 (지게차, 화물트럭 등)


class SignupCodeResponse(BaseModel):
    id: int
    company_id: int
    code: str
    role: str
    category: Optional[str] = None
    is_used: bool
    used_by_uid: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    categories: List[str]
