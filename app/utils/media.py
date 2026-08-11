"""게시판·조치이력 이미지 저장소.

`AWS_S3_MEDIA_BUCKET`이 설정되면 S3에, 없으면 로컬 디스크에 저장한다.
로컬 저장은 컨테이너 재시작 시 파일이 사라지므로 개발 환경 전용이다.

DB에는 항상 경로만 넣는다(`/media/...` 또는 `/static/uploads/...`).
클라이언트에 내려줄 때 `public_url()`로 접두사를 붙인다.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.utils.s3_utils import delete_object_from_s3, upload_fileobj_to_s3


LOCAL_UPLOAD_DIR = Path("static/uploads")
LOCAL_URL_PREFIX = "/static/uploads/"
MEDIA_URL_PREFIX = "/media/"
MEDIA_S3_PREFIX = "media/"

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _media_bucket() -> Optional[str]:
    return os.getenv("AWS_S3_MEDIA_BUCKET")


def storage_mode() -> str:
    """현재 이미지 저장 위치. /health 에서 배포 후 확인용으로 쓴다."""
    return "s3" if _media_bucket() else "local"


def public_url(value: Optional[str]) -> Optional[str]:
    """DB에 저장된 경로를 클라이언트가 그대로 쓸 수 있는 URL로 바꾼다."""
    if not value or not isinstance(value, str):
        return value

    if value.startswith(MEDIA_URL_PREFIX):
        # 운영에서는 프론트와 미디어가 같은 CloudFront 뒤에 있어 상대경로로 충분하다.
        # 로컬에서 S3를 쓸 때만 MEDIA_BASE_URL로 절대주소를 만든다.
        base = os.getenv("MEDIA_BASE_URL", "").rstrip("/")
        return f"{base}{value}" if base else value

    if value.startswith("/static/"):
        backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
        return f"{backend_url}{value}"

    return value


def save_image(image: UploadFile, folder: str) -> str:
    """이미지를 저장하고 DB에 넣을 경로를 반환한다."""
    extension = IMAGE_EXTENSIONS.get(image.content_type or "")
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="jpg, png, webp, gif 형식의 이미지만 업로드할 수 있습니다.",
        )

    # 날짜로 나눠 한 접두사에 객체가 몰리지 않게 하고, 수명주기 정책을 걸기 쉽게 한다.
    # 파일명은 uuid 라 동시 업로드에도 덮어쓰기가 없다.
    relative_path = f"{folder}/{datetime.now():%Y/%m/%d}/{uuid4().hex}{extension}"

    bucket = _media_bucket()
    if not bucket:
        print(
            "[Media] WARNING: AWS_S3_MEDIA_BUCKET 미설정. 로컬 디스크에 저장하며 "
            "재배포 시 이미지가 사라집니다."
        )
        return _save_local(image, relative_path)

    image.file.seek(0)
    uploaded = upload_fileobj_to_s3(
        image.file,
        bucket,
        f"{MEDIA_S3_PREFIX}{relative_path}",
        image.content_type,
    )
    if not uploaded:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="이미지 업로드에 실패했습니다.",
        )
    return f"{MEDIA_URL_PREFIX}{relative_path}"


def delete_image(image_url: Optional[str]) -> None:
    """이전 이미지를 지운다. 저장 위치를 경로 접두사로 판별한다."""
    if not image_url:
        return

    if image_url.startswith(MEDIA_URL_PREFIX):
        bucket = _media_bucket()
        if bucket:
            key = f"{MEDIA_S3_PREFIX}{image_url[len(MEDIA_URL_PREFIX):]}"
            delete_object_from_s3(bucket, key)
        return

    if not image_url.startswith(LOCAL_URL_PREFIX):
        return

    upload_root = LOCAL_UPLOAD_DIR.resolve()
    file_path = Path(image_url.lstrip("/")).resolve()
    try:
        file_path.relative_to(upload_root)
    except ValueError:
        return
    file_path.unlink(missing_ok=True)


def _save_local(image: UploadFile, relative_path: str) -> str:
    file_path = LOCAL_UPLOAD_DIR / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    image.file.seek(0)
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    if file_path.stat().st_size == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="빈 이미지 파일은 업로드할 수 없습니다.",
        )

    return f"{LOCAL_URL_PREFIX}{relative_path}"
