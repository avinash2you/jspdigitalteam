import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.asset import Asset, AssetType, PrimaryLanguage
from app.models.geography import AssetGeoTag, GeoAlias, GeoEntity, GeoTier


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_geography_tables_and_indexes_exist() -> None:
    async with AsyncSessionLocal() as session:
        # Check tables existence
        res_tables = await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename IN ('geo_entities', 'geo_aliases', 'asset_geo_tags')"
            )
        )
        tables = {row[0] for row in res_tables.fetchall()}
        assert "geo_entities" in tables
        assert "geo_aliases" in tables
        assert "asset_geo_tags" in tables

        # Check indexes existence
        res_indexes = await session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename = 'geo_entities'"
            )
        )
        indexes = {row[0] for row in res_indexes.fetchall()}
        assert "ix_geo_entities_name" in indexes
        assert "ix_geo_entities_tier" in indexes
        assert "ix_geo_entities_parent_id" in indexes
        assert "ix_geo_entities_code" in indexes


@pytest.mark.asyncio
async def test_geo_entity_hierarchy_and_10_tiers() -> None:
    suffix = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as session:
        # 1. India (Country tier)
        india = GeoEntity(
            name="India",
            telugu_name="భారతదేశం",
            tier=GeoTier.INDIA,
            code=f"IND-{suffix}",
        )
        session.add(india)
        await session.flush()

        # 2. Andhra Pradesh (State tier)
        ap = GeoEntity(
            name="Andhra Pradesh",
            telugu_name="ఆంధ్రప్రదేశ్",
            tier=GeoTier.STATE,
            parent_id=india.id,
            code=f"AP-{suffix}",
        )
        session.add(ap)
        await session.flush()

        # 3. Kakinada (District tier)
        kakinada = GeoEntity(
            name="Kakinada",
            telugu_name="కాకినాడ",
            tier=GeoTier.DISTRICT,
            parent_id=ap.id,
            code=f"AP-KKD-{suffix}",
        )
        session.add(kakinada)
        await session.flush()

        # 4. Pithapuram (Assembly Constituency tier)
        pithapuram = GeoEntity(
            name="Pithapuram",
            telugu_name="పిఠాపురం",
            tier=GeoTier.ASSEMBLY_CONSTITUENCY,
            parent_id=kakinada.id,
            code=f"AP-AC-{suffix}",
        )
        session.add(pithapuram)
        await session.commit()

        # Query hierarchy back
        stmt = select(GeoEntity).where(GeoEntity.id == pithapuram.id)
        res = await session.execute(stmt)
        saved_ac = res.scalar_one()

        assert saved_ac.name == "Pithapuram"
        assert saved_ac.telugu_name == "పిఠాపురం"
        assert saved_ac.tier == GeoTier.ASSEMBLY_CONSTITUENCY
        assert saved_ac.parent_id == kakinada.id


@pytest.mark.asyncio
async def test_geo_aliases_historical_mapping() -> None:
    suffix = uuid.uuid4().hex[:6]
    unique_alias = f"East Godavari (undivided) {suffix}"
    async with AsyncSessionLocal() as session:
        new_district = GeoEntity(
            name=f"Konaseema (Dr. B.R. Ambedkar) {suffix}",
            telugu_name="కోనసీమ",
            tier=GeoTier.DISTRICT,
            code=f"AP-KNS-{suffix}",
        )
        session.add(new_district)
        await session.flush()

        alias = GeoAlias(
            alias_name=unique_alias,
            mapped_entity_id=new_district.id,
            valid_until_year=2022,
        )
        session.add(alias)
        await session.commit()

        # Query alias and verify mapping
        stmt = select(GeoAlias).where(GeoAlias.alias_name == unique_alias)
        res = await session.execute(stmt)
        saved_alias = res.scalar_one()

        assert saved_alias.mapped_entity_id == new_district.id
        assert saved_alias.valid_until_year == 2022
        assert "Konaseema" in saved_alias.mapped_entity.name


@pytest.mark.asyncio
async def test_single_asset_multiple_geo_tags_across_different_tiers() -> None:
    async with AsyncSessionLocal() as session:
        # Create an asset
        asset = Asset(
            title="Pithapuram Development Review Order",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key="raw/pithapuram_order.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=102400,
        )
        session.add(asset)
        await session.flush()

        # Create 3 entities across different tiers
        state_entity = GeoEntity(
            name="Andhra Pradesh State",
            tier=GeoTier.STATE,
            code=f"AP-{uuid.uuid4().hex[:6]}",
        )
        district_entity = GeoEntity(
            name="Kakinada District",
            tier=GeoTier.DISTRICT,
            code=f"DIST-{uuid.uuid4().hex[:6]}",
        )
        ac_entity = GeoEntity(
            name="Pithapuram AC",
            tier=GeoTier.ASSEMBLY_CONSTITUENCY,
            code=f"AC-{uuid.uuid4().hex[:6]}",
        )
        mandal_entity = GeoEntity(
            name="Gollaprolu Mandal",
            tier=GeoTier.MANDAL,
            code=f"MANDAL-{uuid.uuid4().hex[:6]}",
        )
        session.add_all([state_entity, district_entity, ac_entity, mandal_entity])
        await session.flush()

        # Attach all 4 entities across 4 different tiers to the single asset
        tag1 = AssetGeoTag(asset_id=asset.id, geo_entity_id=state_entity.id)
        tag2 = AssetGeoTag(asset_id=asset.id, geo_entity_id=district_entity.id)
        tag3 = AssetGeoTag(asset_id=asset.id, geo_entity_id=ac_entity.id)
        tag4 = AssetGeoTag(asset_id=asset.id, geo_entity_id=mandal_entity.id)
        session.add_all([tag1, tag2, tag3, tag4])
        await session.commit()

        # Query back through relationship
        stmt = select(Asset).where(Asset.id == asset.id)
        res = await session.execute(stmt)
        saved_asset = res.scalar_one()

        attached_tiers = {geo.tier for geo in saved_asset.geo_entities}
        assert len(saved_asset.geo_entities) == 4
        assert GeoTier.STATE in attached_tiers
        assert GeoTier.DISTRICT in attached_tiers
        assert GeoTier.ASSEMBLY_CONSTITUENCY in attached_tiers
        assert GeoTier.MANDAL in attached_tiers

        # Verify reverse navigation from geo entity to assets
        stmt_geo = select(GeoEntity).where(GeoEntity.id == ac_entity.id)
        res_geo = await session.execute(stmt_geo)
        saved_ac = res_geo.scalar_one()
        assert len(saved_ac.assets) == 1
        assert saved_ac.assets[0].id == asset.id
