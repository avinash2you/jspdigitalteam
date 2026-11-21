import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.asset import (
    Asset,
    AssetRelationship,
    AssetStatus,
    AssetType,
    CopyrightFlag,
    PrimaryLanguage,
    RelationType,
    VerificationStatus,
)
from app.models.document_chunk import DocumentChunk
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_assets_indexes_exist() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'assets' AND schemaname = 'public'"
            )
        )
        index_names = {row[0] for row in result.fetchall()}

        # Verify required indexes from Acceptance Criteria
        assert "ix_assets_file_sha256" in index_names
        assert "ix_assets_go_number" in index_names
        assert "ix_assets_source_url" in index_names
        assert "ix_assets_asset_type" in index_names


@pytest.mark.asyncio
async def test_asset_creation_with_all_fields_and_enums() -> None:
    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=f"uploader_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Asset Uploader",
            role=UserRole.CONTRIBUTOR,
        )
        session.add(user)
        await session.flush()

        asset_id = uuid.uuid4()
        sha256_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        asset = Asset(
            id=asset_id,
            title="AP Free Sand Policy Government Order 2024",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.TELUGU,
            source_name="AP Gazette",
            source_url="https://goir.ap.gov.in/orders/2024/sand_policy.pdf",
            r2_object_key="raw/2024/07/sand_policy.pdf",
            file_sha256=sha256_hash,
            mime_type="application/pdf",
            file_size_bytes=2048576,
            go_number="GO-MS-42",
            copyright_flag=CopyrightFlag.PUBLIC_DOMAIN,
            is_public_record=True,
            extracted_text="ఆంధ్రప్రదేశ్ ఉచిత ఇసుక విధానం వివరాలు...",
            english_summary="Detailed government order outlining the AP Free Sand Policy 2024.",
            tenglish_keywords=["isuka vidhanam", "free sand", "mines department"],
            subject_tags=["governance", "mining", "public welfare"],
            dynamic_metadata={
                "issuing_department": "Mines & Geology",
                "date_of_issue": "2024-07-08",
                "state": "Andhra Pradesh",
            },
            status=AssetStatus.PUBLISHED,
            verification_status=VerificationStatus.VERIFIED,
            uploaded_by=user.id,
        )
        session.add(asset)
        await session.commit()

        # Query back and verify all fields
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await session.execute(stmt)
        saved = result.scalar_one()

        assert saved.title == "AP Free Sand Policy Government Order 2024"
        assert saved.asset_type == AssetType.GOVERNMENT_DOCUMENT
        assert saved.primary_language == PrimaryLanguage.TELUGU
        assert saved.go_number == "GO-MS-42"
        assert saved.file_sha256 == sha256_hash
        assert saved.is_public_record is True
        assert saved.copyright_flag == CopyrightFlag.PUBLIC_DOMAIN
        assert saved.status == AssetStatus.PUBLISHED
        assert saved.verification_status == VerificationStatus.VERIFIED
        assert saved.dynamic_metadata["issuing_department"] == "Mines & Geology"
        assert "isuka vidhanam" in saved.tenglish_keywords
        assert "mining" in saved.subject_tags
        assert saved.uploaded_by == user.id
        assert saved.created_at is not None
        assert saved.updated_at is not None


@pytest.mark.asyncio
async def test_asset_relationships_and_cascade() -> None:
    async with AsyncSessionLocal() as session:
        # Create source and target assets
        asset1 = Asset(
            title="GO-MS-10 Original Policy",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key="raw/doc1.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=1000,
            go_number="GO-MS-10",
        )
        asset2 = Asset(
            title="GO-MS-25 Amendment Policy",
            asset_type=AssetType.GOVERNMENT_DOCUMENT,
            primary_language=PrimaryLanguage.ENGLISH,
            r2_object_key="raw/doc2.pdf",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="application/pdf",
            file_size_bytes=1200,
            go_number="GO-MS-25",
        )
        session.add_all([asset1, asset2])
        await session.flush()

        rel_id = uuid.uuid4()
        rel = AssetRelationship(
            id=rel_id,
            source_asset_id=asset2.id,
            target_asset_id=asset1.id,
            relation_type=RelationType.AMENDS,
        )
        session.add(rel)
        await session.commit()

        # Query relationship
        stmt = select(AssetRelationship).where(AssetRelationship.id == rel_id)
        res = await session.execute(stmt)
        saved_rel = res.scalar_one()
        assert saved_rel.relation_type == RelationType.AMENDS
        assert saved_rel.source_asset_id == asset2.id
        assert saved_rel.target_asset_id == asset1.id

        # Delete source asset, verifying cascade delete on relationship
        await session.delete(asset2)
        await session.commit()

        stmt_check = select(AssetRelationship).where(AssetRelationship.id == rel_id)
        res_check = await session.execute(stmt_check)
        assert res_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_document_chunks_with_pgvector_and_cascade() -> None:
    async with AsyncSessionLocal() as session:
        asset = Asset(
            title="Clipping Page 1",
            asset_type=AssetType.NEWSPAPER_CLIPPING,
            primary_language=PrimaryLanguage.TELUGU,
            r2_object_key="raw/clipping.jpg",
            file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            mime_type="image/jpeg",
            file_size_bytes=500000,
        )
        session.add(asset)
        await session.flush()

        # 768-dimensional mock embedding vector
        mock_embedding = [0.01 * (i % 10) for i in range(768)]

        chunk1 = DocumentChunk(
            asset_id=asset.id,
            chunk_index=0,
            page_number=1,
            bbox_json={"x": 50, "y": 100, "w": 400, "h": 200},
            start_sec=None,
            end_sec=None,
            text="ఈనాడు వార్తా కథనం మొదటి పేజీ ముఖ్యాంశాలు...",
            embedding=mock_embedding,
        )
        chunk2 = DocumentChunk(
            asset_id=asset.id,
            chunk_index=1,
            page_number=1,
            bbox_json={"x": 50, "y": 320, "w": 400, "h": 150},
            start_sec=None,
            end_sec=None,
            text="పథకం అమలు తీరుపై ప్రత్యేక విశ్లేషణ...",
            embedding=None,
        )
        session.add_all([chunk1, chunk2])
        await session.commit()

        # Query chunks back
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.asset_id == asset.id)
            .order_by(DocumentChunk.chunk_index)
        )
        res = await session.execute(stmt)
        chunks = res.scalars().all()
        assert len(chunks) == 2
        assert chunks[0].chunk_index == 0
        assert chunks[0].bbox_json == {"x": 50, "y": 100, "w": 400, "h": 200}
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 768
        assert chunks[1].chunk_index == 1
        assert chunks[1].embedding is None

        # Verify cascade delete on asset deletion
        await session.delete(asset)
        await session.commit()

        res_after = await session.execute(stmt)
        assert len(res_after.scalars().all()) == 0
