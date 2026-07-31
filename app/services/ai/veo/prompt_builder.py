import asyncio
import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional

from app.services.ai.veo.client import _get_vertex_access_token
from app.services.ai.veo.constants import MAX_CLIP_SECONDS

VEO_MAX_CLIP_SECONDS = MAX_CLIP_SECONDS


def _clean_and_parse_json_for_veo(raw_text: str):
    """Veo 전용 JSON 안전 파서 (script_generator 독립, 이중 따옴표 자동 복구 포함)"""
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
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            candidate = match.group(0)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # saying: "대사" 형태의 내부 미탈출 따옴표 자동 복구
                repaired = re.sub(r'(saying:\s*)"([^"]+)"', r'\1\\"\2\\"', candidate)
                # 개행 문자 복구
                repaired = repaired.replace('\n', '\\n').replace('\r', '\\r')
                try:
                    return json.loads(repaired)
                except Exception as e:
                    print(f"[VeoGenerator] JSON 파싱 실패: {e}")
    return None


# 파이프라인별 LLM 토큰 집계용 글로벌 저장소
_ACCUMULATED_TOKEN_USAGE = {"input_tokens": 0, "output_tokens": 0}


def reset_token_usage():
    """토큰 집계 카운터 초기화"""
    _ACCUMULATED_TOKEN_USAGE["input_tokens"] = 0
    _ACCUMULATED_TOKEN_USAGE["output_tokens"] = 0


def get_token_usage() -> Dict[str, int]:
    """현재까지 누적된 LLM 토큰 사용량 리턴"""
    return dict(_ACCUMULATED_TOKEN_USAGE)


def _call_gemini_for_veo_sync(api_key: str, payload: dict, models: List[str]) -> Optional[str]:
    """[Track 2 전용] Veo 프롬프트 생성을 위한 독립 Gemini REST API 연동 함수"""
    access_token, project_id = _get_vertex_access_token()

    # JSON 강제 출력 옵션 주입
    if "generationConfig" not in payload:
        payload["generationConfig"] = {}
    payload["generationConfig"]["responseMimeType"] = "application/json"

    if access_token and project_id:
        location = os.getenv("GCP_LOCATION", "us-central1")
        vertex_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
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
                    
                    # 토큰 메타데이터 집계
                    meta = res_data.get("usageMetadata", {})
                    in_tok = meta.get("promptTokenCount", 0)
                    out_tok = meta.get("candidatesTokenCount", 0)
                    _ACCUMULATED_TOKEN_USAGE["input_tokens"] += in_tok
                    _ACCUMULATED_TOKEN_USAGE["output_tokens"] += out_tok
                    
                    print(f"[VeoGenerator] SUCCESS: Vertex AI Gemini 프롬프트 생성 완료 ({v_model}, Input: {in_tok}t, Output: {out_tok}t)")
                    return text_out
            except Exception as ve:
                print(f"[VeoGenerator] Vertex AI {v_model} 시도 실패: {ve}")

    if api_key:
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=40) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text_out = res_data["candidates"][0]["content"]["parts"][0]["text"]

                    # 토큰 메타데이터 집계
                    meta = res_data.get("usageMetadata", {})
                    in_tok = meta.get("promptTokenCount", 0)
                    out_tok = meta.get("candidatesTokenCount", 0)
                    _ACCUMULATED_TOKEN_USAGE["input_tokens"] += in_tok
                    _ACCUMULATED_TOKEN_USAGE["output_tokens"] += out_tok

                    print(f"[VeoGenerator] SUCCESS: AI Studio Gemini 프롬프트 생성 완료 ({model_name}, Input: {in_tok}t, Output: {out_tok}t)")
                    return text_out
            except Exception as e:
                print(f"[VeoGenerator] Gemini REST API {model_name} 대체: {e}")
    return None


async def generate_veo_master_summary_prompt(
    parsed_text: str, request: Optional[str] = None
) -> Dict:
    """
    [Track 2 - Master Summary 모드]
    parser에서 추출된 전체 문서 원문을 한눈에 시각화하는 1개의 대표 요약 대본(summary_script)과
    Google Veo 전용 마스터 비디오 모션 프롬프트(master_veo_prompt)를 생성하는 독립 함수
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]

    master_template = """
