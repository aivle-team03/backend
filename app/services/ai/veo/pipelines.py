import asyncio
import os
import re
import shutil
from typing import Dict, List, Optional

from app.services.ai.parser import parse_document_content
from app.services.ai.veo.client import extend_veo_video_clip_sync, generate_veo_video_clip
from app.services.ai.veo.constants import MAX_CLIP_SECONDS
from app.services.ai.veo.prompt_builder import (
    generate_veo_master_summary_prompt,
    generate_veo_prompts_from_parsed_text,
)
from app.services.ai.veo.video_editor import _concat_video_clips_ffmpeg

VEO_MAX_CLIP_SECONDS = MAX_CLIP_SECONDS


def _split_script_into_segments(script: str, budgets: List[int]) -> List[str]:
    """
    한국어 대본(script)을 문장 단위로 잘라, budgets 리스트에 지정된 글자 수 예산에 맞춰
    순서대로 여러 세그먼트에 배분한다. (Veo 클립마다 서로 다른 대사를 말하게 하기 위함)
    """
    if not script or not script.strip():
        return []

    sentences = [s.strip() for s in re.split(r'(?<=[.!?다요])\s+', script.strip()) if s.strip()]
    if not sentences:
        return [script.strip()]

    segments: List[str] = []
    current = ""
    budget_idx = 0

    for sentence in sentences:
        budget = budgets[min(budget_idx, len(budgets) - 1)]
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= budget or not current:
            current = candidate
        else:
            segments.append(current)
            budget_idx += 1
            current = sentence

    if current:
        segments.append(current)

    return segments


