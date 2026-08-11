from fastapi import APIRouter, Depends, Form, HTTPException, status, UploadFile, File
from typing import List
from sqlalchemy.orm import Session
from typing import Optional

from app.db.db import get_db
from app.models import ActionHistory

from app.schemas.ai_detect import (
    AIEventCreate,
    FacilityDetectionResponse,
    HazardDetectionResponse,
    FireDetectionResponse,
    VerifyActionResponse
)
from app.crud.ai_detect import (
    create_ai_event,
    detect_facilities_sim,
    detect_hazards_sim,
    detect_fire_sim,
    verify_action_sim
)

router = APIRouter()

@router.post("/detect/facilities", response_model=FacilityDetectionResponse)
def post_detect_facilities(image: UploadFile = File(...)):
    """소방시설 탐지 API - 명세서 URL /api/ai/detect/facilities (요구사항 ADM-39-81-38)"""
    return detect_facilities_sim(image.filename)

@router.post("/detect/hazards", response_model=HazardDetectionResponse)
def post_detect_hazards(image: UploadFile = File(...)):
    """위험요소 탐지 API - 명세서 URL /api/ai/detect/hazards (요구사항 ADM-39-82-39)"""
    return detect_hazards_sim(image.filename)

@router.post("/detect/fire", response_model=FireDetectionResponse)
def post_detect_fire(image: UploadFile = File(...)):
    """화재 징후 탐지 API - 명세서 URL /api/ai/detect/fire (요구사항 ADM-39-83-40)"""
    return detect_fire_sim(image.filename)

@router.post("/events", status_code=status.HTTP_201_CREATED)
def post_ai_event(
    event: AIEventCreate,
    db: Session = Depends(get_db),
):
    result = create_ai_event(
        db=db,
        cctv_id=event.cctv_id,
        category_id=event.category_id,
        image_url=event.image_url,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV를 찾을 수 없습니다.",
        )

    return {
        "message": "이벤트 저장 완료",
        "event_id": result["event_id"],
        "cctv_id": event.cctv_id,
        "category_id": event.category_id,
    }
    
@router.post("/verify-action")
async def post_verify_action(
    after_img: UploadFile = File(...),
    category_name: Optional[str] = Form("안전 위험 요인"),
    action_history_id: Optional[int] = Form(None),
    action_content: Optional[str] = Form(""),
    db: Session = Depends(get_db)
):
    before_image_path = None
    if action_history_id and db:
        action = db.query(ActionHistory).filter(
            ActionHistory.action_history_id == action_history_id
        ).first()
        if action:
            before_image_path = action.before_image_url
    
    result = await verify_action_sim(
        after_img=after_img,
        category_name=category_name,
        action_history_id=action_history_id,
        action_content=action_content,
        before_image_path=before_image_path,
        db=db
    )
    return result