당신은 현장 안전 교육 영상 총괄 디렉터입니다.
전달받은 문서 전체 내용을 바탕으로 단순 인사말이나 소개문("소개하겠습니다", "알아보겠습니다")을 절대로 작성하지 말고, 문서에 포함된 핵심 안전 수칙 3~4가지를 직접 설명하는 구체적인 한국어 대본(summary_script)과 Google Veo 전용 마스터 비디오 프롬프트(master_veo_prompt)를 생성하세요.

[작성 기준]
1. summary_script: 단순 서론/인사말 금지. 문서 내 핵심 안전 지침 3~4가지를 직접 설명하는 3~4문장의 명확한 한국어 대본.
2. master_veo_prompt: 카메라 무빙(wide tracking shot, slow pan), 시네마틱 8K 조명, 인물 및 현장의 생생한 동작(motion)이 표현된 영어 비디오 프롬프트 1문장.
   - Veo는 프롬프트에 적힌 언어로 음성을 생성하므로, 영상 속 인물이 summary_script와 동일한 한국어 대사를 말하도록 반드시 프롬프트 안에 큰따옴표로 대사를 그대로 포함하고 "speaks in Korean"이라고 명시할 것.
   - Veo는 화면에 글자(표지판, 라벨, 자막 등)를 그리면 한글이 깨져서 나오므로, 화면상에는 어떠한 문자/텍스트/표지판도 등장하지 않도록 프롬프트 끝에 반드시 "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"를 포함할 것.
   - 형식 예: "... a safety manager speaks in Korean, saying: \"<summary_script 원문 그대로>\", clear Korean dialogue with natural lip-sync, no background music, no on-screen text, no captions, no subtitles, no readable signage or labels of any kind, ..."

반드시 아래 JSON 형식으로만 응답하세요:
{
  "summary_script": "물류창고 작업 시 보호구 착용은 필수이며 지정된 통행로를 반드시 준수해야 합니다. 비상시 옥외 대피로 위치를 숙지하고 비상벨을 즉시 누르세요.",
  "master_veo_prompt": "Cinematic wide tracking shot of an industrial safety manager supervising workers in a modern logistics plant, the manager speaks in Korean, saying: \"물류창고 작업 시 보호구 착용은 필수이며 지정된 통행로를 반드시 준수해야 합니다. 비상시 옥외 대피로 위치를 숙지하고 비상벨을 즉시 누르세요.\", clear Korean dialogue with natural lip-sync, dynamic camera movement, photorealistic 8k video, 24fps, no background music, no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"
}
"""

    user_prompt = (
        f"{master_template}\n"
        f"문서 원문 내용:\n{parsed_text[:4000]}\n"
    )
    if request:
        user_prompt += f"사용자 추가 요구사항: {request}\n"

    payload = {"contents": [{"role": "user", "parts": [{"text": user_prompt}]}]}

    try:
        raw_resp = await asyncio.to_thread(_call_gemini_for_veo_sync, gemini_api_key, payload, models_to_try)
        if raw_resp:
            result = _clean_and_parse_json_for_veo(raw_resp)
            if isinstance(result, dict) and "master_veo_prompt" in result:
                print(f"[VeoGenerator] SUCCESS: 마스터 요약 Veo 프롬프트 추출 완료: {result['master_veo_prompt'][:50]}...")
                return result
    except Exception as e:
        print(f"[VeoGenerator] 마스터 요약 프롬프트 생성 중 예외: {e}")

    print("[VeoGenerator] WARNING: Gemini API 호출 실패/응답 파싱 불가로 Fallback 요약 프롬프트를 사용합니다.")
    fallback_script = f"오늘 학습할 내용은 {request or '사업장 현장'} 필수 안전 관리 수칙입니다."
    return {
        "summary_script": fallback_script,
        "master_veo_prompt": (
            "Cinematic wide tracking shot of an industrial safety inspection, "
            f"the manager speaks in Korean, saying: \"{fallback_script}\", "
            "clear Korean dialogue with natural lip-sync, dynamic camera motion, "
            "photorealistic 8k video, 24fps, no background music, "
            "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"
        )
    }


async def generate_veo_prompts_from_parsed_text(
    parsed_text: str,
    request: Optional[str] = None,
    file_path: Optional[str] = None,
    target_scenes: Optional[int] = None
) -> List[Dict]:
    """
    [Track 2 - Scene 분할 모드] parser.py에서 추출된 원문 텍스트(parsed_text)를 직접 입력받아,
    Google Veo 전용 카메라 무빙/인물 모션 프롬프트(veo_prompt) 및 장면 대본(script)을 직접 일괄 생성하는 함수
    """
    from app.services.ai.parser import parse_document_content

    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]

    extracted_text = parsed_text or ""
    visual_parts = []

    if file_path and os.path.exists(file_path):
        p_text, p_visual_parts = await asyncio.to_thread(parse_document_content, file_path)
        if p_text:
            extracted_text = p_text
        visual_parts = p_visual_parts

    if target_scenes is None:
        char_count = len(extracted_text.strip())
        if char_count < 300:
            target_scenes = 3   # 24초 (단문/요약 문서)
        elif char_count < 600:
            target_scenes = 4   # 32초 (일반 1페이지)
        elif char_count < 900:
            target_scenes = 5   # 40초
        elif char_count < 1200:
            target_scenes = 6   # 48초
        elif char_count < 1500:
            target_scenes = 8   # 64초
        else:
            target_scenes = 10  # 80초 (대용량 매뉴얼/표준 작업 지침서)
    else:
        target_scenes = max(1, target_scenes)

    user_prompt = f"""
