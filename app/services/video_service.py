import os
import asyncio
import shutil
from typing import Dict, Optional

from app.core.celery_app import celery_app

from app.services.ai.parser import extract_text_from_file
from app.services.ai.script_generator import generate_script_from_text
from app.services.ai.tts_generator import create_audio_from_text
from app.services.ai.image_generator import generate_image_from_prompt
from app.services.ai.video_composer import compose_video
from app.utils.cloudinary_utils import upload_video_to_cloudinary
from app.db.db import SessionLocal
from app.models.education import Education


from app.crud.video_task import create_task, get_task, update_task

def create_task_record() -> str:
    """새로운 비동기 영상 제작 태스크 생성 및 ID 반환"""
    return create_task(task_type="STANDARD")

def get_task_status(task_id: str) -> Optional[Dict]:
    """태스크 처리 상태 및 결과 반환"""
    return get_task(task_id)


async def process_video_generation_pipeline(
    task_id: str,
    file_path: str,
    company_id: int,
    raw_content: Optional[bytes] = None,
    title: Optional[str] = None,
    category: Optional[str] = "공통",
    type: Optional[str] = "필수",
    request: Optional[str] = None,
):
    """
    비동기 백그라운드 워커: 5단계 영상 자동 제작 파이프라인 제어 후 DB(Education)에 영속화
    """
    record = get_task(task_id)
    if not record:
        return

    # Redis 브로커의 visibility timeout으로 재전달된 태스크는 실행하지 않는다. (veo_service와 동일)
    if record.get("status") != "PENDING":
        print(f"[VideoService] 이미 시작된 태스크가 재전달되어 실행을 건너뜁니다 (status={record.get('status')}, task_id={task_id})")
        if record.get("status") == "PROCESSING":
            update_task(task_id, status="FAILED", error_message="작업이 중단된 뒤 재전달되어 실행하지 않았습니다. 다시 요청해 주세요.")
        return

    try:
        update_task(task_id, status="PROCESSING", progress_percent=10)

        # Step 1: 문서 텍스트 추출
        extracted_text = extract_text_from_file(file_path, raw_content=raw_content)
        update_task(task_id, progress_percent=25)

        # Step 2: LLM 장면별 대본 & 프롬프트 파싱 (Gemini Vision 멀티모달 파일 전달 포함)
        scenes = await generate_script_from_text(extracted_text, request=request, file_path=file_path)
        update_task(task_id, progress_percent=40)

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
            update_task(task_id, progress_percent=progress)

        # Step 5: 최종 비디오 인코딩 및 합성 (파일명·public_id는 충돌하지 않는 task_id 사용)
        output_video_path = f"static/videos/{task_id}.mp4"
        await compose_video(scene_clips, output_video_path)

        local_video_url = f"/static/videos/{task_id}.mp4"
        cloudinary_url = await upload_video_to_cloudinary(output_video_path, folder="safety_videos", public_id=task_id)
        video_url = cloudinary_url if cloudinary_url else local_video_url

        # 휴지통 비우기: 작업이 끝난 임시 폴더 삭제
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        # 원본 텍스트/파일 삭제
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        # 클라우드 업로드 성공 시 로컬 비디오 파일 삭제
        if cloudinary_url and os.path.exists(output_video_path):
            os.remove(output_video_path)

        update_task(task_id, progress_percent=100, status="COMPLETED", video_url=video_url)

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
                company_id=company_id,
                title=edu_title,
                video_url=video_url,
                category=category or "공통",
                type=type or "필수"
            )
            db.add(new_edu)
            db.commit()
            db.refresh(new_edu)
            update_task(task_id, education_id=new_edu.education_id)
            print(f"[VideoService] Education DB 테이블에 영상 저장 완료 (education_id: {new_edu.education_id})")
        except Exception as db_err:
            db.rollback()
            print(f"[VideoService] Education DB 레코드 저장 중 오류 발생: {db_err}")
        finally:
            db.close()

    except Exception as e:
        print(f"[VideoService] 파이프라인 수행 중 오류 발생 (task_id: {task_id}): {e}")
        update_task(task_id, status="FAILED", error_message=str(e))

@celery_app.task(name="video_service.process_video_pipeline_task")
def process_video_pipeline_task(
    task_id: str,
    file_path: str,
    company_id: int = 1,
    title: Optional[str] = None,
    category: Optional[str] = "공통",
    type: Optional[str] = "필수",
    request: Optional[str] = None,
):
    """Celery 워커가 실행할 동기 래퍼 함수 (raw_content는 Celery JSON 직렬화를 위해 제외하고 file_path만 전달)"""
    asyncio.run(process_video_generation_pipeline(
        task_id=task_id,
        file_path=file_path,
        company_id=company_id,
        raw_content=None,
        title=title,
        category=category,
        type=type,
        request=request
    ))
