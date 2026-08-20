"""보고서 파일용 S3 헬퍼.

report_agent 가 생성해 올린 문서를 다운로드할 수 있도록 presigned URL 을 만든다.
미디어(이미지·영상)와는 버킷도 리전도 자격증명도 달라 별도 모듈로 둔다.

  미디어   AWS_S3_MEDIA_BUCKET        ap-northeast-2   공개 읽기
  보고서   AWS_REPORT_S3_BUCKET_NAME  us-east-1        비공개 + presigned
"""
import os
from typing import Optional

import boto3
from botocore.config import Config


DEFAULT_REGION = "us-east-1"
DEFAULT_EXPIRES_IN = 3600

# addressing_style을 명시하지 않으면 presigned URL이 리전 없는 글로벌 엔드포인트
# (bucket.s3.amazonaws.com)로 서명되어 리다이렉트나 AuthorizationHeaderMalformed를 유발한다.
_S3_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "virtual", "us_east_1_regional_endpoint": "regional"},
)


def _create_s3_client(region_name: Optional[str] = None):
    """Environment variable-based boto3 S3 client initialization"""
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_REPORT_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_REPORT_SECRET_ACCESS_KEY"),
        region_name=region_name or os.getenv("AWS_REPORT_REGION", DEFAULT_REGION),
        config=_S3_CONFIG
    )


def generate_presigned_url(
    object_name: str,
    expires_in: int = DEFAULT_EXPIRES_IN,
    bucket_name: Optional[str] = None,
    region_name: Optional[str] = None
) -> Optional[str]:
    """
    S3 오브젝트 키에 대해 기한부 HTTPS 다운로드 URL을 생성한다.
    버킷을 퍼블릭으로 열지 않고도 파일을 내려받을 수 있다.
    S3 설정 미비 또는 생성 실패 시 None을 반환한다.

    서명은 네트워크 호출 없이 로컬에서 계산되므로 동기 함수로 둔다.
    """
    if not object_name:
        print("[S3Presign] 대상 오브젝트 키가 비어 있습니다.")
        return None

    bucket = bucket_name or os.getenv("AWS_REPORT_S3_BUCKET_NAME")

    if not bucket:
        print("[S3Presign] WARNING: AWS_REPORT_S3_BUCKET_NAME 설정이 미비하여 URL 생성을 생략합니다.")
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


def delete_report_object_from_s3(
    object_name: str,
    bucket_name: Optional[str] = None,
    region_name: Optional[str] = None,
) -> None:
    """Delete a report object from the private report S3 bucket.

    This follows the same non-blocking style as app.utils.s3_utils.delete_object_from_s3:
    failures are logged, but not raised to the caller.
    """
    if not object_name:
        print("[S3Delete] WARNING: 삭제할 리포트 S3 key가 비어 있습니다.")
        return

    bucket = bucket_name or os.getenv("AWS_REPORT_S3_BUCKET_NAME")

    if not bucket:
        print("[S3Delete] WARNING: AWS_REPORT_S3_BUCKET_NAME 설정이 미비하여 삭제를 생략합니다.")
        return

    try:
        _create_s3_client(region_name).delete_object(Bucket=bucket, Key=object_name)
    except Exception as e:
        print(f"[S3Delete] WARNING: 리포트 S3 삭제 예외 발생 ({object_name}): {e}")
