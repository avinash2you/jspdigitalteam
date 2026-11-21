import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.db.seed_geography import seed_geography
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.geography import GeoEntity
from app.models.user import User, UserRole
from app.services.geography import GeographyService


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


async def _create_test_user(role: UserRole = UserRole.VIEWER) -> tuple[User, str]:
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=clerk_id,
            email=email,
            full_name="Test User",
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token({"sub": clerk_id, "email": email})
    return user, token


@pytest.mark.asyncio
async def test_geography_search_by_name_and_alias() -> None:
    await seed_geography()
    _, token = await _create_test_user(UserRole.VIEWER)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Search 'West Godavari' - matches district directly and Kovvur AC via historical alias
        res_wg = await client.get("/api/v1/geography/search?q=West Godavari", headers=headers)
        assert res_wg.status_code == 200
        items_wg = res_wg.json()
        assert len(items_wg) >= 2

        wg_district = next((i for i in items_wg if i["code"] == "AP-WGD"), None)
        assert wg_district is not None
        assert wg_district["tier"] == "district"
        assert wg_district["matched_alias"] is None

        kovvur_alias_match = next((i for i in items_wg if i["code"] == "AP-AC-054"), None)
        assert kovvur_alias_match is not None
        assert kovvur_alias_match["tier"] == "assembly_constituency"
        assert kovvur_alias_match["matched_alias"] == "West Godavari (Undivided)"

        # 2. Search 'Kovvur' - returns multiple administrative tiers
        res_kovvur = await client.get("/api/v1/geography/search?q=Kovvur", headers=headers)
        assert res_kovvur.status_code == 200
        items_kovvur = res_kovvur.json()
        tiers = {i["tier"] for i in items_kovvur}
        assert "assembly_constituency" in tiers
        assert "mandal" in tiers
        assert "municipality" in tiers
        assert "village" in tiers

        # 3. Filtered search by tier
        res_tier = await client.get(
            "/api/v1/geography/search?q=Kovvur&tier=assembly_constituency", headers=headers
        )
        assert res_tier.status_code == 200
        items_tier = res_tier.json()
        assert len(items_tier) == 1
        assert items_tier[0]["code"] == "AP-AC-054"
        assert items_tier[0]["tier"] == "assembly_constituency"


@pytest.mark.asyncio
async def test_resolve_geo_filter_ids_for_kovvur() -> None:
    await seed_geography()
    _, token = await _create_test_user(UserRole.RESEARCHER)

    async with AsyncSessionLocal() as session:
        # Fetch Kovvur AC and West Godavari district
        kovvur_stmt = select(GeoEntity).where(GeoEntity.code == "AP-AC-054")
        kovvur_ac = (await session.execute(kovvur_stmt)).scalar_one()

        wg_stmt = select(GeoEntity).where(GeoEntity.code == "AP-WGD")
        wg_district = (await session.execute(wg_stmt)).scalar_one()

        mandal_stmt = select(GeoEntity).where(GeoEntity.code == "AP-MDL-KOV")
        kovvur_mandal = (await session.execute(mandal_stmt)).scalar_one()

        village_stmt = select(GeoEntity).where(GeoEntity.code == "AP-VIL-KOV")
        kovvur_village = (await session.execute(village_stmt)).scalar_one()

        # 1. Service resolution check
        resolved_ids = await GeographyService.resolve_geo_filter_ids(session, [kovvur_ac.id])

        # Assert self
        assert kovvur_ac.id in resolved_ids
        # Assert descendants (mandal, village)
        assert kovvur_mandal.id in resolved_ids
        assert kovvur_village.id in resolved_ids
        # Assert linked pre-2022 alias entity (West Godavari district)
        assert wg_district.id in resolved_ids

    # 2. HTTP Endpoint resolution check
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/geography/resolve-filters",
            json={"geo_ids": [str(kovvur_ac.id)]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        endpoint_resolved = {uuid.UUID(uid) for uid in res.json()["resolved_ids"]}
        assert kovvur_ac.id in endpoint_resolved
        assert kovvur_mandal.id in endpoint_resolved
        assert kovvur_village.id in endpoint_resolved
        assert wg_district.id in endpoint_resolved


@pytest.mark.asyncio
async def test_geography_tree_lineage_and_children() -> None:
    await seed_geography()
    _, token = await _create_test_user(UserRole.VIEWER)
    transport = ASGITransport(app=app)

    async with AsyncSessionLocal() as session:
        stmt = select(GeoEntity).where(GeoEntity.code == "AP-AC-054")
        kovvur_ac = (await session.execute(stmt)).scalar_one()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch Kovvur tree
        res = await client.get(f"/api/v1/geography/{kovvur_ac.id}/tree", headers=headers)
        assert res.status_code == 200
        tree = res.json()

        # Entity
        assert tree["entity"]["id"] == str(kovvur_ac.id)
        assert tree["entity"]["name"] == "Kovvur Assembly Constituency"
        assert tree["entity"]["tier"] == "assembly_constituency"

        # Ancestors: India -> Andhra Pradesh -> East Godavari
        ancestor_codes = [a["code"] for a in tree["ancestors"]]
        assert "IND" in ancestor_codes
        assert "AP" in ancestor_codes
        assert "AP-EGD" in ancestor_codes

        # Immediate children: Kovvur Mandal and Kovvur Municipality
        child_codes = [c["code"] for c in tree["children"]]
        assert "AP-MDL-KOV" in child_codes
        assert "AP-MN-KOV" in child_codes

        # 2. Non-existent ID returns 404
        random_id = uuid.uuid4()
        res_404 = await client.get(f"/api/v1/geography/{random_id}/tree", headers=headers)
        assert res_404.status_code == 404

        # 3. Unauthenticated request returns 401
        res_unauth = await client.get(f"/api/v1/geography/{kovvur_ac.id}/tree")
        assert res_unauth.status_code == 401