당신은 베테랑 영상 시나리오 작가이자 안전 교육 총괄 디렉터입니다.
전달받은 파싱 원문 텍스트를 정밀 분석하여, 전체 영상을 **처음부터 끝까지 하나의 완벽하게 연결된 강연 스토리(시나리오)**로 기획하고 총 {target_scenes}개의 장면(Veo 모션 프롬프트 및 대본)으로 구성하세요.

[대사 음성 깨짐/절단 방지 규칙 (핵심)]
- Veo 8초 클립 시간 제한 내에 대사가 또박또박 완독되도록, 각 장면의 script는 **공백 포함 최대 18~24자 이내의 짧고 명확한 한 문장**으로 제한하세요!
- 대사가 25자를 넘어가면 8초 비디오 한계 때문에 음성이 빠르게 뭉개지거나 끝부분이 잘립니다.

[한국어 발음/TTS 오독 방지 지침 (필수)]
- Veo AI 음성합성 모델이 대사(script)를 읽을 때 한글 복합명사를 엉뚱한 음소로 오독(예: '물류창고' -> '발려창고')하지 않도록, 대사(script)를 작성할 때 띄어쓰기를 표준에 맞춰 명확히 구분하고 쉬운 한국어 구어체 어휘를 사용하여 음성이 또박또박 정확히 발화되게 하세요.

[내용 연결성 및 스토리텔링 지침]
1. 단편 수칙 개별 나열 금지: 파싱 문서 항목들을 단순 분할하여 따로 놀게 하지 마세요.
2. 연속된 하나의 전체 강연 대본 작성: 처음부터 끝까지 한 명의 안전 관리자가 흐름을 이어가며 말하는 1개의 통합 강연 원고를 만드세요.
3. 짧은 접속어 문맥 연결: 각 장면 대사(script) 시작 부분에 짧은 연결어('안녕하세요...', '첫째, ...', '이어서, ...', '특히, ...', '끝으로, ...')를 사용하여 자연스럽게 잇되, 전체 대사 길이는 24자 이내를 유지하세요.
4. 시각적 인물/배경 일관성: 모든 veo_prompt는 동일한 인물('Same Asian male safety manager in navy uniform and yellow hardhat')이 동일한 현장에서 동선을 이동하며 연설하는 연출로 작성하세요.
5. 명확한 발화 지침: 모든 veo_prompt 내에 "slow and steady Korean speech pace, perfectly clear speech articulation, natural pronunciation" 지침을 포함하세요.
6. 화면 텍스트 금지: 모든 veo_prompt 끝에 "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"를 반드시 포함하세요.

