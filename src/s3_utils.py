import os
import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

import botocore
from botocore.exceptions import NoCredentialsError, ClientError

log = logging.getLogger("compliance_copilot")

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "compliance-frontend-sujal-2026")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

def get_s3_client():
    """Return configured boto3 S3 client with unsigned fallback for public buckets."""
    try:
        return boto3.client("s3", region_name=AWS_REGION)
    except Exception:
        return boto3.client("s3", region_name=AWS_REGION, config=botocore.client.Config(signature_version=botocore.UNSIGNED))

def upload_bytes_to_s3(file_bytes: bytes, s3_key: str, content_type: str = "application/pdf") -> str:
    """
    Upload byte stream to AWS S3 and return public S3 URL.
    """
    s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type
        )
        log.info("Successfully uploaded %d bytes to S3: %s", len(file_bytes), s3_url)
    except Exception as e:
        log.warning("S3 upload attempt warning (%s): %s", s3_key, e)

    return s3_url

def read_bytes_from_s3(s3_key: str) -> bytes:
    """
    Download file bytes directly from AWS S3.
    """
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return obj["Body"].read()
    except Exception as e:
        log.error("Failed to read bytes from S3 (%s): %s", s3_key, e)
        raise e

def get_s3_public_url(s3_key: str) -> str:
    """Generate public HTTPS S3 URL."""
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
