"""AWS S3 저수준 헬퍼.

게시판·조치이력 이미지와 직접 등록 영상의 실제 업로드·삭제를 담당한다.
저장 경로 규칙과 URL 변환은 media.py 가 갖고 있고, 이 모듈은 boto3 호출만 한다.
"""
import os
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.config import Config


DEFAULT_REGION = "ap-northeast-2"

# addressing_style을 명시하지 않으면 리전 없는 글로벌 엔드포인트
# (bucket.s3.amazonaws.com)로 서명되어, 서울 리전 버킷에서 리다이렉트나
# AuthorizationHeaderMalformed를 유발한다.
_S3_CONFIG = Config(s3={"addressing_style": "virtual"})


def _create_s3_client(region_name: Optional[str] = None):
    """Environment variable-based boto3 S3 client initialization"""
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=region_name or os.getenv("AWS_REGION", DEFAULT_REGION),
        config=_S3_CONFIG
    )
    
def _extract_s3_key(path: Optional[str]) -> Optional[str]:
    """URL 또는 S3 URI에서 실제 S3 Key 경로 전체를 추출합니다."""
    if not path:
        return None

    # 유튜브/외부 링크는 S3 삭제 대상에서 제외
    if path.startswith(
        ("https://www.youtube.com", "https://youtu.be", "http://www.youtube.com")
    ):
        return None

    # s3:// URI 처리
    if path.startswith("s3://"):
        parts = path[len("s3://") :].split("/", 1)
        return parts[1] if len(parts) == 2 else None

    if path.startswith("http://") or path.startswith("https://"):
        parsed = urlparse(path)
        return parsed.path.lstrip("/")  # "media/videos/2026_08_20/..."

    return path


def upload_fileobj_to_s3(
    fileobj,
    bucket: str,
    key: str,
    content_type: str,
    region_name: Optional[str] = None
) -> bool:
    """열려 있는 파일 객체를 S3에 업로드한다. 성공 여부를 반환한다."""
    try:
        s3_client = _create_s3_client(region_name)
        s3_client.upload_fileobj(
            fileobj, bucket, key, ExtraArgs={"ContentType": content_type}
        )
        print(f"[S3Upload] SUCCESS: s3://{bucket}/{key}")
        return True
    except Exception as e:
        print(f"[S3Upload] WARNING: 업로드 예외 발생 ({key}): {e}")
        return False


def delete_object_from_s3(
    key_or_url: Optional[str],
    bucket: Optional[str] = None,
    region_name: Optional[str] = None,
) -> None:
    """S3 오브젝트를 삭제한다. 실패해도 호출부를 막지 않는다."""
    key = _extract_s3_key(key_or_url)
    if not key:
        return

    target_bucket = bucket or os.getenv("AWS_S3_MEDIA_BUCKET")
    if not target_bucket:
        print("[S3Delete] WARNING: AWS_S3_MEDIA_BUCKET 설정이 미비하여 삭제를 생략합니다.")
        return

    try:
        _create_s3_client(region_name).delete_object(Bucket=target_bucket, Key=key)
    except Exception as e:
        print(f"[S3Delete] WARNING: 삭제 예외 발생 ({key}): {e}")