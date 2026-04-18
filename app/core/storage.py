from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.core.config import settings


@lru_cache
def get_r2_client() -> BaseClient:
    """Return a boto3 S3 client configured against Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
