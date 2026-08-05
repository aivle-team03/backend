from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from sqlalchemy.orm import Session

from app.db.db import get_db

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

@router.post("/verify-action", response_model=VerifyActionResponse)
def post_verify_action(before_img: UploadFile = File(...), after_img: UploadFile = File(...)):
    """조치결과 재확인 API - 명세서 URL /api/ai/verify-action (요구사항 APP-18-56-54)"""
    return verify_action_sim(before_img.filename, after_img.filename)

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
        "cctv_id": event.cctv_id,
        "category_id": event.category_id,
    }