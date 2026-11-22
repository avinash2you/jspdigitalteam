import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select

from app.adapters.base import (
    AssetSearchDocument,
    SearchFilters,
    SearchProvider,
)
from app.adapters.registry import get_search_provider
from app.adapters.search_postgres import PostgresHybridSearchProvider
from app.db.seed_geography import seed_geography
from app.db.session import AsyncSessionLocal, engine
from app.models.asset import Asset, AssetStatus, AssetType, PrimaryLanguage
from app.models.document_chunk import DocumentChunk
from app.models.geography import AssetGeoTag, GeoAlias, GeoEntity
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


async def _create_test_user() -> User:
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"search_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=clerk_id,
            email=email,
            full_name="Search Tester",
            role=UserRole.RESEARCHER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_search_provider_registration_and_protocol() -> None:
    provider = get_search_provider("postgres")
    assert isinstance(provider, SearchProvider)
    assert isinstance(provider, PostgresHybridSearchProvider)

    # Test sync index_asset and delete_asset protocol methods
    doc = AssetSearchDocument(
        id=str(uuid.uuid4()),
        title="Protocol Test Asset",
        content_text="Sample text for indexing protocol verification",
        asset_type="government_document",
        tags=["protocol", "test"],
    )
    provider.index_asset(doc)
    res = provider.search("Protocol")
    assert res.total >= 1
    assert any(item.id == doc.id for item in res.items)

    provider.delete_asset(doc.id)
    res_after = provider.search(f"ID:{doc.id}")
    assert not any(item.id == doc.id for item in res_after.items)


@pytest.mark.asyncio
async def test_postgres_search_english_telugu_tenglish_and_go_number() -> None:
    user = await _create_test_user()
    provider = PostgresHybridSearchProvider()

    test_suffix = uuid.uuid4().hex[:6]

    async with AsyncSessionLocal() as session:
        # 1. English document on Irrigation
        a1 = Asset(
            title=f"Polavaram Irrigation Project Progress Report {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=4096,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="The Polavaram multi-purpose project ensures irrigation water to Godavari delta districts.",
            english_summary="Comprehensive progress report on Polavaram dam construction.",
            tenglish_keywords=["polavaram", "dam", "irrigation"],
            dynamic_metadata={"issuing_department": "Water Resources", "date_of_issue": "2024-01-15"},
        )
        session.add(a1)

        # 2. Telugu Unicode document on Rythu Bharosa
        a2 = Asset(
            title=f"రైతు భరోసా పథకం నిధుల విడుదల {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=4096,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="ఆంధ్రప్రదేశ్ రాష్ట్రంలో అర్హులైన రైతులకు రైతు భరోసా పథకం ద్వారా ఆర్థిక సాయం అందించడం జరిగింది.",
            english_summary="Financial assistance disbursed under farmer welfare scheme.",
            tenglish_keywords=["rythu bharosa", "pathakam", "farmer welfare"],
            go_number="GO-MS-888",
            dynamic_metadata={"issuing_department": "Agriculture", "date_of_issue": "2024-02-20"},
        )
        session.add(a2)

        # 3. Tenglish keywords in Newspaper clipping
        a3 = Asset(
            title=f"Pawan Kalyan Varahi Yatra Speech {test_suffix}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/{uuid.uuid4().hex}.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=2048,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="వారాహి యాత్రలో భాగంగా భారీ బహిరంగ సభ నిర్వహించారు.",
            english_summary="Public rally addressed during Varahi tour.",
            tenglish_keywords=["varahi yatra", "pawan kalyan", "sabha"],
            dynamic_metadata={
                "newspaper_name": "Eenadu",
                "headline": "Historic Public Gathering at Kakinada",
                "publication_date": "2024-03-10",
            },
        )
        session.add(a3)

        # 4. Specific GO Number document
        a4 = Asset(
            title=f"Secretariat Allotment Order {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=1024,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            go_number="GO-RT-777",
            extracted_text="Government Order regarding office accommodation in Amaravati Secretariat.",
            english_summary="Order sanctioning office allotment.",
            dynamic_metadata={"issuing_department": "General Administration", "date_of_issue": "2024-04-01"},
        )
        session.add(a4)

        # 5. Draft document (MUST BE EXCLUDED)
        a5_draft = Asset(
            title=f"Draft Secret Document {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=1024,
            status=AssetStatus.DRAFT,
            uploaded_by=user.id,
            extracted_text="Top secret internal memo mentioning Polavaram and GO-RT-777.",
        )
        session.add(a5_draft)

        await session.commit()

    # 1. Match English query & verify highlighted snippet
    res_en = await provider.asearch("Polavaram")
    matching_en_ids = [item.id for item in res_en.items]
    assert str(a1.id) in matching_en_ids
    assert str(a5_draft.id) not in matching_en_ids
    item_en = next(item for item in res_en.items if item.id == str(a1.id))
    assert "<mark>" in item_en.snippet
    assert "Polavaram" in item_en.snippet

    # 2. Match Telugu Unicode query & verify highlighted snippet
    res_te = await provider.asearch("రైతు భరోసా")
    matching_te_ids = [item.id for item in res_te.items]
    assert str(a2.id) in matching_te_ids
    item_te = next(item for item in res_te.items if item.id == str(a2.id))
    assert "<mark>" in item_te.snippet or "రైతు" in item_te.snippet

    # 3. Match Tenglish keyword query ('rythu bharosa')
    res_teng = await provider.asearch("rythu bharosa")
    assert any(item.id == str(a2.id) for item in res_teng.items)

    # 4. Match exact GO number with highest score
    res_go = await provider.asearch("GO-RT-777")
    assert len(res_go.items) >= 1
    assert res_go.items[0].id == str(a4.id)
    assert res_go.items[0].go_number == "GO-RT-777"
    assert res_go.items[0].score >= 10.0


