from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class AgentSessionResponse(BaseModel):
    uid: int
    role: str


class AgentInspectionItem(BaseModel):
    inspection_id: int
    category_id: int
    category: Optional[str] = None
    category_name: Optional[str] = None
    category_level: Optional[int] = None
    uid: Optional[int] = None
    user_name: Optional[str] = None
    name: str
    location: str
    cycle: str
    content: Optional[str] = None


class AgentInspectionHistoryItem(BaseModel):
    inspection_history_id: int
    inspection_id: int
    category_id: Optional[int] = None
    category: Optional[str] = None
    category_name: Optional[str] = None
    category_level: Optional[int] = None
    uid: Optional[int] = None
    user_name: Optional[str] = None
    name: str
    location: str
    date: datetime
    status: str
    is_action_required: bool
    content: Optional[str] = None


class AgentActionHistoryItem(BaseModel):
    action_history_id: int
    inspection_history_id: Optional[int] = None
    category_id: int
    category: Optional[str] = None
    category_name: Optional[str] = None
    category_level: Optional[int] = None
    handler_uid: Optional[int] = None
    handler_name: Optional[str] = None
    approver_uid: Optional[int] = None
    approver_name: Optional[str] = None
    action_name: str
    source_type: str
    source_id: Optional[int] = None
    location: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    action_status: str
    content: str
    approval_status: Optional[str] = None
    approval_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class AgentInspectionListResponse(BaseModel):
    items: List[AgentInspectionItem]
    total_items: int
    offset: int
    limit: int


class AgentInspectionHistoryListResponse(BaseModel):
    items: List[AgentInspectionHistoryItem]
    total_items: int
    offset: int
    limit: int
    summary: Dict[str, int]


class AgentActionHistoryListResponse(BaseModel):
    items: List[AgentActionHistoryItem]
    total_items: int
    offset: int
    limit: int
    summary: Dict[str, int]
