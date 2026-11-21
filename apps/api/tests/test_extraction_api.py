import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.asset import Asset, AssetStatus, AssetType, PrimaryLanguage
from app.models.audit_log import AuditLog
from app.models.document_chunk import DocumentChunk
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
            full_name=f"Test {role.value.capitalize()}",
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token({"sub": clerk_id, "email": email})
    return user, token


async def _create_test_asset(
    user_id: uuid.UUID,
    is_public: bool = True,
    status: AssetStatus = AssetStatus.DRAFT,
) -> Asset:
    async with AsyncSessionLocal() as session:
        asset = Asset(
            title="Test Extraction Asset",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/2024/03/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=4096,
            is_public_record=is_public,
            status=status,
            uploaded_by=user_id,
            dynamic_metadata={
                "go_number": "GO-MS-123",
                "issuing_department": "Revenue",
                "date_of_issue": "2024-03-01",
                "subject": "Initial Subject",
                "state": "Andhra Pradesh",
            },
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        return asset


@pytest.mark.asyncio
async def test_extraction_public_record_runs_ocr_and_ai() -> None:
    user, token = await _create_test_user(UserRole.RESEARCHER)
    asset = await _create_test_asset(user_id=user.id, is_public=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/assets/{asset.id}/extract",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["asset_id"] == str(asset.id)
        assert data["ai_skipped"] is False
        assert data["ai_notice"] is None
        assert data["extracted_text"] != ""
        assert data["status"] == AssetStatus.PENDING_REVIEW.value

        # Check DB updates
        async with AsyncSessionLocal() as session:
            updated = (await session.execute(select(Asset).where(Asset.id == asset.id))).scalar_one()
            assert updated.status == AssetStatus.PENDING_REVIEW
            assert updated.extracted_text == data["extracted_text"]

            # Audit log check
            audit_stmt = select(AuditLog).where(
                AuditLog.resource_id == str(asset.id),
                AuditLog.action == "asset.extract",
            )
            audit = (await session.execute(audit_stmt)).scalar_one_or_none()
            assert audit is not None
            assert audit.metadata_json["ai_skipped"] is False


@pytest.mark.asyncio
async def test_extraction_non_public_record_safely_skips_free_tier_ai() -> None:
    user, token = await _create_test_user(UserRole.RESEARCHER)
    # Non-public confidential record
    asset = await _create_test_asset(user_id=user.id, is_public=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/assets/{asset.id}/extract",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["asset_id"] == str(asset.id)
        assert data["ai_skipped"] is True
        assert "AI extraction skipped for non-public confidential record" in data["ai_notice"]
        # OCR extracted text is still present
        assert data["extracted_text"] != ""
        assert data["status"] == AssetStatus.PENDING_REVIEW.value

        # Check DB
        async with AsyncSessionLocal() as session:
            audit_stmt = select(AuditLog).where(
                AuditLog.resource_id == str(asset.id),
                AuditLog.action == "asset.extract",
            )
            audit = (await session.execute(audit_stmt)).scalar_one_or_none()
            assert audit is not None
            assert audit.metadata_json["ai_skipped"] is True


@pytest.mark.asyncio
async def test_publish_persists_edited_text_and_generates_chunks() -> None:
    user, token = await _create_test_user(UserRole.ADMIN)
    asset = await _create_test_asset(
        user_id=user.id, is_public=True, status=AssetStatus.PENDING_REVIEW
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        edited_text = (
            "Paragraph One: Polavaram irrigation works were reviewed in Godavari delta.\n\n"
            "Paragraph Two: Project timelines and budget allocations confirmed by official ministry."
        )
        payload = {
            "extracted_text": edited_text,
            "english_summary": "Reviewed and finalized English summary of irrigation works.",
            "tenglish_keywords": ["polavaram", "neeti parudala", "godavari"],
            "dynamic_metadata": {
                "go_number": "GO-MS-999",
                "issuing_department": "Water Resources",
                "date_of_issue": "2024-03-01",
                "subject": "Polavaram Works Review",
                "state": "Andhra Pradesh",
            },
        }

        res = await client.post(
            f"/api/v1/assets/{asset.id}/publish",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["status"] == AssetStatus.PUBLISHED.value
        assert data["extracted_text"] == edited_text
        assert data["english_summary"] == payload["english_summary"]
        assert data["tenglish_keywords"] == payload["tenglish_keywords"]
        assert data["dynamic_metadata"]["go_number"] == "GO-MS-999"

        # Check document_chunks in DB
        async with AsyncSessionLocal() as session:
            chunks_stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.asset_id == asset.id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = (await session.execute(chunks_stmt)).scalars().all()
            assert len(chunks) == 2
            assert chunks[0].chunk_index == 0
            assert "Paragraph One" in chunks[0].text
            assert chunks[1].chunk_index == 1
            assert "Paragraph Two" in chunks[1].text

            # Check audit log for asset.edit with publish action
            audit_stmt = select(AuditLog).where(
                AuditLog.resource_id == str(asset.id),
                AuditLog.action == "asset.edit",
            )
            audit = (await session.execute(audit_stmt)).scalar_one_or_none()
            assert audit is not None
            assert audit.metadata_json["action"] == "publish"


@pytest.mark.asyncio
async def test_rbac_restrictions_on_extract_and_publish() -> None:
    _, viewer_token = await _create_test_user(UserRole.VIEWER)
    c1, _ = await _create_test_user(UserRole.CONTRIBUTOR)
    _, c2_token = await _create_test_user(UserRole.CONTRIBUTOR)

    asset = await _create_test_asset(user_id=c1.id, is_public=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Viewer rejected on extract -> 403
        v_extract = await client.post(
            f"/api/v1/assets/{asset.id}/extract",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert v_extract.status_code == 403

        # Viewer rejected on publish -> 403
        v_publish = await client.post(
            f"/api/v1/assets/{asset.id}/publish",
            json={
                "extracted_text": "Text",
                "dynamic_metadata": {
                    "go_number": "GO-1",
                    "issuing_department": "Rev",
                    "date_of_issue": "2024-01-01",
                    "subject": "Sub",
                    "state": "AP",
                },
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert v_publish.status_code == 403

        # Contributor 2 cannot extract Contributor 1's asset -> 403
        c2_extract = await client.post(
            f"/api/v1/assets/{asset.id}/extract",
            headers={"Authorization": f"Bearer {c2_token}"},
        )
        assert c2_extract.status_code == 403

        # Contributor 2 cannot publish Contributor 1's asset -> 403
        c2_publish = await client.post(
            f"/api/v1/assets/{asset.id}/publish",
            json={
                "extracted_text": "Text",
                "dynamic_metadata": {
                    "go_number": "GO-1",
                    "issuing_department": "Rev",
                    "date_of_issue": "2024-01-01",
                    "subject": "Sub",
                    "state": "AP",
                },
            },
            headers={"Authorization": f"Bearer {c2_token}"},
        )
        assert c2_publish.status_code == 403
