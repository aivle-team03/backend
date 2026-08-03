"""AWS S3 media upload service helper module.

미리 준비된 S3 전용 업로드 유틸리티 모듈로, 추후 AWS S3 도입 시 즉시 사용할 수 있습니다.
"""
import os
import asyncio
from typing import Optional


async def upload_video_to_s3(
    file_path: str,
    bucket_name: Optional[str] = None,
    object_name: Optional[str] = None,
    region_name: Optional[str] = None
) -> Optional[str]:
    """
    로컬 MP4 동영상 파일을 AWS S3 버킷에 업로드하고 S3 HTTPS CDN/Public URL을 반환한다.
    
    환경 변수 지원:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION (기본값: ap-northeast-2)
    - AWS_S3_BUCKET_NAME
    """
    if not file_path or not os.path.exists(file_path):
        print(f"[S3Upload] 업로드 대상 파일이 존재하지 않습니다: {file_path}")
        return None

    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = region_name or os.getenv("AWS_REGION", "ap-northeast-2")
    bucket = bucket_name or os.getenv("AWS_S3_BUCKET_NAME")

    if not bucket:
        print("[S3Upload] WARNING: AWS_S3_BUCKET_NAME 설정이 미비하여 업로드를 생략합니다.")
        return None

    if not object_name:
        object_name = f"videos/{os.path.basename(file_path)}"

    def _sync_s3_upload() -> Optional[str]:
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )

            extra_args = {"ContentType": "video/mp4"}
            s3_client.upload_file(file_path, bucket, object_name, ExtraArgs=extra_args)

            s3_url = f"https://{bucket}.s3.{region}.amazonaws.com/{object_name}"
            print(f"[S3Upload] SUCCESS: S3 클라우드 업로드 완료 -> {s3_url}")
            return s3_url
        except ImportError:
            print("[S3Upload] ERROR: 'boto3' 패키지가 설치되어 있지 않습니다. (pip install boto3 필요)")
            return None
        except Exception as e:
            print(f"[S3Upload] WARNING: AWS S3 동영상 업로드 예외 발생: {e}")
            return None

    return await asyncio.to_thread(_sync_s3_upload)
