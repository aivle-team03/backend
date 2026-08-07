"""AWS S3 media upload service helper module.

미리 준비된 S3 전용 업로드 유틸리티 모듈로, 추후 AWS S3 도입 시 즉시 사용할 수 있습니다.
"""
import os
import asyncio
from typing import Optional

import boto3
from botocore.config import Config


DEFAULT_REGION = "ap-northeast-2"
DEFAULT_EXPIRES_IN = 3600

# addressing_style을 명시하지 않으면 presigned URL이 리전 없는 글로벌 엔드포인트
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


def _build_object_name(file_path: str, folder: str, public_id: Optional[str]) -> str:
    """Cloudinary의 folder/public_id 규칙을 S3 오브젝트 키로 변환한다."""
    extension = os.path.splitext(file_path)[1] or ".mp4"
    basename = f"{public_id}{extension}" if public_id else os.path.basename(file_path)
    return f"{folder}/{basename}"


async def upload_video_to_s3(
    file_path: str,
    folder: str = "safety_education_videos",
    public_id: Optional[str] = None,
    bucket_name: Optional[str] = None,
    region_name: Optional[str] = None
) -> Optional[str]:
    """
    로컬 MP4 동영상 파일을 AWS S3 버킷에 업로드하고 S3 오브젝트 키를 반환한다.
    S3 설정 미비 또는 업로드 실패 시 None을 반환한다.

    URL이 아닌 키를 반환하는 이유는 presigned URL이 만료되기 때문이다.
    DB에는 이 키를 저장하고, 조회 시점에 generate_presigned_url()로 URL을 만든다.

    환경 변수 지원:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION (기본값: ap-northeast-2)
    - AWS_S3_BUCKET_NAME
    """
    if not file_path or not os.path.exists(file_path):
        print(f"[S3Upload] 업로드 대상 파일이 존재하지 않습니다: {file_path}")
        return None

    bucket = bucket_name or os.getenv("AWS_S3_BUCKET_NAME")

    if not bucket:
        print("[S3Upload] WARNING: AWS_S3_BUCKET_NAME 설정이 미비하여 업로드를 생략합니다.")
        return None

    object_name = _build_object_name(file_path, folder, public_id)

    try:
        def _sync_upload() -> str:
            s3_client = _create_s3_client(region_name)
            extra_args = {"ContentType": "video/mp4"}
            s3_client.upload_file(file_path, bucket, object_name, ExtraArgs=extra_args)
            return object_name

        uploaded_key = await asyncio.to_thread(_sync_upload)
        print(f"[S3Upload] SUCCESS: 동영상 S3 업로드 완료 -> s3://{bucket}/{uploaded_key}")
        return uploaded_key
    except Exception as e:
        print(f"[S3Upload] WARNING: AWS S3 동영상 업로드 예외 발생: {e}")

    return None


def generate_presigned_url(
    object_name: str,
    expires_in: int = DEFAULT_EXPIRES_IN,
    bucket_name: Optional[str] = None,
    region_name: Optional[str] = None
) -> Optional[str]:
    """
    S3 오브젝트 키에 대해 기한부 HTTPS 다운로드 URL을 생성한다.
    버킷을 퍼블릭으로 열지 않고도 영상을 재생할 수 있다.
    S3 설정 미비 또는 생성 실패 시 None을 반환한다.

    서명은 네트워크 호출 없이 로컬에서 계산되므로 동기 함수로 둔다.
    """
    if not object_name:
        print("[S3Presign] 대상 오브젝트 키가 비어 있습니다.")
        return None

    bucket = bucket_name or os.getenv("AWS_S3_BUCKET_NAME")

    if not bucket:
        print("[S3Presign] WARNING: AWS_S3_BUCKET_NAME 설정이 미비하여 URL 생성을 생략합니다.")
        return None

    try:
        s3_client = _create_s3_client(region_name)
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_name},
            ExpiresIn=expires_in
        )
    except Exception as e:
        print(f"[S3Presign] WARNING: presigned URL 생성 예외 발생: {e}")

    return None
