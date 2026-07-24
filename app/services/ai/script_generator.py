import json
import os
import re
import base64
import urllib.request
import asyncio
from typing import List, Dict, Optional


PROMPT_TEMPLATE = """
당신은 현장 안전 교육 영상 전문 기획자입니다.
전달받은 문서(또는 스캔 이미지 PDF)와 사용자 요청 사항을 바탕으로 교육 영상의 장면(Scene)별 대본(script)과 AI 배경 이미지 생성용 영어 프롬프트(image_prompt)를 작성하세요.

[작성 기준]
1. 각 장면의 대본(script)은 1~2문장의 명확하고 간결한 한국어로 작성하세요 (최대 50~65자 이내).
2. image_prompt는 script에 맞는 이미지를 생성하기 위한 프롬프트를 작성하세요.
3. image_prompt는 반드시 해당 scene에 있는 script를 기반으로 하는 관련 이미지 프롬프트로 작성하세요.

반드시 아래 JSON 배열 형식으로만 응답해야 하며, 다른 서문이나 설명을 추가하지 마세요:
[
  {
    "scene": 1,
    "script": "안녕하세요. 오늘 학습할 내용은 고소작업 필수 안전 수칙입니다.",
    "image_prompt": "A professional wide-angle photograph of an industrial workplace safety inspection, highly detailed 8k"
  },
  {
    "scene": 2,
    "script": "첫째, 사다리와 작업발판의 균열 상태를 반드시 사전 점검하세요.",
    "image_prompt": "A warehouse safety manager inspecting equipment in an industrial logistics facility, 8k photography"
  }
]
"""


def _call_gemini_rest_api_sync(api_key: str, payload: dict, models: List[str]) -> Optional[str]:
    """동기식 API 호출 함수 (내부 로직은 기존과 동일)"""
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                text_out = res_data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"[ScriptGenerator] SUCCESS: Gemini Vision API 호출 성공 ({model_name})")
                return text_out
        except Exception as e:
            print(f"[ScriptGenerator] Gemini REST API {model_name} 대체: {e}")
    return None

def _clean_and_parse_json(raw_text: str) -> Optional[List[Dict]]:
    """[Refactor] LLM의 마크다운 포맷팅 및 예외 문자열을 방어하는 완벽한 JSON 파서"""
    text = raw_text.strip()
    # 마크다운 코드 블록 제거
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        # 1차 시도: 정제된 텍스트 통째로 파싱
        return json.loads(text)
    except json.JSONDecodeError:
        # 2차 시도: 정규식으로 대괄호 배열 부분만 추출해서 파싱
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                print(f"[ScriptGenerator] JSON 정규식 추출 후 파싱 실패: {e}")
    return None


async def generate_script_from_text(
    text: str, request: Optional[str] = None, file_path: Optional[str] = None
) -> List[Dict]:
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    models_to_try = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-2.5-flash-lite"]

    if gemini_api_key:
        print("[ScriptGenerator] Gemini Vision LLM 파이프라인 가동...")
        
        try:
            payload = None
            if file_path and os.path.exists(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                mime_type = "application/pdf" if ext == ".pdf" else ("image/png" if ext == ".png" else "image/jpeg")
                
                # [Refactor] 파일 읽기 작업도 블로킹이므로 백그라운드 스레드로 넘김
                def _read_file():
                    with open(file_path, "rb") as f:
                        return base64.b64encode(f.read()).decode("utf-8")
                
                b64_data = await asyncio.to_thread(_read_file)
                
                user_prompt = f"{PROMPT_TEMPLATE}\n첨부된 문서/이미지 파일 내용 전체를 Vision OCR로 정밀 판독하고 문서 전체 주제에 맞는 교육 대본(최대 2줄 분량)을 작성하세요."
                if request: user_prompt += f"\n사용자 요청 사항: {request}"

                payload = {
                    "contents": [{
                        "parts": [
                            {"text": user_prompt},
                            {"inlineData": {"mimeType": mime_type, "data": b64_data}}
                        ]
                    }]
                }
            else:
                user_prompt = f"{PROMPT_TEMPLATE}\n문서 내용:\n{text[:3000]}\n"
                if request: user_prompt += f"사용자 요청 사항: {request}\n"
                payload = {"contents": [{"parts": [{"text": user_prompt}]}]}

            if payload:
                # [Refactor] urllib 동기 네트워크 호출을 이벤트 루프 블로킹 없이 백그라운드 스레드에서 실행
                raw_resp = await asyncio.to_thread(_call_gemini_rest_api_sync, gemini_api_key, payload, models_to_try)
                
                if raw_resp:
                    results = _clean_and_parse_json(raw_resp)
                    if results:
                        return results
                        
        except Exception as e:
            print(f"[ScriptGenerator] API 파이프라인 예외 발생: {e}")
    else:
        print("[ScriptGenerator] NOTICE: GEMINI_API_KEY 미설정 (기본 Fallback 동작)")

    # Fallback / Default AI 스크립트 분할 파이프라인
    clean_lines = [
        line.strip() for line in text.split("\n") 
        if len(line.strip()) > 5 and "산업안전보건 수칙 교육 자료 (" not in line
    ]
    
    if not clean_lines:
        topic_name = request if request else "사업장 현장"
        clean_lines = [
            f"안녕하세요. 오늘 학습할 내용은 {topic_name} 필수 안전 수칙입니다.",
            "작업 투입 전 기계 장비의 사전 안전점검과 규격 보호구 착용 상태를 확인하세요.",
            "통로 주변 불법 적치물을 방치하지 말고 비상구 및 소방시설 접근로를 상시 확보하세요.",
            "위험 요소 발견 시 즉시 작업을 중지하고 현장 안전 관리자에게 보고하시기 바랍니다."
        ]

    results = []
    for idx, line in enumerate(clean_lines[:5], start=1):
        results.append({
            "scene": idx,
            "script": line,
            "image_prompt": f"Industrial safety workplace illustration for {line[:30]}, digital art 8k"
        })

    print(f"[ScriptGenerator] Fallback 파이프라인으로 대본 생성 완료 (생성된 장면 수: {len(results)})")
    return results
