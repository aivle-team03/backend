from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List

from app.schemas.ai_detect import (
    FacilityDetectionResponse,
    HazardDetectionResponse,
    FireDetectionResponse,
    VerifyActionResponse
)
from app.crud.ai_detect import (
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
