from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.action_history import ActionHistory
from app.schemas.action_history import ActionStatus, SourceType
from app.utils.datetime_utils import get_kst_now

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

def verify_action_sim(before_filename: str, after_filename: str):
    return {
        "similarity_score": 0.94,
        "status": "해결됨",
        "description": "조치 전 이미지에 감지되었던 가연성 박스 적치물이 조치 후 이미지에서는 완전히 소거된 것이 검증되었습니다. 조치 결과 승인을 승인 권장합니다."
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
        image_url=image_url,
        action_status=ActionStatus.WAITING.value,
        approval_status=None,
        created_at=get_kst_now(),
    ))
    db.commit()

    return {
        "message": "이벤트 저장 완료",
        "event_id": event_id,
    }
