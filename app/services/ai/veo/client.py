import asyncio
import base64
import json
import os
import re
import time
import urllib.request
from typing import Optional

from app.services.ai.veo.video_editor import _generate_dummy_fallback_video


def _get_vertex_access_token() -> tuple[Optional[str], Optional[str]]:
    """GCP Service Account 키(video_create.json 등)로 Vertex AI OAuth2 Bearer 토큰 생성"""
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests

        key_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "video_create.json"
        project_id = os.getenv("GCP_PROJECT_ID")

        if os.path.exists(key_file):
            creds = service_account.Credentials.from_service_account_file(
                key_file,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            req = google.auth.transport.requests.Request()
            creds.refresh(req)
            if not project_id and hasattr(creds, "project_id"):
                project_id = creds.project_id
            return creds.token, project_id
    except Exception as e:
        print(f"[VeoGenerator] OAuth2 Token Issue: {e}")

    return None, None


def _extract_video_from_veo_response(res_data) -> tuple[Optional[str], Optional[str]]:
    """
    Vertex AI Veo LRO 완료 응답에서 영상 데이터를 추출하는 범용 파서.
    모델/API 버전에 따라 스키마가 다를 수 있어 모두 지원:
      - {"predictions": [{"bytesBase64Encoded": ...}]}
      - {"videos": [{"bytesBase64Encoded": ...}]}
      - {"generatedVideos": [{"video": {"bytesBase64Encoded": ...}}]}
      - {"video": {"bytesBase64Encoded": ...}}
      - gcsUri/uri 형태의 GCS 저장 결과
    """
    if not isinstance(res_data, dict):
        return None, None

    candidate_lists = []
    for key in ("predictions", "videos", "generatedVideos", "generated_videos", "samples"):
        val = res_data.get(key)
        if isinstance(val, list) and val:
            candidate_lists.append(val)

    if isinstance(res_data.get("video"), dict):
        candidate_lists.append([res_data["video"]])

    for item_list in candidate_lists:
        for item in item_list:
            if not isinstance(item, dict):
                continue
            inner = item.get("video") if isinstance(item.get("video"), dict) else item
            b64 = inner.get("bytesBase64Encoded") or item.get("bytesBase64Encoded")
            if b64:
                return b64, None
            uri = inner.get("gcsUri") or inner.get("uri") or item.get("gcsUri") or item.get("uri")
            if uri:
                return None, uri

    b64 = res_data.get("bytesBase64Encoded")
    if b64:
        return b64, None
    uri = res_data.get("gcsUri") or res_data.get("uri")
    if uri:
        return None, uri

    return None, None


_VEO_SUPPORTED_DURATIONS = (4, 6, 8)
_VEO_EXTENSION_SUPPORTED_DURATIONS = (7,)
VEO_MAX_CLIP_SECONDS = 8


def _clamp_veo_duration(requested_seconds: int, supported: tuple = _VEO_SUPPORTED_DURATIONS) -> int:
    """요청된 영상 길이를 Veo가 지원하는 값 중 가장 가까운 값으로 보정한다."""
    if requested_seconds in supported:
        return requested_seconds
    closest = min(supported, key=lambda d: (abs(d - requested_seconds), -d))
    print(f"[VeoGenerator] INFO: 요청된 영상 길이 {requested_seconds}초는 미지원 값이라 {closest}초로 자동 보정합니다. (지원 값: {supported})")
    return closest


def _sanitize_veo_prompt(raw_prompt: str) -> str:
    """Veo AI 모델에 전달하기 전 화면 텍스트 유발 요소(한글/따옴표 대사) 제거 및 텍스트 금지 지침 보강"""
    if not raw_prompt:
        return "Cinematic medium shot of an industrial workplace, realistic lighting, photorealistic 8k video, 24fps, no text, no captions, no subtitles, no words, no letters, clean video without any text"
    
    # 1. saying: "..." 형태의 대사 따옴표 및 내부 한글 문구 제거 (Veo가 글자로 그리는 원인 차단)
    clean_p = re.sub(r'saying:\s*"[^"]*"', 'speaking and gesturing attentively', raw_prompt, flags=re.IGNORECASE)
    clean_p = re.sub(r'"[^"]*"', '', clean_p)  # 큰따옴표 문구 제거
    clean_p = re.sub(r'[가-힣]+', '', clean_p)  # 한글 텍스트 제거

    # 2. 강력한 텍스트 금지 수식어 보강
    negative_suffix = ", no text, no captions, no subtitles, no words, no letters, no overlay text, no on-screen text, no signage, clean visual frame without any text"
    if "no text" not in clean_p.lower():
        clean_p = clean_p.rstrip(" .,") + negative_suffix

    # 3. 공백 및 콤마 정돈
    clean_p = re.sub(r'\s*,\s*', ', ', clean_p)
    clean_p = re.sub(r'\s+', ' ', clean_p).strip()
    return clean_p


def generate_veo_video_clip_sync(
    prompt: str,
    output_path: str,
    duration_seconds: int = 8,
    aspect_ratio: str = "16:9",
    model_name: str = "veo-3.1-lite-generate-001"
) -> str:
    """Google Vertex AI Veo REST API 1회 단일 호출 함수"""
    access_token, project_id = _get_vertex_access_token()

    if not access_token or not project_id:
        print("[VeoGenerator] GCP 인증 정보가 유효하지 않아 Fallback 동작을 수행합니다.")
        return _generate_dummy_fallback_video(output_path)

    target_model = os.getenv("VEO_MODEL_NAME", model_name)
    location = os.getenv("GCP_LOCATION", "us-central1")
    duration_seconds = _clamp_veo_duration(duration_seconds)
    sanitized_prompt = _sanitize_veo_prompt(prompt)

    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{target_model}:predictLongRunning"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "instances": [{"prompt": sanitized_prompt}],
        "parameters": {
            "aspectRatio": aspect_ratio,
            "durationSeconds": duration_seconds,
            "sampleCount": 1
        }
    }

    try:
        print(f"[VeoGenerator] Vertex AI Veo API 1회 호출 발송... (Model: {target_model})")
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            
            if "name" in res_data:
                operation_name = res_data["name"]
                print(f"[VeoGenerator] LRO 비디오 생성 작업 등록 완료 ({operation_name})")
                res_data = _poll_lro_operation(operation_name, access_token, location)

            try:
                debug_keys = list(res_data.keys()) if isinstance(res_data, dict) else type(res_data)
                print(f"[VeoGenerator] DEBUG: LRO 최종 응답 최상위 키: {debug_keys}")
                print(f"[VeoGenerator] DEBUG: LRO 최종 응답 원문(앞 1500자): {json.dumps(res_data, ensure_ascii=False)[:1500]}")
            except Exception:
                pass

            if isinstance(res_data, dict) and res_data.get("error"):
                err = res_data["error"]
                err_msg = err.get("message") if isinstance(err, dict) else err
                print(f"[VeoGenerator] ERROR: Veo API가 LRO를 오류로 종료함 -> {err_msg}")
            else:
                video_bytes_b64, gcs_uri = _extract_video_from_veo_response(res_data)

                if video_bytes_b64:
                    video_bytes = base64.b64decode(video_bytes_b64)
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(video_bytes)
                    print(f"[VeoGenerator] SUCCESS: Veo 비디오 생성 완료 ({output_path})")
                    return output_path
                elif gcs_uri:
                    print(f"[VeoGenerator] SUCCESS: GCS 비디오 URI 수신 ({gcs_uri})")
                    return gcs_uri
                else:
                    print("[VeoGenerator] WARNING: LRO는 완료됐지만 응답에서 영상 데이터를 찾지 못함.")

    except urllib.error.HTTPError as he:
        try:
            err_body = he.read().decode("utf-8")
            print(f"[VeoGenerator] Veo API ({target_model}) HTTP {he.code} 상세 오류 본문: {err_body}")
        except Exception:
            print(f"[VeoGenerator] Veo API ({target_model}) HTTP 예외: {he}")
    except Exception as e:
        print(f"[VeoGenerator] Veo API ({target_model}) 호출 예외: {e}")

    return _generate_dummy_fallback_video(output_path)


