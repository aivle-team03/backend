from typing import Optional

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel

from app.schemas.ai_detect import (
    FacilityDetectionResponse,
    FireDetectionResponse,
    HazardDetectionResponse,
    VerifyActionResponse,
)
from app.crud.ai_detect import (
    detect_facilities_sim,
    detect_fire_sim,
    detect_hazards_sim,
    verify_action_sim,
)
from app.services.ai.forklift_detection_service import (
    analyze_forklift_video,
)


router = APIRouter()


class ForkliftAnalyzeRequest(BaseModel):
    camera_id: int
    video_url: str


class ForkliftAnalyzeResponse(BaseModel):
    camera_id: int
    output_video_url: str
    danger_detected: bool
    total_frames: int
    danger_frames: int
    warning_frames: int
    minimum_distance_px: Optional[float] = None


@router.post(
    "/detect/facilities",
    response_model=FacilityDetectionResponse,
)
def post_detect_facilities(
    image: UploadFile = File(...),
):
    """
    소방시설 탐지 API
    """

    return detect_facilities_sim(
        image.filename
    )


@router.post(
    "/detect/hazards",
    response_model=HazardDetectionResponse,
)
def post_detect_hazards(
    image: UploadFile = File(...),
):
    """
    위험요소 탐지 API
    """

    return detect_hazards_sim(
        image.filename
    )


@router.post(
    "/detect/fire",
    response_model=FireDetectionResponse,
)
def post_detect_fire(
    image: UploadFile = File(...),
):
    """
    화재 징후 탐지 API
    """

    return detect_fire_sim(
        image.filename
    )


@router.post(
    "/verify-action",
    response_model=VerifyActionResponse,
)
def post_verify_action(
    before_img: UploadFile = File(...),
    after_img: UploadFile = File(...),
):
    """
    조치 결과 재확인 API
    """

    return verify_action_sim(
        before_img.filename,
        after_img.filename,
    )


@router.post(
    "/forklift/analyze",
    response_model=ForkliftAnalyzeResponse,
)
def post_analyze_forklift_video(
    request: ForkliftAnalyzeRequest,
):
    """
    지게차-작업자 거리 분석 API

    최종 URL:
    POST /api/ai/forklift/analyze
    """

    try:
        result = analyze_forklift_video(
            request.video_url
        )

        return {
            "camera_id": request.camera_id,
            "output_video_url": (
                result["output_video_url"]
            ),
            "danger_detected": (
                result["danger_detected"]
            ),
            "total_frames": (
                result["total_frames"]
            ),
            "danger_frames": (
                result["danger_frames"]
            ),
            "warning_frames": (
                result["warning_frames"]
            ),
            "minimum_distance_px": (
                result[
                    "minimum_distance_px"
                ]
            ),
        }

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI 영상 분석 중 오류가 "
                f"발생했습니다: {error}"
            ),
        ) from error