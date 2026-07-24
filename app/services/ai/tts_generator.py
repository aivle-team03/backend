import os
import asyncio
from typing import Optional


def _save_gtts_sync(text: str, output_path: str):
    """[관심사 분리] 동기 라이브러리인 gTTS를 스레드 풀에서 안전하게 실행하기 위한 함수"""
    from gtts import gTTS
    tts = gTTS(text=text, lang="ko")
    tts.save(output_path)


async def create_audio_from_text(
    text: str,
    output_path: str,
    voice: str = "ko-KR-HyunsuNeural"
) -> str:
    """
    edge-tts 및 gTTS를 활용하여 대본을 자연스러운 한국어 AI 음성 파일(.mp3)로 비동기 생성
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1차 시도: edge-tts (가장 자연스러운 고품질 신경망 AI 보이스)
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[TTSGenerator] edge-tts 음성 생성 성공: {output_path}")
            return output_path
    except Exception as e:
        print(f"[TTSGenerator] edge-tts 연동 실패 -> gTTS Fallback 전환: {e}")

    # 2차 시도: gTTS (Google Translate TTS - Blocking 방지를 위해 asyncio.to_thread 적용)
    try:
        await asyncio.to_thread(_save_gtts_sync, text, output_path)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[TTSGenerator] gTTS 음성 생성 성공 (Fallback): {output_path}")
            return output_path
    except Exception as ge:
        print(f"[TTSGenerator] gTTS 연동 실패 -> Dummy Audio 생성: {ge}")

    # 3차 시도: Fallback 가상 더미 MP3 파일 작성 (파이프라인이 중단되지 않도록 최소 바이너리 제공)
    try:
        with open(output_path, "wb") as f:
            f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00Dummy Audio Stream for TTS Pipeline")
        print(f"[TTSGenerator] Dummy Audio 작성 완료: {output_path}")
    except Exception as fe:
        print(f"[TTSGenerator] 파일 생성 예외: {fe}")

    return output_path