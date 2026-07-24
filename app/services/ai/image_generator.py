import os
import re
import time
import random
import textwrap
import urllib.parse
import urllib.request
import asyncio
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


def _extract_scene_keywords(prompt: str, script: Optional[str] = None, scene_num: int = 1) -> str:
    """프롬프트 및 대본에서 장면별 고유 시각 키워드를 추출"""
    combined_text = f"{prompt} {script or ''}"
    words = re.findall(r"[a-zA-Z]{4,}", combined_text)
    skip_words = {"professional", "photograph", "industrial", "detailed", "photography", "photo", "with", "this", "that"}
    filtered = [w.lower() for w in words if w.lower() not in skip_words]
    
    if filtered:
        return ",".join(filtered[:3])
    
    if script:
        if "소방" in script or "화재" in script or "소화기" in script: return "fire,extinguisher"
        elif "지게차" in script or "운행" in script: return "forklift,warehouse"
        elif "비상구" in script or "피난" in script: return "emergency,exit"
        elif "보호구" in script or "안전모" in script: return "safety,helmet"
        elif "적치물" in script or "창고" in script: return "warehouse,storage"
            
    default_tags = ["safety,workplace", "warehouse,logistics", "industrial,worker"]
    return default_tags[(scene_num - 1) % len(default_tags)]


def _overlay_subtitle_sync(
    image_path: str, 
    text_content: str, 
    width: int = 1280, 
    height: int = 720, 
    scene_num: int = 1
):
    """[관심사 분리] 이미지 하단에 자막을 렌더링하는 전용 PIL 함수"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        if os.path.exists(image_path):
            img = Image.open(image_path).convert("RGB")
        else:
            img = Image.new("RGB", (width, height), color=(15, 23, 42))

        draw = ImageDraw.Draw(img)

        # 폰트 구성 (시스템 폰트 또는 기본값)
        try:
            font_sub = ImageFont.truetype("malgun.ttf", 24)
        except Exception:
            font_sub = ImageFont.load_default()

        # 한글 기준 1280px 폭에 적절한 줄바꿈 (약 35~40자 내외)
        lines = textwrap.wrap(text_content.strip(), width=38)
        if not lines:
            lines = [text_content]
        lines = lines[:2] # 최대 2줄 유지

        line_height = 34
        box_height = 90

        # 하단 어두운 자막 배경 박스
        draw.rectangle([0, height - box_height, width, height], fill=(10, 15, 25))

        total_text_height = len(lines) * line_height
        y_start = height - box_height + (box_height - total_text_height) // 2

        for idx, line in enumerate(lines):
            draw.text((40, y_start + idx * line_height), line, fill=(255, 255, 255), font=font_sub)

        img.save(image_path, quality=95)
        print(f"[ImageGenerator] SUCCESS: 자막 오버레이 완료 (Scene {scene_num})")
    except Exception as pe:
        print(f"[ImageGenerator] PIL 렌더링 예외 (Scene {scene_num}): {pe}")


def _download_image_sync(
    prompt: str, 
    output_path: str, 
    width: int, 
    height: int, 
    scene_num: int, 
    script: Optional[str]
) -> bool:
    """[관심사 분리] Pollinations / Fallback 네트워크 다운로드 동기 함수"""
    pollinations_key = os.getenv("POLLINATIONS_API_KEY")
    timestamp_cb = int(time.time() * 1000)
    rand_nonce = random.randint(10000, 99999)
    seed = scene_num * 157 + rand_nonce
    cb_token = f"cb={timestamp_cb}_{rand_nonce}"

    encoded_prompt = urllib.parse.quote(prompt[:250])
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true&model=flux&{cb_token}"
    if pollinations_key:
        url += f"&api_key={pollinations_key}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cache-Control": "no-cache"
    }
    if pollinations_key:
        headers["Authorization"] = f"Bearer {pollinations_key}"

    # 1. Pollinations.ai 시도
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                if data and len(data) > 3000:
                    with open(output_path, "wb") as f:
                        f.write(data)
                    print(f"[ImageGenerator] Pollinations AI 이미지 생성 성공 (Scene {scene_num})")
                    return True
        except Exception as e:
            if attempt == 0: time.sleep(0.5)

    # 2. Fallback 사진 API 시도
    scene_tags = _extract_scene_keywords(prompt, script, scene_num)
    rand_token = random.randint(1, 9999)
    fallback_urls = [
        f"https://loremflickr.com/{width}/{height}/{scene_tags}/all?random={scene_num * 100 + rand_token}",
        f"https://picsum.photos/{width}/{height}?random={scene_num * 50 + rand_token}"
    ]
    for f_url in fallback_urls:
        try:
            f_req = urllib.request.Request(f_url, headers=headers)
            with urllib.request.urlopen(f_req, timeout=8) as resp:
                data = resp.read()
                if data and len(data) > 3000:
                    with open(output_path, "wb") as f:
                        f.write(data)
                    print(f"[ImageGenerator] Fallback 현장 사진 다운로드 성공 (Scene {scene_num})")
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
    """[비동기 래퍼] 멀티에이전트 파이프라인에서 블로킹 없이 병렬 수행 가능한 이미지 에이전트 메인 진입점"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1. 이미지 생성/다운로드를 스레드 풀에서 비동기로 수행 (Non-blocking)
    img_downloaded = await asyncio.to_thread(
        _download_image_sync, prompt, output_path, width, height, scene_num, script
    )

    # 2. 자막 렌더링 작업 수행
    display_script = script.strip() if (script and script.strip()) else prompt[:50]
    await asyncio.to_thread(
        _overlay_subtitle_sync, output_path, display_script, width, height, scene_num
    )

    return output_path