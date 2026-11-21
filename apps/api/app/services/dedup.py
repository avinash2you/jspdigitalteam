import re
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


def normalize_go_number(go_number: str | None) -> str | None:
    if not go_number or not go_number.strip():
        return None
    cleaned = re.sub(r"\s+", " ", go_number.strip())
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    cleaned = re.sub(r"\s*/\s*", "/", cleaned)
    return cleaned.upper()


def normalize_url(url: str | None) -> str | None:
    if not url or not url.strip():
        return None
    clean = url.strip()
    if not clean.startswith(("http://", "https://")):
        clean = "https://" + clean
    parsed = urlparse(clean)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))


class DuplicateMatch(BaseModel):
    id: str
    title: str
    asset_type: str
    match_reason: str


class DeduplicationService:
    """Service to detect duplicates across SHA-256 hash, GO numbers, and source URLs."""

    @staticmethod
    async def check_duplicates(
        db: AsyncSession,
        file_sha256: str | None = None,
        go_number: str | None = None,
        source_url: str | None = None,
    ) -> list[DuplicateMatch]:
        matches: list[DuplicateMatch] = []
        seen_asset_ids: set[str] = set()

        # 1. Match by SHA-256 checksum
        if file_sha256 and file_sha256.strip():
            clean_hash = file_sha256.strip().lower()
            stmt = select(Asset).where(func.lower(Asset.file_sha256) == clean_hash)
            res = await db.execute(stmt)
            for asset in res.scalars().all():
                asset_id_str = str(asset.id)
                if asset_id_str not in seen_asset_ids:
                    seen_asset_ids.add(asset_id_str)
                    matches.append(
                        DuplicateMatch(
                            id=asset_id_str,
                            title=asset.title,
                            asset_type=asset.asset_type.value,
                            match_reason="sha256_checksum",
                        )
                    )

        # 2. Match by normalized GO number
        if go_number and go_number.strip():
            norm_go = normalize_go_number(go_number)
            if norm_go:
                stripped_norm_go = norm_go.replace(" ", "").replace("-", "")
                stmt = select(Asset).where(
                    Asset.go_number.is_not(None),
                    func.upper(
                        func.replace(func.replace(Asset.go_number, " ", ""), "-", "")
                    )
                    == stripped_norm_go,
                )
                res = await db.execute(stmt)
                for asset in res.scalars().all():
                    asset_id_str = str(asset.id)
                    if asset_id_str not in seen_asset_ids:
                        seen_asset_ids.add(asset_id_str)
                        matches.append(
                            DuplicateMatch(
                                id=asset_id_str,
                                title=asset.title,
                                asset_type=asset.asset_type.value,
                                match_reason="go_number",
                            )
                        )

        # 3. Match by canonical source URL
        if source_url and source_url.strip():
            norm_url = normalize_url(source_url)
            if norm_url:
                stmt = select(Asset).where(
                    Asset.source_url.is_not(None),
                    func.lower(func.rtrim(Asset.source_url, "/")) == norm_url.lower(),
                )
                res = await db.execute(stmt)
                for asset in res.scalars().all():
                    asset_id_str = str(asset.id)
                    if asset_id_str not in seen_asset_ids:
                        seen_asset_ids.add(asset_id_str)
                        matches.append(
                            DuplicateMatch(
                                id=asset_id_str,
                                title=asset.title,
                                asset_type=asset.asset_type.value,
                                match_reason="source_url",
                            )
                        )

        return matches
