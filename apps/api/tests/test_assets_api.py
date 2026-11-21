import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.db.seed_geography import seed_geography
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.asset import AssetStatus, AssetType, RelationType
from app.models.audit_log import AuditLog
from app.models.geography import GeoEntity
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


@pytest.mark.asyncio
async def test_create_and_retrieve_all_6_asset_types() -> None:
    await seed_geography()
    _, uploader_token = await _create_test_user(UserRole.RESEARCHER)

    # Get a seeded geo entity
    async with AsyncSessionLocal() as session:
        geo = (await session.execute(select(GeoEntity).limit(1))).scalar_one()
        geo_id = geo.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {uploader_token}"}

        test_cases: list[tuple[AssetType, dict[str, Any]]] = [
            (
                AssetType.GOVERNMENT_DOCUMENT,
                {
                    "go_number": "GO-MS-999",
                    "issuing_department": "Revenue Dept",
                    "date_of_issue": "2024-01-10",
                    "subject": "Land Record Verification",
                    "state": "Andhra Pradesh",
                },
            ),
            (
                AssetType.NEWSPAPER_CLIPPING,
                {
                    "newspaper_name": "Eenadu",
                    "publication_date": "2024-02-10",
                    "headline": "Historic Rally in Godavari",
                    "edition": "Rajahmundry",
                },
            ),
            (
                AssetType.ONLINE_NEWS_SOCIAL,
                {
                    "platform_publisher": "Twitter/X",
                    "source_url": "https://x.com/JanaSenaParty/status/987654321",
                    "published_date": "2024-03-01",
                    "author_handle": "@PawanKalyan",
                },
            ),
            (
                AssetType.VIDEO_AUDIO,
                {
                    "source_channel_event": "Press Meet Kakinada",
                    "recording_date": "2024-03-15",
                    "speakers": ["Pawan Kalyan"],
                    "duration_sec": 1800,
                },
            ),
            (
                AssetType.IMAGE_INFOGRAPHIC,
                {
                    "event_subject": "Varahi Yatra Phase 3",
                    "capture_date": "2024-03-20",
                    "credit_source": "JSP Media",
                },
            ),
            (
                AssetType.RESEARCH_MATERIAL,
                {
                    "document_title": "Coastal Aquaculture Policy Paper",
                    "authoring_body": "JSP Policy Cell",
                    "publication_date": "2024-01-25",
                },
            ),
        ]

        for asset_type, meta in test_cases:
            sha = uuid.uuid4().hex + uuid.uuid4().hex
            payload = {
                "title": f"Test Asset for {asset_type.value}",
                "asset_type": asset_type.value,
                "r2_object_key": f"raw/2024/03/{uuid.uuid4().hex}.pdf",
                "file_sha256": sha,
                "mime_type": "application/pdf",
                "file_size_bytes": 10240,
                "dynamic_metadata": meta,
                "geo_entity_ids": [str(geo_id)],
            }

            res = await client.post("/api/v1/assets", json=payload, headers=headers)
            assert res.status_code == 201, f"Failed for {asset_type}: {res.text}"
            data = res.json()
            asset_id = data["id"]
            assert data["title"] == payload["title"]
            assert data["asset_type"] == asset_type.value
            assert len(data["geo_entities"]) == 1
            assert data["geo_entities"][0]["id"] == str(geo_id)
            assert data["uploader"] is not None

            # Retrieve asset
            get_res = await client.get(f"/api/v1/assets/{asset_id}", headers=headers)
            assert get_res.status_code == 200
            get_data = get_res.json()
            assert get_data["id"] == asset_id
            assert get_data["dynamic_metadata"] == meta
            assert len(get_data["geo_entities"]) == 1


@pytest.mark.asyncio
async def test_dynamic_metadata_validation_error_returns_422() -> None:
    _, token = await _create_test_user(UserRole.RESEARCHER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "title": "Invalid Gov Doc",
            "asset_type": AssetType.GOVERNMENT_DOCUMENT.value,
            "r2_object_key": "raw/doc.pdf",
            "file_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "dynamic_metadata": {"go_number": "GO-1"},  # Missing issuing_dept, date, etc.
        }
        res = await client.post("/api/v1/assets", json=payload, headers=headers)
        assert res.status_code == 422
        assert "Dynamic metadata validation failed" in res.json()["detail"]


