from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.seed_geography import load_seed_data, seed_geography
from app.db.session import AsyncSessionLocal, engine
from app.models.geography import GeoAlias, GeoEntity, GeoTier


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_geography_idempotent_execution() -> None:
    seed_data = load_seed_data()
    expected_codes = [e["code"] for e in seed_data["entities"]]

    # First execution
    entities_count_1, aliases_count_1 = await seed_geography()
    assert entities_count_1 == len(expected_codes)
    assert aliases_count_1 >= 14

    # Second execution: must not throw duplicate errors and return identical counts
    entities_count_2, aliases_count_2 = await seed_geography()
    assert entities_count_1 == entities_count_2
    assert aliases_count_1 == aliases_count_2

    async with AsyncSessionLocal() as session:
        entity_res = await session.execute(
            select(func.count(GeoEntity.id)).where(GeoEntity.code.in_(expected_codes))
        )
        assert entity_res.scalar_one() == len(expected_codes)

        alias_res = await session.execute(select(func.count(GeoAlias.id)))
        assert alias_res.scalar_one() >= aliases_count_1


@pytest.mark.asyncio
async def test_kovvur_assembly_constituency_hierarchy_and_alias() -> None:
    await seed_geography()

    async with AsyncSessionLocal() as session:
        # 1. Fetch Kovvur Assembly Constituency with eager loaded relationships
        stmt = (
            select(GeoEntity)
            .options(
                selectinload(GeoEntity.parent),
                selectinload(GeoEntity.children),
            )
            .where(GeoEntity.code == "AP-AC-054")
        )
        result = await session.execute(stmt)
        kovvur_ac = result.scalar_one()

        assert kovvur_ac.name == "Kovvur Assembly Constituency"
        assert kovvur_ac.tier == GeoTier.ASSEMBLY_CONSTITUENCY
        assert kovvur_ac.telugu_name == "కొవ్వూరు శాసనసభ నియోజకవర్గం"

        # 2. Verify parent district is East Godavari (post-2022 reorganization)
        assert kovvur_ac.parent is not None
        assert kovvur_ac.parent.name == "East Godavari"
        assert kovvur_ac.parent.tier == GeoTier.DISTRICT

        # 3. Verify child entities (Mandal & Municipality)
        child_codes = {c.code for c in kovvur_ac.children}
        assert "AP-MDL-KOV" in child_codes
        assert "AP-MN-KOV" in child_codes

        # 4. Verify grandchild entity (Village under Kovvur Mandal)
        mandal_stmt = (
            select(GeoEntity)
            .options(selectinload(GeoEntity.children))
            .where(GeoEntity.code == "AP-MDL-KOV")
        )
        mandal_res = await session.execute(mandal_stmt)
        mandal = mandal_res.scalar_one()
        mandal_child_codes = {c.code for c in mandal.children}
        assert "AP-VIL-KOV" in mandal_child_codes

        # 5. Verify pre-2022 West Godavari alias mapping
        alias_stmt = (
            select(GeoAlias)
            .options(selectinload(GeoAlias.mapped_entity))
            .where(
                GeoAlias.alias_name == "West Godavari (Undivided)",
                GeoAlias.mapped_entity_id == kovvur_ac.id,
            )
        )
        alias_res = await session.execute(alias_stmt)
        alias = alias_res.scalar_one()
        assert alias.valid_until_year == 2022
        assert alias.mapped_entity.code == "AP-AC-054"


@pytest.mark.asyncio
async def test_all_10_tiers_present_in_seeded_data() -> None:
    await seed_geography()

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(GeoEntity.tier).distinct())
        seeded_tiers = {row[0] for row in res.fetchall()}

        for tier in GeoTier:
            assert tier in seeded_tiers, f"Expected tier '{tier}' to be present in seeded data"
