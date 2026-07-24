import os
import asyncio
import uuid
import time
from typing import Dict, Optional

from app.services.ai.parser import extract_text_from_file
from app.services.ai.script_generator import generate_script_from_text
from app.services.ai.tts_generator import create_audio_from_text
from app.services.ai.image_generator import generate_image_from_prompt
from app.services.ai.video_composer import compose_video
from app.db.db import SessionLocal
from app.models.education import Education


# 인메모리 작업 상태 저장소
TASK_STORE: Dict[str, Dict] = {}


def create_task_record() -> str:
    """새로운 비동기 영상 제작 태스크 생성 및 ID 반환"""
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    TASK_STORE[task_id] = {
        "task_id": task_id,
        "status": "PENDING",
        "progress_percent": 0,
        "video_url": None,
        "education_id": None,
        "error_message": None,
        "created_at": int(time.time())
    }
    return task_id


def get_task_status(task_id: str) -> Optional[Dict]:
    """태스크 처리 상태 및 결과 반환"""
    return TASK_STORE.get(task_id)


async def process_video_generation_pipeline(
    task_id: str,
    file_path: str,
    raw_content: Optional[bytes] = None,
    title: Optional[str] = None,
    category: Optional[str] = "공통",
    type: Optional[str] = "필수",
    request: Optional[str] = None,
):
    """
    비동기 백그라운드 워커: 5단계 영상 자동 제작 파이프라인 제어 후 DB(Education)에 영속화
    """
    record = TASK_STORE.get(task_id)
    if not record:
        return

    try:
        record["status"] = "PROCESSING"
        record["progress_percent"] = 10

        # Step 1: 문서 텍스트 추출
        extracted_text = extract_text_from_file(file_path, raw_content=raw_content)
        record["progress_percent"] = 25

        # Step 2: LLM 장면별 대본 & 프롬프트 파싱 (Gemini Vision 멀티모달 파일 전달 포함)
        scenes = await generate_script_from_text(extracted_text, request=request, file_path=file_path)
        record["progress_percent"] = 40

        temp_dir = f"static/temp/{task_id}"
        os.makedirs(temp_dir, exist_ok=True)

        # Step 3 & Step 4: TTS 음성 생성 및 장면별 배경 이미지 생성
        scene_clips = []
        num_scenes = len(scenes)
        for idx, sc in enumerate(scenes):
            scene_num = sc.get("scene", idx + 1)
            script_txt = sc.get("script", "")
            img_prompt = sc.get("image_prompt", "")

            img_path = os.path.join(temp_dir, f"scene_{scene_num}.jpg")
            aud_path = os.path.join(temp_dir, f"scene_{scene_num}.mp3")

            # 이미지 & 오디오 병렬/순차 생성 (async def generate_image_from_prompt 비동기 호출)
            await generate_image_from_prompt(img_prompt, img_path, scene_num=scene_num, script=script_txt)
            await create_audio_from_text(script_txt, aud_path)
            await asyncio.sleep(0.5)

            scene_clips.append({
                "image_path": img_path,
                "audio_path": aud_path,
                "script": script_txt
            })

            progress = 40 + int((idx + 1) / num_scenes * 35)
            record["progress_percent"] = progress

        # Step 5: 최종 비디오 인코딩 및 합성
        output_video_path = f"static/videos/{title}.mp4"
        compose_video(scene_clips, output_video_path)

        video_url = f"/static/videos/{title}.mp4"
        record["progress_percent"] = 100
        record["status"] = "COMPLETED"
        record["video_url"] = video_url

        # Education DB 테이블에 신규 생성된 교육 영상 정보 적재
        db = SessionLocal()
        try:
            # 제목 우선순위: 전달받은 title > 추출된 텍스트 첫줄 > 기본 타이틀
            if title and title.strip():
                edu_title = title.strip()
            elif extracted_text and extracted_text.strip():
                edu_title = extracted_text.strip().split("\n")[0][:100]
            else:
                edu_title = f"AI 자동 생성 안전 교육 ({task_id})"

            new_edu = Education(
                title=edu_title,
                video_url=video_url,
                category=category or "공통",
                type=type or "필수"
            )
            db.add(new_edu)
            db.commit()
            db.refresh(new_edu)
            record["education_id"] = new_edu.education_id
            print(f"[VideoService] Education DB 테이블에 영상 저장 완료 (education_id: {new_edu.education_id})")
        except Exception as db_err:
            db.rollback()
            print(f"[VideoService] Education DB 레코드 저장 중 오류 발생: {db_err}")
        finally:
            db.close()

    except Exception as e:
        print(f"[VideoService] 파이프라인 수행 중 오류 발생 (task_id: {task_id}): {e}")
        record["status"] = "FAILED"
        record["error_message"] = str(e)
