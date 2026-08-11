from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.action_history import ActionHistory
from app.schemas.action_history import ActionStatus, SourceType
from app.utils.datetime_utils import get_kst_now
from app.utils.media import public_url
import httpx
from fastapi import UploadFile

AI_SERVER_URL = "http://127.0.0.1:8001"

def detect_facilities_sim(filename: str):
    return {
        "status": "안전",
        "detections": [
            {
                "label": "fire_extinguisher",
                "confidence": 0.96,
                "bbox": {"x_min": 120.5, "y_min": 340.0, "x_max": 210.0, "y_max": 510.5}
            }
        ]
    }

def detect_hazards_sim(filename: str):
    return {
        "risk_level": "High",
        "detections": [
            {
                "label": "cardboard_box",
                "confidence": 0.91,
                "bbox": {"x_min": 50.0, "y_min": 400.2, "x_max": 180.5, "y_max": 550.0}
            }
        ],
        "description": "비상구 탈출 통로 주변에 불법 가연성 적치물(박스)이 감지되어 대피 방해가 우려됩니다."
    }

def detect_fire_sim(filename: str):
    return {
        "fire_detected": True,
        "smoke_detected": True,
        "confidence": 0.98,
        "message": "CCTV 화면 내에서 고온의 불꽃 징후 및 농연(Smoke) 감지. 즉시 화재 수신기 점검 및 대피령 전파 권장."
    }

def create_ai_event(
    db: Session,
    cctv_id: int,
    category_id: int,
    image_url: Optional[str] = None,
):
    # CCTV의 company_id 조회
    cctv = db.execute(
        text("""
            SELECT company_id, location
            FROM cctv
            WHERE cctv_id = :cctv_id
              AND is_deleted = 0
        """),
        {"cctv_id": cctv_id},
    ).fetchone()

    if cctv is None:
        return None

    company_id, location = cctv
    category_name = db.execute(
        text("SELECT category_name FROM event_category WHERE category_id = :category_id"),
        {"category_id": category_id},
    ).scalar() or "AI 감지"

    # AI 서버는 백엔드 재시작/DB 일시 오류 때 같은 스냅샷을 재전송할 수 있다.
    # 스냅샷 URL을 멱등 키로 사용하면 event가 중복 생성되지 않고, 예전 실행에서
    # event만 저장되고 action_history가 빠진 경우에도 아래에서 함께 복구된다.
    existing_event_id = None
    if image_url:
        existing_event_id = db.execute(
            text("""
                SELECT event_id
                FROM event
                WHERE cctv_id = :cctv_id
                  AND category_id = :category_id
                  AND image_url = :image_url
                  AND is_deleted = 0
                ORDER BY event_id DESC
                LIMIT 1
            """),
            {
                "cctv_id": cctv_id,
                "category_id": category_id,
                "image_url": image_url,
            },
        ).scalar()

    if existing_event_id is not None:
        event_id = existing_event_id
        existing_action = db.query(ActionHistory.action_history_id).filter(
            ActionHistory.event_id == event_id,
            ActionHistory.type == SourceType.EVENT.value,
            ActionHistory.is_deleted == False,
        ).first()
        if existing_action is not None:
            return {"message": "이벤트가 이미 저장되어 있습니다", "event_id": event_id}
    else:
        # event 테이블 저장
        result = db.execute(
            text("""
                INSERT INTO event
                (
                    company_id,
                    category_id,
                    cctv_id,
                    date,
                    image_url,
                    is_deleted
                )
                VALUES
                (
                    :company_id,
                    :category_id,
                    :cctv_id,
                    :detected_at,
                    :image_url,
                    0
                )
            """),
            {
                "company_id": company_id,
                "category_id": category_id,
                "cctv_id": cctv_id,
                "image_url": image_url,
                "detected_at": get_kst_now(),
            },
        )
        event_id = result.lastrowid
    db.add(ActionHistory(
        company_id=company_id,
        event_id=event_id,
        category_id=category_id,
        handler_uid=None,
        handler_name=None,
        # 조치명은 이벤트 카테고리 자체를 사용한다. AI 감지 문구를 여기서
        # 하드코딩하지 않고, 상세 내용은 담당자가 조치 과정에서 작성한다.
        action_name=category_name,
        type=SourceType.EVENT.value,
        location=location,
        content="",
        before_image_url=image_url,
        image_url=None,
        action_status=ActionStatus.WAITING.value,
        approval_status=None,
        created_at=get_kst_now(),
    ))
    db.commit()

    return {
        "message": "이벤트 저장 완료",
        "event_id": event_id,
    }
    

async def verify_action_sim(
    after_img: UploadFile, 
    category_name: str = "안전 위험 요인",
    action_content: str = "",
    action_history_id: int | None = None,
    before_image_path: str | None = None,
    db: Session | None = None
) -> dict:
    try:
        after_bytes = await after_img.read()
        mime_type = after_img.content_type or "image/jpeg"

        async with httpx.AsyncClient() as client:
            files = {
                "after_img": (after_img.filename, after_bytes, mime_type)
            }
            data = {
                "category_name": category_name,
                "action_content": action_content
            }
            
            before_file_opened = None
            if before_image_path:
                # S3에 올라간 이미지는 /media/ 경로로 저장되어 로컬에 파일이 없다.
                # public_url()로 절대주소를 만들어 아래 HTTP 분기로 넘긴다.
                before_image_path = public_url(before_image_path) or before_image_path
                try:
                    if not before_image_path.startswith("http"):
                        clean_path = before_image_path.lstrip("/")
                        if clean_path.startswith("http"):
                            clean_path = clean_path.split("/static/")[-1]
                            clean_path = f"static/{clean_path}"

                        local_file = Path(clean_path)
                        if local_file.exists():
                            before_file_opened = open(local_file, "rb")
                            files["before_img"] = (
                                local_file.name,
                                before_file_opened.read(),
                                "image/jpeg"
                            )
                        else:
                            print(
                                f"[AIVerify] WARNING: before 이미지를 찾을 수 없어 "
                                f"없이 검증합니다: {before_image_path}",
                                flush=True,
                            )

                    else:
                        img_res = await client.get(before_image_path, timeout=5.0)
                        if img_res.status_code == 200:
                            files["before_img"] = (
                                "before_image.jpg",
                                img_res.content,
                                "image/jpeg"
                            )
                except Exception as img_err:
                    print(f"⚠️ [before_image_path 읽기 실패]: {img_err}", flush=True)

            response = await client.post(
                f"{AI_SERVER_URL}/api/ai/verify-action",
                data=data,
                files=files,
                timeout=20.0,
            )

            if response.status_code == 200:
                result = response.json()
            else:
                result = {
                    "is_resolved": False,
                    "result_text": "AI 서버 오류",
                    "confidence": 0.0,
                    "analysis_summary": f"AI 서버 응답 에러 (Status: {response.status_code})",
                }

    except Exception as e:
        result = {
            "is_resolved": False,
            "result_text": "통신 장애",
            "confidence": 0.0,
            "analysis_summary": f"AI 서버 연결 중 오류 발생: {str(e)}",
        }

    # DB에 AI 판정 결과 업데이트
    if db and action_history_id:
        action = db.query(ActionHistory).filter(ActionHistory.action_history_id == action_history_id).first()
        if action:
            action.ai_verified = result.get("is_resolved")
            action.ai_confidence = result.get("confidence")
            action.ai_summary = result.get("analysis_summary")
            action.ai_verified_at = datetime.now()
            db.commit()

    return result
