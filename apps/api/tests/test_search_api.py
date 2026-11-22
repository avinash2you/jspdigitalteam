import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.db.seed_geography import seed_geography
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.asset import Asset, AssetStatus, AssetType, PrimaryLanguage, VerificationStatus
from app.models.geography import AssetGeoTag, GeoAlias, GeoEntity
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


async def _create_user_with_role(role: UserRole) -> tuple[User, str]:
    clerk_id = f"user_{role.value}_{uuid.uuid4().hex[:8]}"
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
async def test_search_endpoint_rbac_all_6_roles_allowed_unauthenticated_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.get("/api/v1/search?q=test")
        assert res_unauth.status_code == 401

        # 2. All 6 authenticated roles can access
        for role in UserRole:
            _, token = await _create_user_with_role(role)
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get("/api/v1/search?q=test", headers=headers)
            assert res.status_code == 200, f"Role {role.value} should be allowed to search"
            data = res.json()
            assert "items" in data
            assert "total" in data


@pytest.mark.asyncio
async def test_search_api_combined_filters_and_highlighted_snippets() -> None:
    await seed_geography()
    _, token = await _create_user_with_role(UserRole.VIEWER)
    test_run = uuid.uuid4().hex[:8]

    # Fetch East Godavari & historical alias
    async with AsyncSessionLocal() as session:
        geo_stmt = select(GeoEntity).where(GeoEntity.code == "AP-EGD")
        east_godavari = (await session.execute(geo_stmt)).scalar_one()
        eg_id = east_godavari.id

        alias_stmt = select(GeoAlias).limit(1)
        alias_obj = (await session.execute(alias_stmt)).scalar_one()
        mapped_id = alias_obj.mapped_entity_id
        hist_id = alias_obj.historical_entity_id

    # Create published assets
    async with AsyncSessionLocal() as session:
        # 1. Telugu newspaper clipping with East Godavari geo tag
        c1 = Asset(
            title=f"East Godavari Varahi Sabha {test_run}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/search/{test_run}_1.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=2048,
            status=AssetStatus.PUBLISHED,
            verification_status=VerificationStatus.VERIFIED,
            extracted_text="తూర్పు గోదావరి జిల్లాలో వారాహి యాత్ర విజయవంతంగా సాగింది. వేలాదిగా తరలివచ్చిన ప్రజలు.",
            dynamic_metadata={
                "newspaper_name": "Eenadu",
                "headline": "Massive Turnout in Godavari",
                "publication_date": "2024-03-15",
                "issuing_department": "Public Relations",
            },
        )
        session.add(c1)
        await session.flush()
        session.add(AssetGeoTag(asset_id=c1.id, geo_entity_id=eg_id))

        # 2. English Government Document on Agriculture / Irrigation with alias
        c2 = Asset(
            title=f"Water Resources Budget Sanction {test_run}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/search/{test_run}_2.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=4096,
            status=AssetStatus.PUBLISHED,
            verification_status=VerificationStatus.VERIFIED,
            go_number="GO-MS-999",
            extracted_text="Government Order sanctioning budget for canal modernization and irrigation support.",
            english_summary="Sanction order for canal desiltation.",
            tenglish_keywords=["polavaram", "canals", "irrigation"],
            dynamic_metadata={
                "date_of_issue": "2024-02-20",
                "issuing_department": "Water Resources",
            },
        )
        session.add(c2)
        await session.flush()
        if mapped_id:
            session.add(AssetGeoTag(asset_id=c2.id, geo_entity_id=mapped_id))

        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Search Telugu query ('గోదావరి')
        res_te = await client.get("/api/v1/search?q=గోదావరి", headers=headers)
        assert res_te.status_code == 200
        te_data = res_te.json()
        assert te_data["total"] >= 1
        te_items = [i for i in te_data["items"] if i["id"] == str(c1.id)]
        assert len(te_items) == 1
        assert "<mark>" in te_items[0]["snippet"] or "గోదావరి" in te_items[0]["snippet"]
        assert te_items[0]["preview_url"] is not None

        # 2. Search exact GO Number ('GO-MS-999')
        res_go = await client.get("/api/v1/search?q=GO-MS-999", headers=headers)
        assert res_go.status_code == 200
        go_data = res_go.json()
        assert go_data["total"] >= 1
        assert go_data["items"][0]["id"] == str(c2.id)
        assert go_data["items"][0]["go_number"] == "GO-MS-999"

        # 3. Filter by department (Water Resources)
        res_dept = await client.get(
            f"/api/v1/search?q={test_run}&department=Water Resources", headers=headers
        )
        assert res_dept.status_code == 200
        dept_data = res_dept.json()
        assert len(dept_data["items"]) == 1
        assert dept_data["items"][0]["id"] == str(c2.id)

        # 4. Filter by asset_types (newspaper_clipping)
        res_type = await client.get(
            f"/api/v1/search?q={test_run}&asset_types=newspaper_clipping", headers=headers
        )
        assert res_type.status_code == 200
        type_data = res_type.json()
        assert len(type_data["items"]) == 1
        assert type_data["items"][0]["id"] == str(c1.id)

        # 5. Filter by geo_ids with alias expansion
        if hist_id:
            res_geo = await client.get(
                f"/api/v1/search?q={test_run}&geo_ids={hist_id}", headers=headers
            )
            assert res_geo.status_code == 200
            geo_data = res_geo.json()
            assert any(item["id"] == str(c2.id) for item in geo_data["items"])