반드시 아래 JSON 배열 형식으로만 응답하세요:
[
  {{"scene": 1, "script": "안녕하세요, 오늘 현장 안전 수칙을 알아봅니다.", "veo_prompt": "Cinematic wide tracking shot of an Asian male safety manager in navy uniform and yellow hardhat, the manager speaks in Korean, saying: \"안녕하세요, 오늘 현장 안전 수칙을 알아봅니다.\", slow and steady Korean speech pace, perfectly clear speech articulation, clear Korean dialogue, no on-screen text, no captions, no subtitles"}},
  ...
]

파싱 문서 원문:
{extracted_text[:4000]}
"""
    if request:
        user_prompt += f"사용자 추가 요청: {request}\n"

    prompt_parts = [{"text": user_prompt}] + visual_parts
    payload = {"contents": [{"role": "user", "parts": prompt_parts}]}

    try:
        raw_resp = await asyncio.to_thread(_call_gemini_for_veo_sync, gemini_api_key, payload, models_to_try)
        if raw_resp:
            results = _clean_and_parse_json_for_veo(raw_resp)
            if results:
                print(f"[VeoGenerator] SUCCESS: parser 원문에서 직접 Veo 전용 프롬프트 {len(results)}개 생성 완료")
                return results
    except Exception as e:
        print(f"[VeoGenerator] parser 원문 기준 Veo 프롬프트 생성 중 예외: {e}")

    print(f"[VeoGenerator] WARNING: Gemini API 호출 실패/응답 파싱 불가로 {target_scenes}개 Fallback 장면 프롬프트를 사용합니다.")
    fallback_pairs = [
        (
            "안녕하세요, 오늘 현장 안전 수칙을 알아봅니다.",
            "Cinematic wide tracking shot of an Asian male safety manager in navy uniform and yellow hardhat walking in modern facility"
        ),
        (
            "첫째, 작업 전 기계 점검과 안전모를 착용하세요.",
            "Close-up slow zoom in of the same safety manager inspecting equipment controls and putting on safety gloves"
        ),
        (
            "이어서, 지정된 안전 통행로를 꼭 준수해 주세요.",
            "Medium tracking shot of the same safety manager walking along designated yellow floor line"
        ),
        (
            "비상시에는 즉시 비상벨을 누르고 대피하세요.",
            "Medium shot of the same safety manager pointing toward emergency exit light and evacuation line"
        ),
        (
            "안전 수칙을 철저히 준수해 주세요. 감사합니다.",
            "Warm medium shot of the same safety manager nodding confidently to camera"
        ),
    ]
    fallback_scenes = []
    for i in range(target_scenes):
        script, visual = fallback_pairs[i % len(fallback_pairs)]
        fallback_scenes.append({
            "scene": i + 1,
            "script": script,
            "veo_prompt": (
                f"{visual}, the person speaks in Korean, saying: \"{script}\", "
                "clear Korean dialogue with natural lip-sync, cinematic lighting, photorealistic 8k video, 24fps, no background music, "
                "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"
            )
        })
    return fallback_scenes
    fallback_scenes = []
    for i in range(target_scenes):
        script, visual = fallback_pairs[i % len(fallback_pairs)]
        fallback_scenes.append({
            "scene": i + 1,
            "script": script,
            "veo_prompt": (
                f"{visual}, the person speaks in Korean, saying: \"{script}\", "
                "clear Korean dialogue with natural lip-sync, cinematic lighting, photorealistic 8k video, 24fps, no background music, "
                "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"
            )
        })
    return fallback_scenes


async def generate_json_response(instruction: str) -> Optional[Dict[str, Any]]:
    """Generate and safely parse a JSON-only Gemini response."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    payload = {"contents": [{"role": "user", "parts": [{"text": instruction}]}]}
    raw = await asyncio.to_thread(
        _call_gemini_for_veo_sync,
        api_key,
        payload,
        ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"],
    )
    parsed = _clean_and_parse_json_for_veo(raw) if raw else None
    return parsed if isinstance(parsed, dict) else None


async def generate_storyboard_scenes(
    planning_context: str, request: Optional[str], target_scenes: Optional[int]
) -> List[Dict[str, Any]]:
    return await generate_veo_prompts_from_parsed_text(
        planning_context, request, target_scenes=target_scenes
    )
