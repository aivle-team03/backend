"""
Veo Generator Compatibility Layer
Provides backward compatibility for code importing directly from app.services.ai.veo_generator.
"""

from app.services.ai.veo import (
    MAX_CLIP_SECONDS,
    TEXT_TO_VIDEO_DURATIONS,
    VIDEO_EXTENSION_DURATION,
    extend_veo_video_clip_sync,
    generate_dynamic_extended_veo_summary,
    generate_json_response,
    generate_single_veo_summary_video,
    generate_storyboard_scenes,
    generate_veo_long_video,
    generate_veo_master_summary_prompt,
    generate_veo_pipeline_from_file,
    generate_veo_prompts_from_parsed_text,
    generate_veo_video_clip,
    generate_veo_video_clip_sync,
    generate_veo_video_from_storyboard,
    render_extended_summary,
    render_long_video,
    render_scene_sequence,
    render_storyboard,
    render_summary,
)
from app.services.ai.veo.client import (
    _clamp_veo_duration,
    _extract_video_from_veo_response,
    _get_vertex_access_token,
    _poll_lro_operation,
)
from app.services.ai.veo.prompt_builder import (
    _call_gemini_for_veo_sync,
    _clean_and_parse_json_for_veo,
)
from app.services.ai.veo.video_editor import (
    _concat_video_clips_ffmpeg,
    _generate_dummy_fallback_video,
    _get_ffmpeg_executable,
)

VEO_MAX_CLIP_SECONDS = MAX_CLIP_SECONDS
_VEO_SUPPORTED_DURATIONS = TEXT_TO_VIDEO_DURATIONS
_VEO_EXTENSION_SUPPORTED_DURATIONS = (VIDEO_EXTENSION_DURATION,)
