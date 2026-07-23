import os
import time
import random
import textwrap
import urllib.parse
import urllib.request
from typing import Optional


def generate_image_from_prompt(
    prompt: str,
    output_path: str,
    width: int = 1280,
    height: int = 720,
    scene_num: int = 1,
    script: Optional[str] = None
) -> str:
    """
    Pollinations.ai / LoremFlickr / Picsum 고화질 이미지 연동 
    (Cloudflare & CDN 캐시 우회 Cache-Busting 기법 적용 및 화면 맞춤 자막 렌더링)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img_downloaded = False

    # 1. Pollinations.ai AI 이미지 생성 시도 (Cloudflare CDN 캐시 무력화 Cache-Buster 쿼리 및 헤더 적용)
    timestamp_cb = int(time.time() * 1000)
    rand_nonce = random.randint(10000, 99999)
    seed = scene_num * 157 + rand_nonce
    cb_token = f"cb={timestamp_cb}_{rand_nonce}"

    encoded_prompt = urllib.parse.quote(prompt[:250])
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true&model=flux&{cb_token}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                if data and len(data) > 3000:
                    with open(output_path, "wb") as f:
                        f.write(data)
                    img_downloaded = True
                    print(f"[ImageGenerator] Pollinations AI 신규 이미지 생성 성공 (Scene {scene_num}, Seed: {seed}): {output_path}")
                    break
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)

    # 2. LoremFlickr / Picsum 고화질 현장 사진 API 대체 (동적 랜덤 시드 기반 캐시 우회)
    if not img_downloaded:
        dynamic_lock = (int(time.time()) + scene_num * 73 + random.randint(1, 9999)) % 10000
        fallback_urls = [
            f"https://loremflickr.com/1280/720/warehouse,industrial,safety/all?lock={dynamic_lock}",
            f"https://picsum.photos/1280/720?random={dynamic_lock}"
        ]
        for f_url in fallback_urls:
            try:
                f_req = urllib.request.Request(f_url, headers=headers)
                with urllib.request.urlopen(f_req, timeout=8) as resp:
                    data = resp.read()
                    if data and len(data) > 3000:
                        with open(output_path, "wb") as f:
                            f.write(data)
                        img_downloaded = True
                        print(f"[ImageGenerator] 고화질 현장 사진 다운로드 성공 (Scene {scene_num}, Lock: {dynamic_lock})")
                        break
            except Exception:
                pass

    # 3. 이미지 하단 화면 폭 맞춤 자막 오버레이 (최대 2줄 제한 + 세로 고정 + Scene 텍스트 완전히 제거)
    try:
        from PIL import Image, ImageDraw, ImageFont

        if img_downloaded and os.path.exists(output_path):
            img = Image.open(output_path).convert("RGB")
        else:
            img = Image.new("RGB", (width, height), color=(15, 23, 42))

        draw = ImageDraw.Draw(img)

        # 폰트 구성 (한글 맑은 고딕 또는 기본 폰트)
        try:
            font_sub = ImageFont.truetype("malgun.ttf", 26)
        except Exception:
            font_sub = ImageFont.load_default()

        display_script = script.strip() if (script and script.strip()) else prompt[:50]
        
        # 1280px 화면 폭에 맞춰 1줄당 자동 줄바꿈
        lines = textwrap.wrap(display_script, width=60)
        if not lines:
            lines = [display_script]

        # 자막은 최대 2줄로 제한하여 세로로 길어지지 않게 고정!
        lines = lines[:2]

        line_height = 36
        # 슬림한 고정 자막 박스 높이 (95px)로 세로 비대화 완전 방지
        box_height = 95

        # 하단 반투명 어두운 자막 배경 박스
        draw.rectangle([0, height - box_height, width, height], fill=(10, 15, 25))

        # 자막 텍스트 세로 중앙 정렬 렌더링
        total_text_height = len(lines) * line_height
        y_start = height - box_height + (box_height - total_text_height) // 2

        for idx, line in enumerate(lines):
            draw.text((40, y_start + idx * line_height), line, fill=(255, 255, 255), font=font_sub)

        img.save(output_path, quality=95)
        print(f"[ImageGenerator] SUCCESS: 화면 맞춤 최대 2줄 자막 오버레이 완성 (Scene {scene_num}, 출력 줄수: {len(lines)})")
        return output_path
    except Exception as pe:
        print(f"[ImageGenerator] PIL 렌더링 예외: {pe}")

    return output_path
