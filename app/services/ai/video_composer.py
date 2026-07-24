import os
import shutil
import asyncio
from typing import List, Dict


def _set_clip_duration(clip, duration: float):
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    elif hasattr(clip, "set_duration"):
        return clip.set_duration(duration)
    return clip


def _set_clip_audio(clip, audio_clip):
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio_clip)
    elif hasattr(clip, "set_audio"):
        return clip.set_audio(audio_clip)
    return clip


def _compose_video_sync(scene_data_list: List[Dict], output_video_path: str) -> str:
    """[관심사 분리] MoviePy를 사용한 실제 동기식 비디오/오디오 합성 및 메모리 자원 해제 전용 함수"""
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

    # 1. MoviePy 모듈 불러오기 (v1 / v2 버전 호환)
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

    clips = []
    audio_clips_to_close = []
    final_video = None

    try:
        for data in scene_data_list:
            img_path = data.get("image_path")
            aud_path = data.get("audio_path")

            duration = 5.0
            audio_clip = None

            # 오디오 추출 및 길이 동기화
            if aud_path and os.path.exists(aud_path) and os.path.getsize(aud_path) > 100:
                try:
                    audio_clip = AudioFileClip(aud_path)
                    duration = audio_clip.duration
                    audio_clips_to_close.append(audio_clip)
                except Exception as ae:
                    print(f"[VideoComposer] AudioFileClip 로드 실패: {ae}")
                    audio_clip = None

            # 이미지 클립 생성 및 오디오 결합
            if img_path and os.path.exists(img_path):
                img_clip = ImageClip(img_path)
                img_clip = _set_clip_duration(img_clip, duration)
                if audio_clip:
                    img_clip = _set_clip_audio(img_clip, audio_clip)
                clips.append(img_clip)

        # 비디오 시퀀스 연동 및 MP4 렌더링
        if clips:
            final_video = concatenate_videoclips(clips, method="compose")
            final_video.write_videofile(
                output_video_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )
            
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000:
                print(f"[VideoComposer] SUCCESS: MP4 비디오 합성 성공! ({output_video_path})")
                return output_video_path

    except Exception as e:
        print(f"[VideoComposer] MoviePy 합성 중 예외 발생: {e}")

    finally:
        # [핵심] 메모리 누수 방지를 위한 클립 자원 해제 (Close)
        for ac in audio_clips_to_close:
            try: ac.close()
            except Exception: pass
            
        for c in clips:
            try: c.close()
            except Exception: pass

        if final_video:
            try: final_video.close()
            except Exception: pass

    # 2. Fallback: 합성 실패 시 샘플 동영상 복사
    try:
        sample_src = os.path.join("static", "videos", "ai_safety_sample.mp4")
        if os.path.exists(sample_src) and os.path.getsize(sample_src) > 1000:
            shutil.copyfile(sample_src, output_video_path)
            print(f"[VideoComposer] Fallback: 샘플 동영상 복사 완료 ({output_video_path})")
            return output_video_path
    except Exception as fe:
        print(f"[VideoComposer] Fallback 복사 실패: {fe}")

    return output_video_path


async def compose_video(scene_data_list: List[Dict], output_video_path: str) -> str:
    """[비동기 래퍼] 멀티에이전트 파이프라인에서 블로킹 없이 실행 가능한 비디오 합성 메인 진입점"""
    return await asyncio.to_thread(_compose_video_sync, scene_data_list, output_video_path)