@pytest.mark.asyncio
async def test_combined_filters_geo_expansion_asset_type_and_dates() -> None:
    await seed_geography()
    user = await _create_test_user()
    provider = PostgresHybridSearchProvider()

    test_suffix = uuid.uuid4().hex[:6]

    # Retrieve East Godavari district and a historical alias
    async with AsyncSessionLocal() as session:
        geo_stmt = select(GeoEntity).where(GeoEntity.code == "AP-EGD")
        east_godavari = (await session.execute(geo_stmt)).scalar_one()
        eg_id = east_godavari.id

        alias_stmt = select(GeoAlias).limit(1)
        alias_obj = (await session.execute(alias_stmt)).scalar_one()
        mapped_id = alias_obj.mapped_entity_id
        hist_id = alias_obj.historical_entity_id

    async with AsyncSessionLocal() as session:
        # Asset 1: Newspaper clipping in East Godavari, March 2024
        doc1 = Asset(
            title=f"Kakinada Port Development News {test_suffix}",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key=f"raw/{uuid.uuid4().hex}.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=2048,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="కాకినాడ పోర్టు విస్తరణపై ప్రత్యేక నివేదిక.",
            dynamic_metadata={
                "newspaper_name": "Eenadu",
                "publication_date": "2024-03-15",
                "issuing_department": "Ports",
            },
        )
        session.add(doc1)
        await session.flush()
        session.add(AssetGeoTag(asset_id=doc1.id, geo_entity_id=eg_id))

        # Asset 2: Government Order tagged with alias-mapped geo entity, February 2024
        doc2 = Asset(
            title=f"Revenue Land Allotment GO {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=2048,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="Revenue department land sanction order.",
            dynamic_metadata={
                "date_of_issue": "2024-02-10",
                "issuing_department": "Revenue",
            },
        )
        session.add(doc2)
        await session.flush()
        if mapped_id:
            session.add(AssetGeoTag(asset_id=doc2.id, geo_entity_id=mapped_id))

        await session.commit()

    # 1. Filter by asset_type
    filter_type = SearchFilters(asset_type="newspaper_clipping")
    res_type = await provider.asearch(test_suffix, filters=filter_type)
    returned_type_ids = {item.id for item in res_type.items}
    assert str(doc1.id) in returned_type_ids
    assert str(doc2.id) not in returned_type_ids

    # 2. Filter by date range (March only)
    filter_date = SearchFilters(date_from="2024-03-01", date_to="2024-03-31")
    res_date = await provider.asearch(test_suffix, filters=filter_date)
    returned_date_ids = {item.id for item in res_date.items}
    assert str(doc1.id) in returned_date_ids
    assert str(doc2.id) not in returned_date_ids

    # 3. Filter by geo_id (East Godavari)
    filter_geo = SearchFilters(geo_ids=[eg_id])
    res_geo = await provider.asearch(test_suffix, filters=filter_geo)
    returned_geo_ids = {item.id for item in res_geo.items}
    assert str(doc1.id) in returned_geo_ids

    # 4. Filter by pre-2022 historical alias geo_id (alias expansion)
    if hist_id:
        filter_alias = SearchFilters(geo_ids=[hist_id])
        res_alias = await provider.asearch(test_suffix, filters=filter_alias)
        returned_alias_ids = {item.id for item in res_alias.items}
        assert str(doc2.id) in returned_alias_ids


@pytest.mark.asyncio
async def test_pgvector_semantic_search_with_rrf() -> None:
    user = await _create_test_user()
    provider = PostgresHybridSearchProvider()

    test_suffix = uuid.uuid4().hex[:6]
    vec_a = [0.1] * 768
    vec_b = [0.9] * 768

    async with AsyncSessionLocal() as session:
        # Doc A: matches query text weakly but has high semantic similarity
        doc_a = Asset(
            title=f"Agricultural Subsidies Overview {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=1024,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="Fertilizer and seed support details for rural farmers.",
        )
        session.add(doc_a)
        await session.flush()

        chunk_a = DocumentChunk(
            asset_id=doc_a.id,
            chunk_index=0,
            text="Fertilizer and seed support details for rural farmers.",
            embedding=vec_a,
        )
        session.add(chunk_a)

        # Doc B: matches text strongly
        doc_b = Asset(
            title=f"Farmer Assistance Programs {test_suffix}",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key=f"raw/{uuid.uuid4().hex}.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=1024,
            status=AssetStatus.PUBLISHED,
            uploaded_by=user.id,
            extracted_text="Farmer Assistance Program allocations across Andhra Pradesh.",
        )
        session.add(doc_b)
        await session.flush()

        chunk_b = DocumentChunk(
            asset_id=doc_b.id,
            chunk_index=0,
            text="Farmer Assistance Program allocations across Andhra Pradesh.",
            embedding=vec_b,
        )
        session.add(chunk_b)

        await session.commit()

    # Search with embedding close to vec_a: RRF incorporates vector distance ranking
    query_emb = [0.1] * 768
    res = await provider.asearch("Farmer", query_embedding=query_emb)
    assert res.total >= 2
    matched_ids = [item.id for item in res.items]
    assert str(doc_a.id) in matched_ids
    assert str(doc_b.id) in matched_ids
