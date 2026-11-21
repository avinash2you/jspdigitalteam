from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.adapters.base import ObjectMetadata, StorageProvider
from app.adapters.registry import get_storage_provider
from app.adapters.storage_r2 import R2StorageProvider


@pytest.fixture
def mock_s3_client() -> MagicMock:
    client = MagicMock()
    client.generate_presigned_url.side_effect = (
        lambda ClientMethod, Params, ExpiresIn, HttpMethod: (
            f"https://r2.cloudflarestorage.com/{Params['Bucket']}/{Params['Key']}"
            f"?method={ClientMethod}&expires={ExpiresIn}&http={HttpMethod}"
        )
    )
    return client


@pytest.fixture
def r2_provider(mock_s3_client: MagicMock) -> R2StorageProvider:
    return R2StorageProvider(
        endpoint_url="https://test-account.r2.cloudflarestorage.com",
        access_key_id="test_key_id",
        secret_access_key="test_secret_key",
        bucket_name="jsp-test-bucket",
        s3_client=mock_s3_client,
    )


def test_r2_implements_storage_provider_protocol(r2_provider: R2StorageProvider) -> None:
    assert isinstance(r2_provider, StorageProvider)


def test_generate_upload_url_presigned_put_and_ttl_bounds(
    r2_provider: R2StorageProvider, mock_s3_client: MagicMock
) -> None:
    # 1. Test standard call exceeding MAX_EXPIRY_SEC (900s clamped to 300s)
    url = r2_provider.generate_upload_url("assets/doc1.pdf", "application/pdf", expires_sec=900)

    mock_s3_client.generate_presigned_url.assert_called_with(
        ClientMethod="put_object",
        Params={
            "Bucket": "jsp-test-bucket",
            "Key": "assets/doc1.pdf",
            "ContentType": "application/pdf",
        },
        ExpiresIn=300,
        HttpMethod="PUT",
    )
    assert "https://r2.cloudflarestorage.com/jsp-test-bucket/assets/doc1.pdf" in url
    assert "method=put_object" in url
    assert "expires=300" in url
    assert "http=PUT" in url

    # 2. Test TTL within bounds (150s kept as 150s)
    r2_provider.generate_upload_url("assets/doc2.pdf", "image/png", expires_sec=150)
    mock_s3_client.generate_presigned_url.assert_called_with(
        ClientMethod="put_object",
        Params={
            "Bucket": "jsp-test-bucket",
            "Key": "assets/doc2.pdf",
            "ContentType": "image/png",
        },
        ExpiresIn=150,
        HttpMethod="PUT",
    )

    # 3. Test non-positive TTL clamped to default MAX_EXPIRY_SEC (300s)
    r2_provider.generate_upload_url("assets/doc3.pdf", "application/pdf", expires_sec=0)
    mock_s3_client.generate_presigned_url.assert_called_with(
        ClientMethod="put_object",
        Params={
            "Bucket": "jsp-test-bucket",
            "Key": "assets/doc3.pdf",
            "ContentType": "application/pdf",
        },
        ExpiresIn=300,
        HttpMethod="PUT",
    )


def test_generate_download_url_presigned_get_and_ttl_bounds(
    r2_provider: R2StorageProvider, mock_s3_client: MagicMock
) -> None:
    # 1. Test standard call exceeding MAX_EXPIRY_SEC (600s clamped to 300s)
    url = r2_provider.generate_download_url("assets/doc1.pdf", expires_sec=600)

    mock_s3_client.generate_presigned_url.assert_called_with(
        ClientMethod="get_object",
        Params={
            "Bucket": "jsp-test-bucket",
            "Key": "assets/doc1.pdf",
        },
        ExpiresIn=300,
        HttpMethod="GET",
    )
    assert "https://r2.cloudflarestorage.com/jsp-test-bucket/assets/doc1.pdf" in url
    assert "method=get_object" in url
    assert "expires=300" in url
    assert "http=GET" in url

    # 2. Test TTL within bounds (60s kept as 60s)
    r2_provider.generate_download_url("assets/doc2.pdf", expires_sec=60)
    mock_s3_client.generate_presigned_url.assert_called_with(
        ClientMethod="get_object",
        Params={
            "Bucket": "jsp-test-bucket",
            "Key": "assets/doc2.pdf",
        },
        ExpiresIn=60,
        HttpMethod="GET",
    )


def test_head_object_metadata_parsing(
    r2_provider: R2StorageProvider, mock_s3_client: MagicMock
) -> None:
    timestamp = datetime(2026, 11, 21, 10, 30, 0, tzinfo=UTC)
    mock_s3_client.head_object.return_value = {
        "ContentLength": 1048576,
        "ContentType": "application/pdf",
        "ETag": '"fba9dede5f2cbd106d1a0e85ac3eecea"',
        "LastModified": timestamp,
    }

    meta = r2_provider.head_object("assets/sample.pdf")

    mock_s3_client.head_object.assert_called_once_with(
        Bucket="jsp-test-bucket", Key="assets/sample.pdf"
    )
    assert isinstance(meta, ObjectMetadata)
    assert meta.key == "assets/sample.pdf"
    assert meta.size == 1048576
    assert meta.content_type == "application/pdf"
    assert meta.etag == "fba9dede5f2cbd106d1a0e85ac3eecea"
    assert meta.last_modified == timestamp.isoformat()


def test_delete_object_calls_boto3(
    r2_provider: R2StorageProvider, mock_s3_client: MagicMock
) -> None:
    r2_provider.delete_object("assets/delete_me.pdf")

    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="jsp-test-bucket", Key="assets/delete_me.pdf"
    )


def test_registry_returns_r2_storage_provider() -> None:
    provider = get_storage_provider("r2")
    assert isinstance(provider, R2StorageProvider)

    alias_provider = get_storage_provider("cloudflare_r2")
    assert isinstance(alias_provider, R2StorageProvider)
