import os
import asyncio
import uuid
import time
from typing import Any, Dict, Optional

from app.services.ai.veo.pipelines import (
    render_scene_sequence,
    render_long_video,
    render_extended_summary,
    render_summary,
    render_storyboard,
)
from app.services.ai.parser import parse_document_content
from app.services.ai.veo.prompt_builder import get_token_usage, reset_token_usage
from app.services.ai.education_video_pipeline import (
    analyze_document,
    extract_learning_objectives,
    create_storyboard,
    inspect_video_quality,
    inspect_video_quality_async,
)
from app.db.db import SessionLocal
from app.models.education import Education


# Veo 서비스용 인메모리 작업 상태 저장소
VEO_TASK_STORE: Dict[str, Dict] = {}


def calculate_veo_usage_and_cost(
    task_id: str,
    clip_count: int,
    total_seconds: int,
    llm_input_tokens: int,
    llm_output_tokens: int
) -> Dict[str, Any]:
    """영상 제작에 소모된 LLM 토큰 수, Veo 비디오 생성 초 수 및 추정 단가를 집계하여 출력한다."""
    # Gemini 2.5 Flash 단가 (Input $0.075 / 1M, Output $0.30 / 1M)
    llm_in_cost = (llm_input_tokens / 1_000_000) * 0.075
    llm_out_cost = (llm_output_tokens / 1_000_000) * 0.30
    llm_total_cost = llm_in_cost + llm_out_cost

    # Veo 3.1 Lite 단가 (초당 $0.06 USD 추정)
    veo_cost_per_sec = 0.06
    veo_total_cost = total_seconds * veo_cost_per_sec

    total_usd = llm_total_cost + veo_total_cost
    total_krw = total_usd * 1350  # 환율 1,350원 기준

    summary = {
        "llm_model": "gemini-2.5-flash",
        "llm_input_tokens": llm_input_tokens,
        "llm_output_tokens": llm_output_tokens,
        "llm_total_tokens": llm_input_tokens + llm_output_tokens,
        "llm_cost_usd": round(llm_total_cost, 6),
        "veo_model": "veo-3.1-lite-generate-001",
        "video_clips_count": clip_count,
        "total_video_seconds": total_seconds,
        "veo_cost_usd": round(veo_total_cost, 4),
        "total_cost_usd": round(total_usd, 4),
        "total_cost_krw": round(total_krw, 1)
    }

    print("\n" + "=" * 64)
    print(f"💰 [Veo AI 영상 제작 총 토큰 & API 비용 집계 리포트]")
    print(f"  - 태스크 ID: {task_id}")
    print(f"  - 🤖 LLM 토큰 사용량 (Gemini 2.5 Flash):")
    print(f"    • 입력 토큰 (Input Tokens)  : {llm_input_tokens:,} tokens")
    print(f"    • 출력 토큰 (Output Tokens) : {llm_output_tokens:,} tokens")
    print(f"    • 총 사용 토큰 (Total Tokens): {llm_input_tokens + llm_output_tokens:,} tokens")
    print(f"    • 추정 LLM 비용: ${llm_total_cost:.6f} USD (약 ₩{llm_total_cost * 1350:.2f} 원)")
    print(f"  - 🎬 Veo 비디오 생성 사용량 (Veo 3.1 Lite):")
    print(f"    • 생성 클립 개수: {clip_count}개 클립")
    print(f"    • 총 영상 재생 시간: {total_seconds}초")
    print(f"    • 추정 Veo API 비용: ${veo_total_cost:.4f} USD (약 ₩{veo_total_cost * 1350:,.0f} 원)")
    print("-" * 64)
    print(f"  💵 최종 추정 제작 비용: ${total_usd:.4f} USD (약 ₩{total_krw:,.0f} 원)")
    print("=" * 64 + "\n")

    return summary


def create_veo_task_record() -> str:
    """새로운 Veo 비동기 동영상 제작 태스크 생성 및 ID 반환"""
    task_id = f"veo_task_{uuid.uuid4().hex[:12]}"
    VEO_TASK_STORE[task_id] = {
        "task_id": task_id,
        "status": "PENDING",
        "progress_percent": 0,
        "video_url": None,
        "education_id": None,
        "error_message": None,
        "document_analysis": None,
        "learning_objectives": None,
        "storyboard": None,
        "quality_report": None,
        "usage_summary": None,
        "created_at": int(time.time())
    }
    return task_id


def get_veo_task_status(task_id: str) -> Optional[Dict]:
    """Veo 태스크 처리 상태 및 결과 반환"""
    return VEO_TASK_STORE.get(task_id)


