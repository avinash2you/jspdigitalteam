import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.asset import Asset, AssetType, PrimaryLanguage
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


async def _create_test_user(role: UserRole) -> tuple[User, str]:
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"{role.value}_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=clerk_id,
            email=email,
            full_name=f"Test {role.value}",
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token({"sub": clerk_id, "email": email})
    return user, token


@pytest.mark.asyncio
async def test_viewer_receives_403_on_uploads_presign_and_check_duplicate() -> None:
    _, viewer_token = await _create_test_user(UserRole.VIEWER)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. /uploads/check-duplicate returns 403 for viewer
        res_dup = await client.post(
            "/api/v1/uploads/check-duplicate",
            json={"file_sha256": "somehash"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_dup.status_code == 403
        assert "Permission denied" in res_dup.json()["detail"]

        # 2. /uploads/presign returns 403 for viewer
        res_presign = await client.post(
            "/api/v1/uploads/presign",
            json={
                "filename": "document.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 1024,
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_presign.status_code == 403
        assert "Permission denied" in res_presign.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_detection_sha256_go_number_and_url() -> None:
    _, researcher_token = await _create_test_user(UserRole.RESEARCHER)
    transport = ASGITransport(app=app)

    # Insert baseline asset for matching with isolated unique identifiers
    test_hash = uuid.uuid4().hex + uuid.uuid4().hex
    test_go_num = uuid.uuid4().hex[:4].upper()
    test_go = f"GO-MS-{test_go_num}"
    test_url = f"https://goir.ap.gov.in/orders/{uuid.uuid4().hex[:6]}/sand_policy.pdf"

    async with AsyncSessionLocal() as session:
        asset = Asset(
            title="AP Free Sand Policy 2024",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key="raw/2024/sand.pdf",
            file_sha256=test_hash,
            mime_type="application/pdf",
            file_size_bytes=204800,
            go_number=test_go,
            source_url=test_url,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        asset_id_str = str(asset.id)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {researcher_token}"}

        # 1. Match by SHA-256 (uppercase variant check)
        res_sha = await client.post(
            "/api/v1/uploads/check-duplicate",
            json={"file_sha256": test_hash.upper()},
            headers=headers,
        )
        assert res_sha.status_code == 200
        body_sha = res_sha.json()
        assert body_sha["is_duplicate"] is True
        assert len(body_sha["matches"]) == 1
        assert body_sha["matches"][0]["id"] == asset_id_str
        assert body_sha["matches"][0]["match_reason"] == "sha256_checksum"

        # 2. Match by normalized GO number (spaces and lowercase variant check)
        res_go = await client.post(
            "/api/v1/uploads/check-duplicate",
            json={"go_number": f"  go - ms - {test_go_num.lower()} "},
            headers=headers,
        )
        assert res_go.status_code == 200
        body_go = res_go.json()
        assert body_go["is_duplicate"] is True
        assert any(
            m["id"] == asset_id_str and m["match_reason"] == "go_number"
            for m in body_go["matches"]
        )

        # 3. Match by normalized canonical URL (trailing slash and protocol case check)
        res_url = await client.post(
            "/api/v1/uploads/check-duplicate",
            json={"source_url": f"{test_url}/"},
            headers=headers,
        )
        assert res_url.status_code == 200
        body_url = res_url.json()
        assert body_url["is_duplicate"] is True
        assert any(
            m["id"] == asset_id_str and m["match_reason"] == "source_url"
            for m in body_url["matches"]
        )

        # 4. No matches for completely distinct values
        res_none = await client.post(
            "/api/v1/uploads/check-duplicate",
            json={
                "file_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "go_number": "GO-RT-9999",
                "source_url": "https://example.com/other.pdf",
            },
            headers=headers,
        )
        assert res_none.status_code == 200
        body_none = res_none.json()
        assert body_none["is_duplicate"] is False
        assert body_none["matches"] == []


@pytest.mark.asyncio
async def test_presigned_upload_endpoint_and_validation() -> None:
    _, contributor_token = await _create_test_user(UserRole.CONTRIBUTOR)
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {contributor_token}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid request generates presigned upload URL
        res = await client.post(
            "/api/v1/uploads/presign",
            json={
                "filename": "gazette_2024.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 5 * 1024 * 1024,
            },
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert "raw/" in body["object_key"]
        assert "gazette_2024.pdf" in body["object_key"]
        assert body["expires_in"] == 300
        assert "upload" in body["upload_url"]

        # 2. Exceeding 50MB limit fails with 400
        res_large = await client.post(
            "/api/v1/uploads/presign",
            json={
                "filename": "huge_archive.zip",
                "mime_type": "application/zip",
                "file_size_bytes": 51 * 1024 * 1024,
            },
            headers=headers,
        )
        assert res_large.status_code == 400
        assert "exceeds maximum allowed limit" in res_large.json()["detail"]

        # 3. Invalid non-positive size fails with 400
        res_zero = await client.post(
            "/api/v1/uploads/presign",
            json={
                "filename": "empty.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 0,
            },
            headers=headers,
        )
        assert res_zero.status_code == 400

        # 4. Invalid MIME type fails with 400
        res_mime = await client.post(
            "/api/v1/uploads/presign",
            json={
                "filename": "file.bin",
                "mime_type": "invalidmime",
                "file_size_bytes": 1024,
            },
            headers=headers,
        )
        assert res_mime.status_code == 400


@pytest.mark.asyncio
async def test_download_url_generates_presigned_url_and_records_audit_log() -> None:
    user, user_token = await _create_test_user(UserRole.RESEARCHER)
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {user_token}"}

    # Insert asset into database
    asset_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        asset = Asset(
            id=asset_id,
            title="Confidential Intelligence Brief",
            asset_type=AssetType.RESEARCH_MATERIAL,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key="raw/briefs/intel_brief.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=10240,
        )
        session.add(asset)
        await session.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request download URL
        res = await client.get(f"/api/v1/assets/{asset_id}/download-url", headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert body["asset_id"] == str(asset_id)
        assert "download" in body["download_url"]
        assert body["expires_in"] == 300

        # Non-existent asset returns 404
        non_existent_id = uuid.uuid4()
        res_404 = await client.get(
            f"/api/v1/assets/{non_existent_id}/download-url", headers=headers
        )
        assert res_404.status_code == 404

    # Verify immutable audit log record was created
    async with AsyncSessionLocal() as session:
        stmt = select(AuditLog).where(
            AuditLog.action == "asset.download",
            AuditLog.resource_id == str(asset_id),
        )
        result = await session.execute(stmt)
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.actor_user_id == user.id
        assert log.resource_type == "asset"
        assert log.metadata_json["title"] == "Confidential Intelligence Brief"
        assert log.metadata_json["mime_type"] == "application/pdf"
