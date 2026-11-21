from fastapi import FastAPI

from app.core.config import settings
from app.routers.assets import router as assets_router
from app.routers.audit import router as audit_router
from app.routers.extraction import router as extraction_router
from app.routers.geography import router as geography_router
from app.routers.me import router as me_router
from app.routers.newspapers import router as newspapers_router
from app.routers.uploads import router as uploads_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.include_router(me_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(uploads_router, prefix=settings.API_V1_STR)
app.include_router(geography_router, prefix=settings.API_V1_STR)
app.include_router(assets_router, prefix=settings.API_V1_STR)
app.include_router(extraction_router, prefix=settings.API_V1_STR)
app.include_router(newspapers_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
