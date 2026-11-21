from typing import Any

import boto3

from app.adapters.base import ObjectMetadata, StorageProvider
from app.core.config import settings


class R2StorageProvider(StorageProvider):
    """Cloudflare R2 storage adapter serving private objects strictly via short-lived presigned URLs."""

    MAX_EXPIRY_SEC: int = 300

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        s3_client: Any | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url or settings.R2_ENDPOINT_URL
        self.access_key_id = access_key_id or settings.R2_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.R2_SECRET_ACCESS_KEY
        self.bucket_name = bucket_name or settings.R2_BUCKET_NAME

        if s3_client is not None:
            self.client = s3_client
        else:
            self.client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name="auto",
            )

    def _clamp_ttl(self, expires_sec: int) -> int:
        if expires_sec <= 0:
            return self.MAX_EXPIRY_SEC
        return min(expires_sec, self.MAX_EXPIRY_SEC)

    def generate_upload_url(self, key: str, content_type: str, expires_sec: int = 900) -> str:
        """Generate a short-lived presigned PUT URL for private direct upload (max 300s)."""
        ttl = self._clamp_ttl(expires_sec)
        url: str = self.client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=ttl,
            HttpMethod="PUT",
        )
        return url

    def generate_download_url(self, key: str, expires_sec: int = 900) -> str:
        """Generate a short-lived presigned GET URL for private read access (max 300s)."""
        ttl = self._clamp_ttl(expires_sec)
        url: str = self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
            },
            ExpiresIn=ttl,
            HttpMethod="GET",
        )
        return url

    def head_object(self, key: str) -> ObjectMetadata:
        """Retrieve metadata for an existing object in Cloudflare R2."""
        response: dict[str, Any] = self.client.head_object(Bucket=self.bucket_name, Key=key)
        etag = response.get("ETag", "").strip('"')
        last_modified = response.get("LastModified")
        last_modified_str: str | None = None
        if last_modified is not None:
            if hasattr(last_modified, "isoformat"):
                last_modified_str = str(last_modified.isoformat())
            else:
                last_modified_str = str(last_modified)
        return ObjectMetadata(
            key=key,
            size=int(response.get("ContentLength", 0)),
            content_type=str(response.get("ContentType", "application/octet-stream")),
            etag=etag if etag else None,
            last_modified=last_modified_str,
        )

    def delete_object(self, key: str) -> None:
        """Permanently delete an object from Cloudflare R2."""
        self.client.delete_object(Bucket=self.bucket_name, Key=key)
