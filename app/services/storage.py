import asyncio

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError


class StorageUploadError(Exception):
    """Raised when an object cannot be uploaded to the bucket."""


class S3StorageService:
    """Uploads binary content to an S3-compatible bucket (Cloudflare R2)."""

    def __init__(
        self,
        client: BaseClient,
        bucket: str,
        public_base_url: str | None = None,
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.public_base_url = public_base_url

    async def upload(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
        cache_control: str | None = "public, max-age=31536000, immutable",
    ) -> str:
        extra: dict = {"ContentType": content_type}
        if cache_control is not None:
            extra["CacheControl"] = cache_control
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=data,
                **extra,
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageUploadError("Failed to upload object") from exc
        return self._object_url(key)

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.delete_object, Bucket=self.bucket, Key=key
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageUploadError("Failed to delete object") from exc

    def _object_url(self, key: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{key.lstrip('/')}"
        return key
