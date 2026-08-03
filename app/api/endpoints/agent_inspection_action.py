from datetime import date, datetime, time
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import agent_inspection_action as agent_crud
from app.crud.auth import get_current_admin
from app.db.agent_read_db import get_agent_read_db
from app.models import User
from app.schemas.agent_inspection_action import (
    AgentActionHistoryItem,
    AgentActionHistoryListResponse,
    AgentInspectionHistoryItem,
    AgentInspectionHistoryListResponse,
    AgentInspectionItem,
    AgentInspectionListResponse,
    AgentSessionResponse,
)


router = APIRouter()


@router.get("/session", response_model=AgentSessionResponse)
def read_agent_session(
    current_admin: User = Depends(get_current_admin),
):
    return AgentSessionResponse(uid=current_admin.uid, role=current_admin.role)


@router.get("/inspections", response_model=AgentInspectionListResponse)
def read_agent_inspections(
    keyword: Optional[str] = Query(None, max_length=100),
    category_id: Optional[int] = Query(None, gt=0),
    uid: Optional[int] = Query(None, gt=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_agent_read_db),
):
    return agent_crud.get_inspections(
        db,
        company_id=current_admin.company_id,
        keyword=keyword,
        category_id=category_id,
        uid=uid,
        offset=offset,
        limit=limit,
    )


@router.get("/inspections/{inspection_id}", response_model=AgentInspectionItem)
def read_agent_inspection_detail(
    inspection_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_agent_read_db),
):
    result = agent_crud.get_inspections(
        db,
        company_id=current_admin.company_id,
        inspection_id=inspection_id,
        offset=0,
        limit=1,
    )
    if not result["items"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="점검 항목을 찾을 수 없습니다.",
        )
    return result["items"][0]


@router.get(
    "/inspection-histories",
    response_model=AgentInspectionHistoryListResponse,
)
def read_agent_inspection_histories(
    inspection_id: Optional[int] = Query(None, gt=0),
    keyword: Optional[str] = Query(None, max_length=100),
    status_filter: Optional[Literal["점검 대기", "점검 완료"]] = Query(None),
    is_action_required: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_agent_read_db),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from은 date_to보다 늦을 수 없습니다.",
        )
    return agent_crud.get_inspection_histories(
        db,
        company_id=current_admin.company_id,
        inspection_id=inspection_id,
        keyword=keyword,
        status=status_filter,
        is_action_required=is_action_required,
        date_from=datetime.combine(date_from, time.min) if date_from else None,
        date_to=datetime.combine(date_to, time.max) if date_to else None,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/inspection-histories/{inspection_history_id}",
    response_model=AgentInspectionHistoryItem,
)
def read_agent_inspection_history_detail(
    inspection_history_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_agent_read_db),
):
    result = agent_crud.get_inspection_histories(
        db,
        company_id=current_admin.company_id,
        inspection_history_id=inspection_history_id,
        offset=0,
        limit=1,
    )
    if not result["items"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="점검 이력을 찾을 수 없습니다.",
        )
    return result["items"][0]


@router.get("/action-histories", response_model=AgentActionHistoryListResponse)
def read_agent_action_histories(
    keyword: Optional[str] = Query(None, max_length=100),
    source_type: Optional[
        Literal["게시판", "이벤트", "점검이력", "직접추가"]
    ] = Query(None),
    category_id: Optional[int] = Query(None, gt=0),
    action_status: Optional[Literal["조치 대기", "조치 완료"]] = Query(None),
    approval_status: Optional[
        Literal["승인 대기", "승인 완료", "반려"]
    ] = Query(None),
    handler_uid: Optional[int] = Query(None, gt=0),
    unassigned: Optional[bool] = Query(None),
    created_from: Optional[date] = Query(None),
    created_to: Optional[date] = Query(None),
    completed_from: Optional[date] = Query(None),
    completed_to: Optional[date] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_agent_read_db),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="created_from은 created_to보다 늦을 수 없습니다.",
        )
    if completed_from and completed_to and completed_from > completed_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="completed_from은 completed_to보다 늦을 수 없습니다.",
        )
    return agent_crud.get_action_histories(
        db,
        company_id=current_admin.company_id,
        keyword=keyword,
        source_type=source_type,
        category_id=category_id,
        action_status=action_status,
        approval_status=approval_status,
        handler_uid=handler_uid,
        unassigned=unassigned,
        created_from=(
            datetime.combine(created_from, time.min) if created_from else None
        ),
        created_to=datetime.combine(created_to, time.max) if created_to else None,
        completed_from=(
            datetime.combine(completed_from, time.min)
            if completed_from
            else None
        ),
        completed_to=(
            datetime.combine(completed_to, time.max) if completed_to else None
        ),
        offset=offset,
        limit=limit,
    )


@router.get(
    "/action-histories/{action_history_id}",
    response_model=AgentActionHistoryItem,
)
def read_agent_action_history_detail(
    action_history_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_agent_read_db),
):
    result = agent_crud.get_action_histories(
        db,
        company_id=current_admin.company_id,
        action_history_id=action_history_id,
        offset=0,
        limit=1,
    )
    if not result["items"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="조치 이력을 찾을 수 없습니다.",
        )
    return result["items"][0]
