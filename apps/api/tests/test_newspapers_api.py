import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.db.seed_geography import seed_geography
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.asset import Asset, AssetStatus, AssetType, PrimaryLanguage
from app.models.geography import AssetGeoTag, GeoAlias, GeoEntity
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


async def _create_test_user(role: UserRole = UserRole.VIEWER) -> tuple[User, str]:
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
async def test_newspaper_filtering_and_exclusion_of_other_asset_types() -> None:
    await seed_geography()
    user, token = await _create_test_user(UserRole.VIEWER)

    # Fetch a seeded district and child or alias
    async with AsyncSessionLocal() as session:
        geo_stmt = select(GeoEntity).where(GeoEntity.code == "AP-EGD")
        east_godavari = (await session.execute(geo_stmt)).scalar_one()
        eg_id = east_godavari.id

        # Also get a historical alias
        alias_stmt = select(GeoAlias).limit(1)
        alias_obj = (await session.execute(alias_stmt)).scalar_one()
        alias_mapped_id = alias_obj.mapped_entity_id
        hist_id = alias_obj.historical_entity_id

    test_run_id = uuid.uuid4().hex[:8]
    p1_name = f"Eenadu_{test_run_id}"
    p2_name = f"Sakshi_{test_run_id}"
    p3_name = f"AndhraJyothy_{test_run_id}"
    edition_name = f"VizagEdition_{test_run_id}"

    # Create test assets
    async with AsyncSessionLocal() as session:
        # 1. Published Eenadu clipping tagged with East Godavari
        c1 = Asset(
            title=f"Eenadu Headline on Irrigation {test_run_id}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/2024/03/{uuid.uuid4().hex}.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=1024,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="Eenadu Telugu OCR Text on East Godavari canals",
            dynamic_metadata={
                "newspaper_name": p1_name,
                "headline": "Historic Godavari Irrigation Milestone",
                "edition": "Amaravati",
                "publication_date": "2024-03-05",
                "page_number": 1,
            },
        )
        session.add(c1)
        await session.flush()
        session.add(AssetGeoTag(asset_id=c1.id, geo_entity_id=eg_id))

        # 2. Published Sakshi clipping in Visakhapatnam edition
        c2 = Asset(
            title=f"Sakshi Headline on Harbor {test_run_id}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/2024/03/{uuid.uuid4().hex}.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=1024,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="Sakshi Text on Vizag port expansion",
            dynamic_metadata={
                "newspaper_name": p2_name,
                "headline": "Vizag Harbor Development Plans",
                "edition": edition_name,
                "publication_date": "2024-03-20",
                "page_number": 3,
            },
        )
        session.add(c2)

        # 3. Published Andhra Jyothy clipping in April
        c3 = Asset(
            title=f"Andhra Jyothy Headline on Varahi {test_run_id}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/2024/04/{uuid.uuid4().hex}.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=1024,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="Andhra Jyothy Text on Varahi tour",
            dynamic_metadata={
                "newspaper_name": p3_name,
                "headline": "Massive Varahi Yatra Meeting",
                "edition": "Kakinada",
                "publication_date": "2024-04-12",
                "page_number": 1,
            },
        )
        session.add(c3)
        await session.flush()
        if alias_mapped_id:
            session.add(AssetGeoTag(asset_id=c3.id, geo_entity_id=alias_mapped_id))

        # 4. Draft Eenadu clipping (MUST BE EXCLUDED)
        c4_draft = Asset(
            title=f"Draft Eenadu Clipping {test_run_id}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/2024/03/{uuid.uuid4().hex}.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=1024,
            status=AssetStatus.DRAFT,
            uploaded_by=user.id,
            dynamic_metadata={
                "newspaper_name": p1_name,
                "headline": "Draft Headline",
                "publication_date": "2024-03-01",
            },
        )
        session.add(c4_draft)

        # 5. Published Government Document (MUST BE EXCLUDED)
        gov_doc = Asset(
            title=f"Published Government Order {test_run_id}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/2024/03/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=2048,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            dynamic_metadata={
                "go_number": "GO-MS-104",
                "issuing_department": "Revenue",
                "date_of_issue": "2024-03-05",
                "subject": "Allotment",
                "state": "AP",
            },
        )
        session.add(gov_doc)

        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Base list: returns all published newspaper clippings, excludes drafts and gov docs
        res_all = await client.get(f"/api/v1/newspapers?newspaper_name={test_run_id}", headers=headers)
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert data_all["total"] == 3
        # Ensure non-clippings and drafts are excluded
        returned_ids = {item["id"] for item in data_all["items"]}
        assert str(c4_draft.id) not in returned_ids
        assert str(gov_doc.id) not in returned_ids
        assert str(c1.id) in returned_ids
        assert str(c2.id) in returned_ids
        assert str(c3.id) in returned_ids

        # 2. Filter by newspaper_name (p1_name)
        res_eenadu = await client.get(f"/api/v1/newspapers?newspaper_name={p1_name}", headers=headers)
        assert res_eenadu.status_code == 200
        eenadu_items = res_eenadu.json()["items"]
        assert len(eenadu_items) == 1
        assert eenadu_items[0]["id"] == str(c1.id)
        assert eenadu_items[0]["newspaper_name"] == p1_name
        assert eenadu_items[0]["headline"] == "Historic Godavari Irrigation Milestone"
        assert eenadu_items[0]["preview_url"] != ""

        # 3. Filter by edition (edition_name)
        res_ed = await client.get(f"/api/v1/newspapers?edition={edition_name}", headers=headers)
        assert res_ed.status_code == 200
        ed_items = res_ed.json()["items"]
        assert len(ed_items) == 1
        assert ed_items[0]["id"] == str(c2.id)
        assert ed_items[0]["newspaper_name"] == p2_name
        assert ed_items[0]["edition"] == edition_name

        # 4. Filter by date range (2024-03-01 to 2024-03-31) and matching test items
        res_dates = await client.get(
            f"/api/v1/newspapers?newspaper_name={test_run_id}&date_from=2024-03-01&date_to=2024-03-31",
            headers=headers,
        )
        assert res_dates.status_code == 200
        date_items = res_dates.json()["items"]
        assert len(date_items) == 2
        date_item_ids = {item["id"] for item in date_items}
        assert str(c1.id) in date_item_ids
        assert str(c2.id) in date_item_ids
        assert str(c3.id) not in date_item_ids

        # 5. Filter by geo_id (East Godavari)
        res_geo = await client.get(
            f"/api/v1/newspapers?newspaper_name={test_run_id}&geo_id={eg_id}",
            headers=headers,
        )
        assert res_geo.status_code == 200
        geo_items = res_geo.json()["items"]
        assert len(geo_items) == 1
        assert geo_items[0]["id"] == str(c1.id)
        assert len(geo_items[0]["geo_tags"]) == 1
        assert geo_items[0]["geo_tags"][0]["code"] == "AP-EGD"

        # 6. Filter by historical alias geo_id (alias expansion)
        if hist_id:
            res_alias = await client.get(
                f"/api/v1/newspapers?newspaper_name={test_run_id}&geo_id={hist_id}",
                headers=headers,
            )
            assert res_alias.status_code == 200
            alias_items = res_alias.json()["items"]
            assert any(item["id"] == str(c3.id) for item in alias_items)