async def generate_veo_pipeline_from_file(
    file_path: str,
    request: Optional[str] = None,
    output_video_path: str = "static/videos/veo_pipeline_output.mp4",
    target_duration_seconds: Optional[int] = None
) -> Dict:
    """
    [Two-Track Architecture - Track 2: 독립형 Veo 파이프라인]
    1. parser.py: 업로드 문서(PDF, PPTX, TXT 등)에서 텍스트 및 시각 정보 정밀 파싱
    2. generate_veo_prompts_from_parsed_text: parser 파싱 원문 ➔ Veo 전용 모션 비디오 프롬프트(veo_prompt) 직접 생성
    3. Veo 비디오 클립 생성: 장면별 Google Veo 비디오 모델 호출 (클립당 최대 8초)
    4. 비디오 결합: 생성된 Veo 영상 클립들을 ffmpeg로 하나의 최종 MP4 비디오로 이어붙임
    """
    from app.services.ai.parser import parse_document_content

    print(f"[VeoTrack] 1단계: parser 모듈로 문서 파싱 가동 ({file_path})...")
    parsed_text, visual_parts = await asyncio.to_thread(parse_document_content, file_path)

    target_scenes = None
    if target_duration_seconds:
        target_scenes = max(1, -(-target_duration_seconds // VEO_MAX_CLIP_SECONDS))
        print(f"[VeoTrack] 목표 영상 길이 {target_duration_seconds}초 -> 클립 {VEO_MAX_CLIP_SECONDS}초 x {target_scenes}장면으로 구성")

    print("[VeoTrack] 2단계: parser 파싱 원문 ➔ Veo 전용 모션 비디오 프롬프트(veo_prompt) 직접 추출...")
    scenes = await generate_veo_prompts_from_parsed_text(parsed_text, request, file_path, target_scenes=target_scenes)

    print(f"[VeoTrack] 3단계: 총 {len(scenes)}개 장면별 Google Veo AI 비디오 클립 생성 가동...")
    video_clips = []
    for sc in scenes:
        scene_idx = sc.get("scene", 1)
        veo_prompt = sc.get("veo_prompt", sc.get("image_prompt", ""))
        clip_path = f"static/videos/veo_clips/scene_{scene_idx}.mp4"

        created_clip = await generate_veo_video_clip(veo_prompt, clip_path, duration_seconds=VEO_MAX_CLIP_SECONDS)
        video_clips.append(created_clip)

    print(f"[VeoTrack] 4단계: {len(video_clips)}개 Veo 클립을 ffmpeg로 병합 -> {output_video_path}")
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

    merged_ok = await asyncio.to_thread(_concat_video_clips_ffmpeg, video_clips, output_video_path)
    if not merged_ok:
        print("[VeoTrack] WARNING: 클립 병합 실패. 첫 번째 클립만 결과로 사용합니다.")
        if video_clips and os.path.exists(video_clips[0]):
            import shutil
            shutil.copy(video_clips[0], output_video_path)

    return {
        "status": "success",
        "track": "veo_track",
        "video_url": "/" + output_video_path.replace("\\", "/"),
        "total_scenes": len(scenes),
        "clip_seconds_each": VEO_MAX_CLIP_SECONDS,
        "estimated_total_seconds": len(scenes) * VEO_MAX_CLIP_SECONDS,
        "scenes": scenes
    }


async def generate_veo_video_from_storyboard(
    storyboard: List[Dict], output_video_path: str
) -> Dict:
    """Render a pre-approved storyboard and merge its scene clips into one MP4."""
    video_clips = []
    for scene in storyboard:
        scene_idx = scene.get("scene", len(video_clips) + 1)
        clip_path = f"static/videos/veo_clips/scene_{scene_idx}.mp4"
        clip = await generate_veo_video_clip(
            scene.get("veo_prompt", ""), clip_path, duration_seconds=VEO_MAX_CLIP_SECONDS
        )
        video_clips.append(clip)

    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    merged_ok = await asyncio.to_thread(_concat_video_clips_ffmpeg, video_clips, output_video_path)
    if not merged_ok and video_clips and os.path.exists(video_clips[0]):
        import shutil
        shutil.copy(video_clips[0], output_video_path)

    return {
        "video_url": "/" + output_video_path.replace("\\", "/"),
        "video_clips": video_clips,
        "merged": merged_ok,
    }


async def generate_single_veo_summary_video(
    file_path: str,
    request: Optional[str] = None,
    output_video_path: str = "static/videos/veo_summary_video.mp4"
) -> Dict:
    """
    [Track 2 - Master Summary 전용 파이프라인]
    문서 전체 내용을 1개의 마스터 Veo 프롬프트로 요약하여 1회 호출로 8초 하이라이트 동영상 및 대표 대본 생성
    """
    from app.services.ai.parser import parse_document_content

    print(f"[VeoSummaryTrack] 1단계: parser 모듈로 문서 파싱 가동 ({file_path})...")
    parsed_text, visual_parts = await asyncio.to_thread(parse_document_content, file_path)

    print("[VeoSummaryTrack] 2단계: 문서 전체 원문 ➔ 1개의 마스터 Veo 프롬프트 및 요약 대본 생성...")
    summary_data = await generate_veo_master_summary_prompt(parsed_text, request)

    master_prompt = summary_data.get("master_veo_prompt", "")
    summary_script = summary_data.get("summary_script", "")

    print("[VeoSummaryTrack] 3단계: Google Veo 1회 호출로 8초 대표 마스터 비디오 생성 가동...")
    created_video = await generate_veo_video_clip(master_prompt, output_video_path, duration_seconds=8)

    return {
        "status": "success",
        "track": "veo_master_summary_track",
        "video_url": "/" + output_video_path.replace("\\", "/"),
        "summary_script": summary_script,
        "master_veo_prompt": master_prompt,
        "video_file": created_video
    }


async def generate_dynamic_extended_veo_summary(
    file_path: str,
    target_duration_seconds: Optional[int] = None,
    request: Optional[str] = None,
    output_video_path: str = "static/videos/veo_extended_summary.mp4"
) -> Dict:
    """
    [Google Veo Video Extension 기반 동적 영상 연장 파이프라인]
    실제로 발화될 대사(summary_script)를 문장 단위로 쪼개서, 초기 8초 클립과 각 연장(+7초)마다
    서로 다른 대사 조각을 말하도록 배분한다. 초기 8초 생성 후 Veo Extension API로 동적 연장한다.
    """
    from app.services.ai.parser import parse_document_content

    VEO_EXTEND_SECONDS = 7
    KOREAN_CHARS_PER_SECOND = 4.0
    PACING_BUFFER_SECONDS = 2

    INITIAL_BUDGET_CHARS = int((VEO_MAX_CLIP_SECONDS - PACING_BUFFER_SECONDS) * KOREAN_CHARS_PER_SECOND)
    EXTEND_BUDGET_CHARS = int((VEO_EXTEND_SECONDS - 1) * KOREAN_CHARS_PER_SECOND)

    print(f"[VeoDynamicExtend] 1단계: parser 모듈로 문서 파싱 가동 ({file_path})...")
    parsed_text, visual_parts = await asyncio.to_thread(parse_document_content, file_path)

    char_count = len(parsed_text.strip())
    print(f"[VeoDynamicExtend] Parsed document length: {char_count} characters")

    print("[VeoDynamicExtend] 2단계: 문서 전체 원문 ➔ 마스터 Veo 프롬프트 및 대사(summary_script) 생성...")
    summary_data = await generate_veo_master_summary_prompt(parsed_text, request)
    master_prompt = summary_data.get("master_veo_prompt", "")
    summary_script = summary_data.get("summary_script", "")

    segments = _split_script_into_segments(
        summary_script,
        budgets=[INITIAL_BUDGET_CHARS, EXTEND_BUDGET_CHARS]
    )
    if not segments:
        segments = [summary_script.strip()] if summary_script.strip() else [""]

    if target_duration_seconds:
        forced_extensions = max(0, -(-(target_duration_seconds - VEO_MAX_CLIP_SECONDS) // VEO_EXTEND_SECONDS))
        forced_segments_count = forced_extensions + 1
        if len(segments) < forced_segments_count:
            while len(segments) < forced_segments_count:
                segments.append(segments[-1])
        elif len(segments) > forced_segments_count:
            merged_tail = " ".join(segments[forced_segments_count - 1:])
            segments = segments[:forced_segments_count - 1] + [merged_tail]

    total_segments = len(segments)
    target_duration_seconds = VEO_MAX_CLIP_SECONDS + VEO_EXTEND_SECONDS * (total_segments - 1)
    print(f"[VeoDynamicExtend] Segments: {total_segments}; target duration: {target_duration_seconds}s")
    for i, seg in enumerate(segments):
        print(f"[VeoDynamicExtend]   세그먼트 {i + 1}: \"{seg}\"")

    initial_segment = segments[0]
    initial_clip = "static/videos/veo_clips/initial_8s.mp4"
    print("[VeoDynamicExtend] 3단계: Initial 8초 Veo 비디오 생성...")

    if summary_script.strip() and summary_script.strip() in master_prompt:
        initial_prompt = master_prompt.replace(summary_script.strip(), initial_segment)
    else:
        initial_prompt = master_prompt

    current_video = await generate_veo_video_clip(initial_prompt, initial_clip, duration_seconds=VEO_MAX_CLIP_SECONDS)

    accumulated_seconds = VEO_MAX_CLIP_SECONDS
    for ext_idx in range(1, total_segments):
        segment_text = segments[ext_idx]
        ext_prompt = (
            "Continuing the same industrial safety training scene with the same person and setting, "
            f"the safety manager continues speaking in Korean, saying: \"{segment_text}\", "
            "matching the previous camera angle, lighting and visual style, natural continued motion, "
            "clear Korean dialogue with natural lip-sync, no background music, "
            "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"
        )
        accumulated_seconds += VEO_EXTEND_SECONDS
        ext_clip = f"static/videos/veo_clips/extended_{accumulated_seconds}s.mp4"
        print(f"[VeoDynamicExtend] 4단계: Veo Extension API 가동 중 (+{VEO_EXTEND_SECONDS}초 연장 #{ext_idx}/{total_segments - 1})...")
        current_video = await asyncio.to_thread(
            extend_veo_video_clip_sync,
            current_video,
            ext_prompt,
            ext_clip,
            VEO_EXTEND_SECONDS
        )

    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    if os.path.exists(current_video):
        import shutil
        shutil.copy(current_video, output_video_path)

    return {
        "status": "success",
        "track": "veo_dynamic_extension_track",
        "video_url": "/" + output_video_path.replace("\\", "/"),
        "total_duration_seconds": target_duration_seconds,
        "summary_script": summary_script,
        "script_segments": segments,
        "master_veo_prompt": master_prompt,
        "final_video_file": output_video_path
    }


async def render_storyboard(storyboard: List[Dict], output_video_path: str) -> Dict:
    return await generate_veo_video_from_storyboard(storyboard, output_video_path)


async def render_scene_sequence(file_path: str, request: Optional[str], output_video_path: str, target_duration_seconds: Optional[int]) -> Dict:
    return await generate_veo_pipeline_from_file(file_path, request, output_video_path, target_duration_seconds)


async def render_summary(file_path: str, request: Optional[str], output_video_path: str) -> Dict:
    return await generate_single_veo_summary_video(file_path, request, output_video_path)


async def render_extended_summary(file_path: str, request: Optional[str], output_video_path: str, target_duration_seconds: Optional[int]) -> Dict:
    return await generate_dynamic_extended_veo_summary(file_path, target_duration_seconds, request, output_video_path)


async def render_long_video(file_path: str, request: Optional[str], output_video_path: str, target_duration_seconds: int) -> Dict:
    return await generate_veo_long_video(file_path, target_duration_seconds, request, output_video_path)


async def _build_extend_chunk_video(
    master_prompt: str,
    summary_script: str,
    chunk_segments: List[str],
    chunk_idx: int,
    extend_seconds: int = 7
) -> str:
    """세그먼트 리스트 하나를 Initial(8s) + Extend(7s)x N 체인으로 이어서 생성 후 mp4 경로 반환"""
    initial_segment = chunk_segments[0]
    if summary_script.strip() and summary_script.strip() in master_prompt:
        initial_prompt = master_prompt.replace(summary_script.strip(), initial_segment)
    else:
        initial_prompt = master_prompt

    initial_clip = f"static/videos/veo_clips/chunk{chunk_idx}_initial_8s.mp4"
    print(f"[VeoLongVideo]   청크 {chunk_idx + 1} - Initial 8초 생성...")
    current_video = await generate_veo_video_clip(initial_prompt, initial_clip, duration_seconds=VEO_MAX_CLIP_SECONDS)

    accumulated = VEO_MAX_CLIP_SECONDS
    for i, seg in enumerate(chunk_segments[1:], start=1):
        ext_prompt = (
            "Continuing the same industrial safety training scene with the same person and setting, "
            f"the safety manager continues speaking in Korean, saying: \"{seg}\", "
            "matching the previous camera angle, lighting and visual style, natural continued motion, "
            "clear Korean dialogue with natural lip-sync, no background music, "
            "no on-screen text, no captions, no subtitles, no readable signage or labels of any kind"
        )
        accumulated += extend_seconds
        ext_clip = f"static/videos/veo_clips/chunk{chunk_idx}_extended_{accumulated}s.mp4"
        print(f"[VeoLongVideo]   청크 {chunk_idx + 1} - Extend +{extend_seconds}초 (#{i})...")
        current_video = await asyncio.to_thread(
            extend_veo_video_clip_sync, current_video, ext_prompt, ext_clip, extend_seconds
        )

    return current_video


async def generate_veo_long_video(
    file_path: str,
    target_duration_seconds: int,
    request: Optional[str] = None,
    output_video_path: str = "static/videos/veo_long_video.mp4"
) -> Dict:
    """[Extend 체인 + ffmpeg 병합 하이브리드 파이프라인 - 30초 이상 긴 영상용]"""
    from app.services.ai.parser import parse_document_content

    VEO_EXTEND_SECONDS = 7
    KOREAN_CHARS_PER_SECOND = 4.0
    PACING_BUFFER_SECONDS = 2
    MAX_SEGMENTS_PER_CHUNK = 4

    INITIAL_BUDGET_CHARS = int((VEO_MAX_CLIP_SECONDS - PACING_BUFFER_SECONDS) * KOREAN_CHARS_PER_SECOND)
    EXTEND_BUDGET_CHARS = int((VEO_EXTEND_SECONDS - 1) * KOREAN_CHARS_PER_SECOND)

    print(f"[VeoLongVideo] 1단계: parser 모듈로 문서 파싱 가동 ({file_path})...")
    parsed_text, _ = await asyncio.to_thread(parse_document_content, file_path)

    print("[VeoLongVideo] 2단계: 마스터 Veo 프롬프트 및 전체 대사(summary_script) 생성...")
    summary_data = await generate_veo_master_summary_prompt(parsed_text, request)
    master_prompt = summary_data.get("master_veo_prompt", "")
    summary_script = summary_data.get("summary_script", "")

    total_extensions_needed = max(0, -(-(target_duration_seconds - VEO_MAX_CLIP_SECONDS) // VEO_EXTEND_SECONDS))
    total_segments_needed = total_extensions_needed + 1

    budgets_cycle = [
        INITIAL_BUDGET_CHARS if i % MAX_SEGMENTS_PER_CHUNK == 0 else EXTEND_BUDGET_CHARS
        for i in range(max(total_segments_needed, 1))
    ]

    segments = _split_script_into_segments(summary_script, budgets=budgets_cycle)
    if not segments:
        segments = [summary_script.strip()] if summary_script.strip() else [""]

    if len(segments) < total_segments_needed:
        while len(segments) < total_segments_needed:
            segments.append(segments[-1])
    elif len(segments) > total_segments_needed:
        merged_tail = " ".join(segments[total_segments_needed - 1:])
        segments = segments[:total_segments_needed - 1] + [merged_tail]

    chunks = [segments[i:i + MAX_SEGMENTS_PER_CHUNK] for i in range(0, len(segments), MAX_SEGMENTS_PER_CHUNK)]
    print(f"[VeoLongVideo] 전체 {len(segments)}개 세그먼트 -> {len(chunks)}개 청크 구성")
    for i, seg in enumerate(segments):
        print(f"[VeoLongVideo]   세그먼트 {i + 1}: \"{seg}\"")

    print(f"[VeoLongVideo] 3단계: 청크별 Initial+Extend 체인 영상 생성 시작...")
    chunk_video_paths = []
    for chunk_idx, chunk_segments in enumerate(chunks):
        print(f"[VeoLongVideo] === 청크 {chunk_idx + 1}/{len(chunks)} 생성 시작 ===")
        chunk_video = await _build_extend_chunk_video(
            master_prompt=master_prompt,
            summary_script=summary_script,
            chunk_segments=chunk_segments,
            chunk_idx=chunk_idx,
            extend_seconds=VEO_EXTEND_SECONDS
        )
        chunk_video_paths.append(chunk_video)

    print(f"[VeoLongVideo] 4단계: {len(chunk_video_paths)}개 청크를 ffmpeg로 병합 -> {output_video_path}")
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    merged_ok = await asyncio.to_thread(_concat_video_clips_ffmpeg, chunk_video_paths, output_video_path)
    if not merged_ok:
        print("[VeoLongVideo] WARNING: 청크 병합 실패. 첫 번째 청크만 결과로 사용합니다.")
        if chunk_video_paths and os.path.exists(chunk_video_paths[0]):
            import shutil
            shutil.copy(chunk_video_paths[0], output_video_path)

    actual_duration = VEO_MAX_CLIP_SECONDS * len(chunks) + VEO_EXTEND_SECONDS * (len(segments) - len(chunks))

    return {
        "status": "success",
        "track": "veo_long_video_chunked_extend",
        "video_url": "/" + output_video_path.replace("\\", "/"),
        "total_duration_seconds": actual_duration,
        "total_chunks": len(chunks),
        "summary_script": summary_script,
        "script_segments": segments,
        "master_veo_prompt": master_prompt,
        "final_video_file": output_video_path
    }
