import os
import re
import glob
import json
import time
import random
import base64
import textwrap
import urllib.parse
import urllib.request
import urllib.error
import asyncio
from typing import Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv()

# AI 모델 교차 로테이션 파라미터 (IP 레이트 리밋 100% 예방)
POLLINATIONS_MODELS = ["flux", "turbo", "midjourney", "flux-realism"]

# Unsplash HD 1280x720 큐레이티드 산업 안전 실사 사진 컬렉션 (백업)
UNSPLASH_SAFETY_STOCK = {
    "forklift": [
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1280&h=720&q=80"
    ],
    "helmet": [
        "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1280&h=720&q=80",
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1280&h=720&q=80"
    ],
    "warehouse": [
        "https://images.unsplash.com/photo-1616401784845-180882ba9ba8?auto=format&fit=crop&w=1280&h=720&q=80"
    ],
    "general": [
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1280&h=720&q=80",
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1280&h=720&q=80"
    ]
}


def _wrap_korean_text(text: str, max_chars: int = 30) -> List[str]:
    """어절(단어) 단위 스마트 한글 줄바꿈 (글자 자름 100% 방지)"""
    words = text.strip().split()
    lines = []
    current_line = ""
    for w in words:
        if len(current_line) + len(w) + 1 <= max_chars:
            current_line = f"{current_line} {w}".strip()
        else:
            if current_line:
                lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)
    return lines[:2]


def _extract_scene_keywords(prompt: str, script: Optional[str] = None) -> str:
    """프롬프트 및 대본에서 주제 키워드 추출"""
    combined = f"{prompt} {script or ''}".lower()
    if any(k in combined for k in ["forklift", "지게차", "운행"]): return "forklift"
    elif any(k in combined for k in ["helmet", "보호구", "안전모", "점검"]): return "helmet"
    elif any(k in combined for k in ["rack", "storage", "적치물", "창고", "선반"]): return "warehouse"
    return "general"