@pytest.mark.asyncio
async def test_document_relationships_crud_and_bidirectional_view() -> None:
    _, admin_token = await _create_test_user(UserRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create Asset A
        res_a = await client.post(
            "/api/v1/assets",
            json={
                "title": "Asset Alpha (New GO)",
                "asset_type": AssetType.GOVERNMENT_DOCUMENT.value,
                "r2_object_key": "raw/a.pdf",
                "file_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
                "mime_type": "application/pdf",
                "file_size_bytes": 2048,
                "dynamic_metadata": {
                    "go_number": "GO-200",
                    "issuing_department": "Irrigation",
                    "date_of_issue": "2024-02-01",
                    "subject": "Polavaram Works Revision",
                    "state": "AP",
                },
            },
            headers=headers,
        )
        assert res_a.status_code == 201
        asset_a_id = res_a.json()["id"]

        # Create Asset B
        res_b = await client.post(
            "/api/v1/assets",
            json={
                "title": "Asset Beta (Original GO)",
                "asset_type": AssetType.GOVERNMENT_DOCUMENT.value,
                "r2_object_key": "raw/b.pdf",
                "file_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
                "mime_type": "application/pdf",
                "file_size_bytes": 4096,
                "dynamic_metadata": {
                    "go_number": "GO-100",
                    "issuing_department": "Irrigation",
                    "date_of_issue": "2023-05-01",
                    "subject": "Initial Polavaram Works",
                    "state": "AP",
                },
            },
            headers=headers,
        )
        assert res_b.status_code == 201
        asset_b_id = res_b.json()["id"]

        # Link: Asset A supersedes Asset B
        rel_res = await client.post(
            f"/api/v1/assets/{asset_a_id}/relationships",
            json={
                "target_asset_id": asset_b_id,
                "relation_type": RelationType.SUPERSEDES.value,
            },
            headers=headers,
        )
        assert rel_res.status_code == 201
        rel_data = rel_res.json()
        rel_id = rel_data["id"]
        assert rel_data["relation_type"] == RelationType.SUPERSEDES.value

        # Test self-link fails
        self_res = await client.post(
            f"/api/v1/assets/{asset_a_id}/relationships",
            json={
                "target_asset_id": asset_a_id,
                "relation_type": RelationType.SUPERSEDES.value,
            },
            headers=headers,
        )
        assert self_res.status_code == 400

        # Test duplicate link fails
        dup_res = await client.post(
            f"/api/v1/assets/{asset_a_id}/relationships",
            json={
                "target_asset_id": asset_b_id,
                "relation_type": RelationType.SUPERSEDES.value,
            },
            headers=headers,
        )
        assert dup_res.status_code == 400

        # View Asset A (outgoing relationship)
        get_a = await client.get(f"/api/v1/assets/{asset_a_id}", headers=headers)
        assert get_a.status_code == 200
        rels_a = get_a.json()["relationships"]
        assert len(rels_a) == 1
        assert rels_a[0]["direction"] == "outgoing"
        assert rels_a[0]["related_asset_id"] == asset_b_id
        assert rels_a[0]["related_asset_title"] == "Asset Beta (Original GO)"
        assert rels_a[0]["relation_type"] == RelationType.SUPERSEDES.value

        # View Asset B (incoming relationship)
        get_b = await client.get(f"/api/v1/assets/{asset_b_id}", headers=headers)
        assert get_b.status_code == 200
        rels_b = get_b.json()["relationships"]
        assert len(rels_b) == 1
        assert rels_b[0]["direction"] == "incoming"
        assert rels_b[0]["related_asset_id"] == asset_a_id
        assert rels_b[0]["related_asset_title"] == "Asset Alpha (New GO)"
        assert rels_b[0]["relation_type"] == RelationType.SUPERSEDES.value

        # Delete relationship
        del_res = await client.delete(
            f"/api/v1/assets/{asset_a_id}/relationships/{rel_id}", headers=headers
        )
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True

        # Verify relationship removed from Asset A
        get_a_after = await client.get(f"/api/v1/assets/{asset_a_id}", headers=headers)
        assert len(get_a_after.json()["relationships"]) == 0


@pytest.mark.asyncio
async def test_rbac_contributor_and_viewer_restrictions() -> None:
    _, contributor1_token = await _create_test_user(UserRole.CONTRIBUTOR)
    _, contributor2_token = await _create_test_user(UserRole.CONTRIBUTOR)
    _, viewer_token = await _create_test_user(UserRole.VIEWER)
    _, admin_token = await _create_test_user(UserRole.ADMIN)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Viewer cannot create an asset
        viewer_post = await client.post(
            "/api/v1/assets",
            json={
                "title": "Viewer Upload Attempt",
                "asset_type": AssetType.NEWSPAPER_CLIPPING.value,
                "r2_object_key": "raw/clipping.jpg",
                "file_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
                "mime_type": "image/jpeg",
                "file_size_bytes": 1024,
                "dynamic_metadata": {
                    "newspaper_name": "Eenadu",
                    "publication_date": "2024-01-01",
                    "headline": "Headline",
                },
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert viewer_post.status_code == 403

        # 2. Contributor 1 creates an asset (draft)
        c1_res = await client.post(
            "/api/v1/assets",
            json={
                "title": "Draft Clipping by C1",
                "asset_type": AssetType.NEWSPAPER_CLIPPING.value,
                "r2_object_key": "raw/clipping.jpg",
                "file_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
                "mime_type": "image/jpeg",
                "file_size_bytes": 1024,
                "status": AssetStatus.DRAFT.value,
                "dynamic_metadata": {
                    "newspaper_name": "Eenadu",
                    "publication_date": "2024-01-01",
                    "headline": "Draft Headline",
                },
            },
            headers={"Authorization": f"Bearer {contributor1_token}"},
        )
        assert c1_res.status_code == 201
        asset_id = c1_res.json()["id"]

        # 3. Contributor 2 attempts to edit Contributor 1's asset -> 403
        c2_edit = await client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"title": "Hacked Title by C2"},
            headers={"Authorization": f"Bearer {contributor2_token}"},
        )
        assert c2_edit.status_code == 403
        assert "Contributors can only edit their own" in c2_edit.json()["detail"]

        # 4. Viewer attempts to edit -> 403
        viewer_edit = await client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"title": "Viewer Edit Attempt"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert viewer_edit.status_code == 403
        assert "Viewers do not have permission" in viewer_edit.json()["detail"]

        # 5. Contributor 1 can edit their own draft
        c1_edit = await client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"title": "Updated Draft Title by C1"},
            headers={"Authorization": f"Bearer {contributor1_token}"},
        )
        assert c1_edit.status_code == 200
        assert c1_edit.json()["title"] == "Updated Draft Title by C1"

        # 6. Admin marks asset as PUBLISHED
        admin_pub = await client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"status": AssetStatus.PUBLISHED.value},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_pub.status_code == 200
        assert admin_pub.json()["status"] == AssetStatus.PUBLISHED.value

        # 7. Contributor 1 attempts to edit now-published asset -> 403
        c1_edit_pub = await client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"title": "Contributor trying to edit published asset"},
            headers={"Authorization": f"Bearer {contributor1_token}"},
        )
        assert c1_edit_pub.status_code == 403
        assert "Contributors cannot edit published assets" in c1_edit_pub.json()["detail"]

        # 8. Viewer can view the asset
        viewer_get = await client.get(
            f"/api/v1/assets/{asset_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert viewer_get.status_code == 200
        assert viewer_get.json()["id"] == asset_id


@pytest.mark.asyncio
async def test_immutable_audit_logs_recorded() -> None:
    _, admin_token = await _create_test_user(UserRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create
        create_res = await client.post(
            "/api/v1/assets",
            json={
                "title": "Audited Asset",
                "asset_type": AssetType.ONLINE_NEWS_SOCIAL.value,
                "r2_object_key": "raw/news.html",
                "file_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
                "mime_type": "text/html",
                "file_size_bytes": 512,
                "dynamic_metadata": {
                    "platform_publisher": "Sakshi",
                    "source_url": "https://example.com/article1",
                    "published_date": "2024-02-14",
                    "author_handle": "Reporter",
                },
            },
            headers=headers,
        )
        assert create_res.status_code == 201
        asset_id = create_res.json()["id"]

        # View
        view_res = await client.get(f"/api/v1/assets/{asset_id}", headers=headers)
        assert view_res.status_code == 200

        # Edit
        edit_res = await client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"title": "Audited Asset Updated"},
            headers=headers,
        )
        assert edit_res.status_code == 200

        # Archive
        archive_res = await client.post(f"/api/v1/assets/{asset_id}/archive", headers=headers)
        assert archive_res.status_code == 200
        assert archive_res.json()["status"] == AssetStatus.ARCHIVED.value

    # Verify audit logs in DB
    async with AsyncSessionLocal() as session:
        logs_stmt = select(AuditLog).where(AuditLog.resource_id == str(asset_id))
        logs = (await session.execute(logs_stmt)).scalars().all()
        actions = {log.action for log in logs}

        assert "asset.upload" in actions
        assert "asset.view" in actions
        assert "asset.edit" in actions
        assert "asset.archive" in actions