def _poll_lro_operation(operation_name: str, access_token: str, location: str, max_retries: int = 60) -> dict:
    """Vertex AI Veo LRO 작업 상태 전용 폴링 함수"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    model_path = re.sub(r"/operations/[^/]+$", "", operation_name)
    fetch_url = f"https://{location}-aiplatform.googleapis.com/v1/{model_path}:fetchPredictOperation"
    fetch_payload = json.dumps({"operationName": operation_name}).encode("utf-8")
    get_url = f"https://{location}-aiplatform.googleapis.com/v1/{operation_name}"

    for attempt in range(max_retries):
        time.sleep(10)
        
        try:
            req = urllib.request.Request(fetch_url, data=fetch_payload, headers=headers)
            with urllib.request.urlopen(req, timeout=35) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("done"):
                    print(f"[VeoGenerator] SUCCESS: Veo LRO 비디오 생성 완료! (Attempt: {attempt + 1})")
                    if "predictions" in res:
                        return res
                    elif "response" in res and isinstance(res["response"], dict):
                        return res["response"]
                    elif "result" in res and isinstance(res["result"], dict):
                        return res["result"]
                    return res

                meta_state = res.get("metadata", {}).get("state", "RUNNING")
                print(f"[VeoGenerator] Veo 렌더링 진행 중... (상태: {meta_state}, {attempt + 1}/{max_retries})")
                continue
        except Exception:
            pass

        try:
            req = urllib.request.Request(get_url, headers=headers)
            with urllib.request.urlopen(req, timeout=35) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("done"):
                    print(f"[VeoGenerator] SUCCESS: Veo LRO 비디오 생성 완료! (Attempt: {attempt + 1})")
                    if "predictions" in res:
                        return res
                    elif "response" in res and isinstance(res["response"], dict):
                        return res["response"]
                    elif "result" in res and isinstance(res["result"], dict):
                        return res["result"]
                    return res

                meta_state = res.get("metadata", {}).get("state", "RUNNING")
                print(f"[VeoGenerator] Veo 렌더링 진행 중... (상태: {meta_state}, {attempt + 1}/{max_retries})")
        except Exception:
            pass

    return {}


async def generate_veo_video_clip(
    prompt: str,
    output_path: str,
    duration_seconds: int = 8,
    aspect_ratio: str = "16:9"
) -> str:
    """Veo 비디오 생성을 위한 비동기 Wrapper 함수"""
    return await asyncio.to_thread(
        generate_veo_video_clip_sync,
        prompt,
        output_path,
        duration_seconds,
        aspect_ratio
    )


def extend_veo_video_clip_sync(
    input_video_path: str,
    prompt: str,
    output_path: str,
    extension_seconds: int = 8,
    model_name: str = "veo-3.1-lite-generate-001"
) -> str:
    """[Google Veo Video Extension API] 기존 영상에 이어지는 영상 연장 생성"""
    access_token, project_id = _get_vertex_access_token()
    if not access_token or not project_id or not os.path.exists(input_video_path):
        print("[VeoGenerator] Extend 예외: 기본 비디오로 Fallback 진행")
        return _generate_dummy_fallback_video(output_path)

    location = os.getenv("GCP_LOCATION", "us-central1")
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:predictLongRunning"
    extension_seconds = _clamp_veo_duration(extension_seconds, supported=_VEO_EXTENSION_SUPPORTED_DURATIONS)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        with open(input_video_path, "rb") as vf:
            video_b64 = base64.b64encode(vf.read()).decode("utf-8")

        sanitized_prompt = _sanitize_veo_prompt(prompt)
        payload = {
            "instances": [
                {
                    "prompt": sanitized_prompt,
                    "video": {
                        "bytesBase64Encoded": video_b64,
                        "mimeType": "video/mp4"
                    }
                }
            ],
            "parameters": {
                "mode": "video_extension",
                "durationSeconds": extension_seconds
            }
        }

        print(f"[VeoGenerator] Veo 비디오 연장(Extend +{extension_seconds}s) 요청 발송...")
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

        with urllib.request.urlopen(req, timeout=120) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if "name" in res_data:
                res_data = _poll_lro_operation(res_data["name"], access_token, location)

            if isinstance(res_data, dict) and res_data.get("error"):
                err = res_data["error"]
                err_msg = err.get("message") if isinstance(err, dict) else err
                print(f"[VeoGenerator] ERROR: Veo Extension API가 LRO를 오류로 종료함 -> {err_msg}")
            else:
                video_bytes_b64, gcs_uri = _extract_video_from_veo_response(res_data)
                if video_bytes_b64:
                    video_bytes = base64.b64decode(video_bytes_b64)
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(video_bytes)
                    print(f"[VeoGenerator] SUCCESS: Veo 비디오 연장 완료 -> {output_path}")
                    return output_path
                elif gcs_uri:
                    print(f"[VeoGenerator] SUCCESS: GCS 비디오 URI 수신 (연장) ({gcs_uri})")
                    return gcs_uri
    except Exception as e:
        print(f"[VeoGenerator] Veo Extension API 호출 중 예외: {e}")

    return _generate_dummy_fallback_video(output_path)