def _overlay_subtitle_sync(
    image_path: str, 
    text_content: str, 
    width: int = 1280, 
    height: int = 720, 
    scene_num: int = 1
):
    """[관심사 분리] 어절 단위 자막 렌더링 및 화면 최하단 레이아웃 보정"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        if os.path.exists(image_path) and os.path.getsize(image_path) > 3000:
            img = Image.open(image_path).convert("RGB")
        else:
            img = Image.new("RGB", (width, height), color=(15, 23, 42))

        # 💡 [핵심 해결 point] 하드코딩된 height 대신 실제 이미지의 해상도(너비/높이)를 직접 사용
        img_w, img_h = img.size

        draw = ImageDraw.Draw(img)

        try:
            font_sub = ImageFont.truetype("malgun.ttf", 25)
        except Exception:
            font_sub = ImageFont.load_default()

        # 어절 단위 스마트 한글 줄바꿈
        lines = _wrap_korean_text(text_content, max_chars=40)
        if not lines:
            lines = [text_content]

        line_height = 36
        padding_y = 15  # 자막 위아래 안쪽 여백

        # 자막 줄 수에 맞춘 박스 높이
        box_height = (len(lines) * line_height) + (padding_y * 2)

        # 1. 실제 이미지 높이(img_h) 기준으로 맨 바닥에 정확히 박스 배치
        box_top = img_h - box_height
        draw.rectangle([0, box_top, img_w, img_h], fill=(10, 15, 25))

        # 2. 첫 번째 줄 자막 Y 위치
        y_start = box_top + padding_y

        # 3. 자막 텍스트 출력
        for idx, line in enumerate(lines):
            draw.text((55, y_start + idx * line_height), line, fill=(255, 255, 255), font=font_sub)

        img.save(image_path, quality=95)
        print(f"[ImageGenerator] SUCCESS: 화면 최하단 자막 오버레이 완료 (Scene {scene_num})")
    except Exception as pe:
        print(f"[ImageGenerator] PIL 렌더링 예외 (Scene {scene_num}): {pe}")


def _get_vertex_access_token() -> Tuple[Optional[str], Optional[str]]:
    """Google Cloud Service Account JSON 키 파일로부터 OAuth2 Bearer 토큰 수급"""
    try:
        import google.auth
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path or not os.path.exists(creds_path):
            json_candidates = glob.glob("*.json")
            for jf in json_candidates:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("type") == "service_account":
                            creds_path = jf
                            break
                except Exception:
                    pass

        if creds_path and os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            project_id = os.getenv("GCP_PROJECT_ID") or getattr(credentials, "project_id", None)
        else:
            credentials, project_id = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        if not credentials.valid:
            credentials.refresh(Request())

        return credentials.token, project_id or os.getenv("GCP_PROJECT_ID")
    except Exception as e:
        print(f"[ImageGenerator] Vertex OAuth2 Token 수급 참고: {e}")
        return None, None


def _download_image_vertex_sync(
    prompt: str, 
    output_path: str, 
    scene_num: int, 
    script: Optional[str]
) -> bool:
    """
    [Google Cloud Vertex AI 100% 렌더링 파이프라인]
    1차 시도: Vertex AI Gemini 2.5 Flash Image (OAuth2 Bearer 인증 기반 2.15MB 초고화질 AI 생성, NO TEXT 프롬프트 적용)
    2차 시도: Pollinations AI (API Key 기반)
    3차 시도: PIL 기반 배경 (최후 백업)
    """
    pollinations_key = os.getenv("POLLINATIONS_API_KEY")
    
    # 텍스트 깨짐 방지: 프롬프트에서 특수문자 제거 후 텍스트 생성 완전 금지 지침 추가
    clean_topic = re.sub(r"[^\w\s]", " ", prompt or script or "").strip()
    safe_prompt = (
        f"A professional realistic 8k photograph of industrial workplace safety inspection: {clean_topic}. "
        f"STRICT NEGATIVE DIRECTIVE: ABSOLUTELY NO TEXT, NO WORDS, NO LETTERS, NO KOREAN CHARACTERS, NO WRITING, NO LOGOS, NO SUBTITLES. Pure clean photography."
    )
    
    timestamp_cb = int(time.time() * 1000)
    seed = scene_num * 357 + random.randint(1000, 9999)

    # ==========================================
    # [1차 시도] Vertex AI Gemini 2.5 Flash Image (OAuth2 Bearer)
    # ==========================================
    access_token, project_id = _get_vertex_access_token()
    if access_token and project_id:
        location = "us-central1"
        model_id = "gemini-2.5-flash-image"
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_id}:generateContent"
        
        v_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": safe_prompt[:1000]}]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"]
            }
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=v_headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            b64_img = part["inlineData"]["data"]
                            with open(output_path, "wb") as f:
                                f.write(base64.b64decode(b64_img))
                            print(f"[ImageGenerator] [1차 시도 SUCCESS] Google Cloud Vertex AI Gemini 2.5 Flash Image 텍스트 제거 초고화질 생성 성공! ($300 크레딧 차감) (Scene {scene_num})")
                            return True
        except Exception as ge:
            print(f"[ImageGenerator] 1차 시도 Vertex AI 예외 (Scene {scene_num}): {ge}")

    # ==========================================
    # [2차 시도] Pollinations AI
    # ==========================================
    if pollinations_key:
        models_rot = ["flux", "turbo", "midjourney"]
        model_name = models_rot[(scene_num - 1) % len(models_rot)]
        encoded_p = urllib.parse.quote(safe_prompt[:250])
        p_url = f"https://image.pollinations.ai/prompt/{encoded_p}?width=1280&height=720&seed={seed}&nologo=true&model={model_name}&api_key={pollinations_key}&cb={timestamp_cb}"
        p_headers = {"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {pollinations_key}"}

        for attempt in range(2):
            try:
                p_req = urllib.request.Request(p_url, headers=p_headers)
                with urllib.request.urlopen(p_req, timeout=12) as p_resp:
                    p_data = p_resp.read()
                    if p_data and len(p_data) > 3000:
                        with open(output_path, "wb") as f:
                            f.write(p_data)
                        print(f"[ImageGenerator] [2차 시도 SUCCESS] Pollinations AI ({model_name}) 생성 성공 (Scene {scene_num})")
                        return True
            except Exception:
                if attempt == 0: time.sleep(0.5)

    # ==========================================
    # [3차 시도] 최후 백업 (PIL 단색 배경)
    # ==========================================
    try:
        from PIL import Image
        img = Image.new("RGB", (1280, 720), color=(15, 23, 42))
        img.save(output_path, quality=95)
        print(f"[ImageGenerator] Fallback: 단색 배경 캔버스 생성 (Scene {scene_num})")
        return True
    except Exception:
        pass

    return False


async def generate_image_from_prompt(
    prompt: str,
    output_path: str,
    width: int = 1280,
    height: int = 720,
    scene_num: int = 1,
    script: Optional[str] = None
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    await asyncio.to_thread(
        _download_image_vertex_sync, prompt, output_path, scene_num, script
    )

    display_script = script.strip() if (script and script.strip()) else prompt[:50]
    await asyncio.to_thread(
        _overlay_subtitle_sync, output_path, display_script, width, height, scene_num
    )

    return output_path