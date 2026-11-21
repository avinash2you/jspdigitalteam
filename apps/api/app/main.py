from fastapi import FastAPI

from app.core.config import settings
from app.routers.me import router as me_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.include_router(me_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
