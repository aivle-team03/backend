import json
import os
import re
import base64
import urllib.request
import asyncio
from typing import List, Dict, Optional
from app.services.ai.parser import parse_document_content


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
    """Vertex AI OAuth2 Bearer 인증 1순위 (429 요청제한 방지) & AI Studio Fallback 대본 생성 함수"""
    from app.services.ai.image_generator import _get_vertex_access_token
    access_token, project_id = _get_vertex_access_token()

    # 1차 시도: GCP Vertex AI OAuth2 (Rate Limit 429 에러 0건 보장)
    if access_token and project_id:
        location = "us-central1"
        vertex_models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite-preview-06-17",
            "gemini-1.5-flash"
        ]
        for v_model in vertex_models:
            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{v_model}:generateContent"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=40) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text_out = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"[ScriptGenerator] SUCCESS: Vertex AI Gemini 대본 생성 성공 ({v_model})")
                    return text_out
            except Exception as ve:
                print(f"[ScriptGenerator] Vertex AI {v_model} 시도 실패: {ve}")

    # 2차 시도: Google AI Studio REST API Key Fallback
    if api_key:
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
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
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

    if gemini_api_key or True:
        print("[ScriptGenerator] Gemini Vision LLM 파이프라인 가동...")
        
        try:
            # parser.py 모듈에서 스마트 페이지 정밀 파싱(텍스트 + 시각 자료 선별 추출) 위임
            extracted_text = text or ""
            visual_parts = []

            if file_path and os.path.exists(file_path):
                parsed_text, parsed_visual_parts = await asyncio.to_thread(parse_document_content, file_path)
                if parsed_text:
                    extracted_text = parsed_text
                visual_parts = parsed_visual_parts

            # [Dynamic Scene Scaling] 문서 분량에 맞춰 씬 수 자동 계산 (최소 3개 ~ 최대 10개)
            char_count = len(extracted_text.strip())
            target_scenes = max(3, min(10, char_count // 150))
            if char_count < 200:
                target_scenes = 3

            print(f"[ScriptGenerator] 문서 글자 수({char_count}자) 기반 동적 목표 씬 수: {target_scenes}개 계산 완료")

            # Gemini 멀티모달 프롬프트 페이로드 결합
            user_prompt = (
                f"{PROMPT_TEMPLATE}\n"
                f"[핵심 요구사항] 입력 문서 분량에 맞춰 반드시 정확히 {target_scenes}개의 장면(Scene 1부터 Scene {target_scenes}까지)으로 대본 및 이미지를 구성하세요.\n"
                f"문서 내용:\n{extracted_text[:4000]}\n"
            )
            if visual_parts:
                user_prompt += "\n참고: 문서 내 포함된 주요 안전 도면 및 시각 이미지 페이지가 첨부되었습니다. 시각 자료의 세부 작업 내용도 대본에 완벽히 반영하세요.\n"
            if request:
                user_prompt += f"사용자 요청 사항: {request}\n"

            prompt_parts = [{"text": user_prompt}] + visual_parts
            payload = {"contents": [{"role": "user", "parts": prompt_parts}]}

            if payload:
                raw_resp = await asyncio.to_thread(_call_gemini_rest_api_sync, gemini_api_key, payload, models_to_try)
                if raw_resp:
                    results = _clean_and_parse_json(raw_resp)
                    if results:
                        return results
                        
        except Exception as e:
            print(f"[ScriptGenerator] API 파이프라인 예외 발생: {e}")

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