async def process_veo_summary_video_pipeline(
    task_id: str,
    file_path: str,
    company_id: int = 1,
    title: Optional[str] = None,
    category: Optional[str] = "공통",
    type: Optional[str] = "필수",
    request: Optional[str] = None,
    mode: str = "concat",  # "concat" (장면분할 FFmpeg 병합), "long_video" (Extend+병합), "extend" (Extension 체인), "summary" (8초 단일)
    target_duration_seconds: Optional[int] = None
):
    """
    [Track 2 - Veo 전용 서비스 파이프라인]
    비동기 백그라운드 워커:
    1. parser 문서 원문 정밀 추출
    2. 장면별 Veo 8초 전용 비디오 모션 프롬프트 및 대본 생성
    3. Vertex AI Veo 8초 동영상 생성 ➔ FFmpeg 자동 병합
    4. DB(Education) 테이블에 생성 결과 및 비디오 URL 영속화
    """
    record = VEO_TASK_STORE.get(task_id)
    if not record:
        return

    try:
        record["status"] = "PROCESSING"
        record["progress_percent"] = 15
        reset_token_usage()

        safe_title = title if title else f"Veo_AI_Safety_{uuid.uuid4().hex[:6]}"
        output_video_path = f"static/videos/{safe_title}.mp4"

        record["progress_percent"] = 30

        # Structured education-video pipeline: parse -> analyze -> objectives -> storyboard -> render -> inspect.
        if mode == "concat":
            parsed_text, _ = await asyncio.to_thread(parse_document_content, file_path)
            record["progress_percent"] = 25
            analysis = await analyze_document(parsed_text)
            record["document_analysis"] = analysis
            record["progress_percent"] = 35
            objectives = await extract_learning_objectives(analysis)
            record["learning_objectives"] = objectives
            record["progress_percent"] = 45
            storyboard = await create_storyboard(
                parsed_text, analysis, objectives, request, target_duration_seconds
            )
            record["storyboard"] = storyboard
            record["progress_percent"] = 55
            render_result = await render_storyboard(storyboard, output_video_path)
            quality_report = await inspect_video_quality_async(
                storyboard, render_result["video_clips"], output_video_path
            )
            record["quality_report"] = quality_report

            # 집계 및 비용 계산
            tokens = get_token_usage()
            total_sec = len(storyboard) * 8
            usage_summary = calculate_veo_usage_and_cost(
                task_id, len(storyboard), total_sec, tokens["input_tokens"], tokens["output_tokens"]
            )
            record["usage_summary"] = usage_summary

            if not quality_report["passed"]:
                raise RuntimeError(f"Video quality checks failed: {quality_report['failed_checks']}")
            result = {**render_result, "scenes": storyboard}
        elif mode == "long_video":
            print(f"[VeoService] Veo 롱비디오 파이프라인 가동 ({task_id})...")
            result = await render_long_video(
                file_path=file_path,
                target_duration_seconds=target_duration_seconds or 32,
                request=request,
                output_video_path=output_video_path
            )
        elif mode == "extend":
            print(f"[VeoService] Veo 동적 영상 연장(Video Extension) 파이프라인 가동 ({task_id})...")
            result = await render_extended_summary(
                file_path=file_path,
                request=request,
                output_video_path=output_video_path,
                target_duration_seconds=target_duration_seconds
            )
        elif mode == "summary":
            print(f"[VeoService] Veo 단일 8초 마스터 요약 파이프라인 가동 ({task_id})...")
            result = await render_summary(
                file_path=file_path,
                request=request,
                output_video_path=output_video_path
            )
        elif mode not in {"concat", "long_video", "extend", "summary"}:
            # 기본 모드: 장면별 8초 클립 생성 후 FFmpeg 자동 병합 ("concat")
            print(f"[VeoService] Veo 장면 분할 FFmpeg 병합 파이프라인 가동 ({task_id})...")
            result = await render_scene_sequence(
                file_path=file_path,
                request=request,
                output_video_path=output_video_path,
                target_duration_seconds=target_duration_seconds or 32
            )

        record["progress_percent"] = 80

        video_url = result.get("video_url", f"/static/videos/{safe_title}.mp4")
        summary_script = result.get("summary_script", "Google Veo AI 자동 생성 현장 안전 교육 동영상")
        master_prompt = result.get("master_veo_prompt", "")

        # DB(Education) 테이블에 결과 저장 및 영속화
        db = SessionLocal()
        try:
            new_edu = Education(
                company_id=company_id,
                title=title if title else "Veo AI 현장 안전 교육",
                video_url=video_url,
                category=category if category else "공통",
                type=type if type else "필수"
            )
            db.add(new_edu)
            db.commit()
            db.refresh(new_edu)

            hitl_required = bool(quality_report and quality_report.get("hitl_required"))
            final_status = "AWAITING_REVIEW" if hitl_required else "COMPLETED"

            record["status"] = final_status
            record["progress_percent"] = 100
            record["video_url"] = video_url
            record["education_id"] = new_edu.education_id

            if hitl_required:
                v_score = quality_report.get("visual_qa", {}).get("visual_score", 0)
                print(f"[VeoService] ✋ HITL(Human-In-The-Loop): AI 시각 점수({v_score}점) 미달로 관리자 검수 대기(AWAITING_REVIEW) 상태로 등록되었습니다. (DB Education ID: {new_edu.education_id})")
            else:
                print(f"[VeoService] SUCCESS: Veo 동영상 생성 및 자동 승인(COMPLETED) 완료! (DB Education ID: {new_edu.education_id})")
        except Exception as dbe:
            db.rollback()
            print(f"[VeoService] DB 저장 중 예외 발생: {dbe}")
            hitl_required = bool(quality_report and quality_report.get("hitl_required"))
            record["status"] = "AWAITING_REVIEW" if hitl_required else "COMPLETED"
            record["progress_percent"] = 100
            record["video_url"] = video_url
        finally:
            db.close()

    except Exception as e:
        print(f"[VeoService] Veo 파이프라인 실행 중 오류: {e}")
        record["status"] = "FAILED"
        record["error_message"] = str(e)
