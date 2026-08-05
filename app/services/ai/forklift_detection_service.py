from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


SERVICE_FILE = Path(__file__).resolve()

APP_DIR = SERVICE_FILE.parents[2]
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

AI_DIR = PROJECT_DIR / "AI"
AI_VIDEO_DIR = AI_DIR / "videos"
AI_OUTPUT_DIR = AI_DIR / "outputs"
AI_SCRIPT_PATH = AI_DIR / "test1.py"

print("PROJECT_DIR:", PROJECT_DIR)
print("AI_DIR:", AI_DIR)
print("AI_SCRIPT_PATH:", AI_SCRIPT_PATH)
print("AI_SCRIPT_EXISTS:", AI_SCRIPT_PATH.exists())

AI_VIDEO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AI_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


if not AI_SCRIPT_PATH.exists():
    raise FileNotFoundError(
        f"AI 분석 파일을 찾을 수 없습니다: "
        f"{AI_SCRIPT_PATH}"
    )


# AI/test.py를 Python 모듈처럼 불러오기
spec = spec_from_file_location(
    "forklift_ai_module",
    AI_SCRIPT_PATH,
)

if spec is None or spec.loader is None:
    raise ImportError(
        f"AI 모듈을 불러올 수 없습니다: "
        f"{AI_SCRIPT_PATH}"
    )

forklift_ai_module = module_from_spec(spec)

spec.loader.exec_module(
    forklift_ai_module
)


# 동시에 여러 요청이 들어왔을 때
# 같은 모델이 중복 실행되는 문제 방지
analysis_lock = Lock()


def resolve_video_path(
    video_url: str,
) -> Path:
    """
    프론트가 보내는 주소:
    http://127.0.0.1:8000/ai-videos/test2.mp4

    실제 파일 경로:
    bigproject/AI/videos/test2.mp4
    """

    parsed_url = urlparse(video_url)

    url_path = parsed_url.path

    if not url_path:
        raise ValueError(
            "영상 URL 경로가 비어 있습니다."
        )

    prefix = "/ai-videos/"

    if not url_path.startswith(prefix):
        raise ValueError(
            "지원하지 않는 영상 주소입니다. "
            "/ai-videos/ 경로만 사용할 수 있습니다."
        )

    filename = Path(
        url_path.removeprefix(prefix)
    ).name

    if not filename:
        raise ValueError(
            "영상 파일명이 없습니다."
        )

    video_path = AI_VIDEO_DIR / filename

    if not video_path.exists():
        raise FileNotFoundError(
            f"영상 파일을 찾을 수 없습니다: "
            f"{video_path}"
        )

    return video_path


def analyze_forklift_video(
    video_url: str,
):
    video_path = resolve_video_path(
        video_url
    )

    with analysis_lock:
        result = (
            forklift_ai_module.analyze_video(
                video_path
            )
        )

    output_filename = result[
        "output_filename"
    ]

    return {
        **result,
        "output_video_url": (
            f"/ai-results/"
            f"{output_filename}"
        ),
    }