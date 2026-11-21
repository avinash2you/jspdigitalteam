import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.geography import GeoAlias, GeoEntity, GeoTier

SEED_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ap_geography_seed.json"


def load_seed_data() -> dict[str, Any]:
    """Synchronously load the geography JSON seed data file."""
    if not SEED_DATA_PATH.exists():
        raise FileNotFoundError(f"Seed data file not found at: {SEED_DATA_PATH}")

    with open(SEED_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


async def seed_geography(db: AsyncSession | None = None) -> tuple[int, int]:
    """Idempotently seed 10-tier Indian/AP geographic hierarchy and pre-2022 district aliases."""
    data = load_seed_data()

    entities_data: list[dict[str, Any]] = data.get("entities", [])
    aliases_data: list[dict[str, Any]] = data.get("aliases", [])

    async def _execute_seed(session: AsyncSession) -> tuple[int, int]:
        # 1. First pass: Upsert all GeoEntities without parent links
        code_to_entity: dict[str, GeoEntity] = {}
        for item in entities_data:
            code = item["code"]
            stmt = select(GeoEntity).where(GeoEntity.code == code)
            result = await session.execute(stmt)
            entity = result.scalar_one_or_none()

            if entity is None:
                entity = GeoEntity(
                    code=code,
                    name=item["name"],
                    telugu_name=item.get("telugu_name"),
                    tier=GeoTier(item["tier"]),
                    is_historical=item.get("is_historical", False),
                )
                session.add(entity)
            else:
                entity.name = item["name"]
                entity.telugu_name = item.get("telugu_name")
                entity.tier = GeoTier(item["tier"])
                entity.is_historical = item.get("is_historical", False)

            code_to_entity[code] = entity

        await session.flush()

        # 2. Second pass: Link parent entities hierarchically
        for item in entities_data:
            parent_code = item.get("parent_code")
            entity = code_to_entity[item["code"]]
            if parent_code and parent_code in code_to_entity:
                entity.parent_id = code_to_entity[parent_code].id
            else:
                entity.parent_id = None

        await session.flush()

        # 3. Third pass: Upsert GeoAliases idempotently
        alias_count = 0
        for alias_item in aliases_data:
            mapped_code = alias_item["mapped_entity_code"]
            if mapped_code not in code_to_entity:
                continue

            mapped_entity = code_to_entity[mapped_code]
            alias_name = alias_item["alias_name"]

            alias_stmt = select(GeoAlias).where(
                GeoAlias.alias_name == alias_name,
                GeoAlias.mapped_entity_id == mapped_entity.id,
            )
            alias_res = await session.execute(alias_stmt)
            existing_alias = alias_res.scalar_one_or_none()

            if existing_alias is None:
                new_alias = GeoAlias(
                    alias_name=alias_name,
                    mapped_entity_id=mapped_entity.id,
                    valid_until_year=alias_item.get("valid_until_year"),
                )
                session.add(new_alias)
                alias_count += 1
            else:
                existing_alias.valid_until_year = alias_item.get("valid_until_year")
                alias_count += 1

        await session.commit()
        return len(entities_data), alias_count

    if db is not None:
        return await _execute_seed(db)

    async with AsyncSessionLocal() as session:
        return await _execute_seed(session)


def main() -> None:
    entities_count, aliases_count = asyncio.run(seed_geography())
    print(
        f"Successfully seeded {entities_count} geographic entities and {aliases_count} aliases."
    )


if __name__ == "__main__":
    main()
