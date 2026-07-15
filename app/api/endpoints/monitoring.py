from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.db import get_db
from app.schemas.monitoring import EventDetailResponse, ActionRequest, ActionRequestResponse
from app.crud.monitoring import get_monitoring_events, get_monitoring_event_by_id, create_action_request

router = APIRouter()

@router.get("/events", response_model=List[EventDetailResponse])
def read_monitoring_events(
    cctv_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    events = get_monitoring_events(db, cctv_id=cctv_id, status=status, skip=skip, limit=limit)
    return events

@router.get("/events/{event_id}", response_model=EventDetailResponse)
def read_monitoring_event(event_id: int, db: Session = Depends(get_db)):
    event = get_monitoring_event_by_id(db, event_id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이벤트를 찾을 수 없습니다."
        )
    return event

@router.post("/events/{event_id}/request", response_model=ActionRequestResponse)
def post_action_request(event_id: int, action_req: ActionRequest, db: Session = Depends(get_db)):
    """현장 조치 요청 발송 API - 명세서 URL /api/monitoring/events/{event_id}/request (요구사항 ADM-39-80-37)"""
    db_checklist = create_action_request(
        db,
        event_id=event_id,
        target_uid=action_req.target_uid,
        message=action_req.message
    )
    if db_checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이벤트를 찾을 수 없거나 조치 요청 생성에 실패했습니다."
        )
    return db_checklist
