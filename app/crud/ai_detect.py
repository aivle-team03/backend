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
