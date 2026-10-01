from fastapi import FastAPI

from app.core.config import settings
from app.modules.generation.router import router as generation_router

app = FastAPI(
    title="ApplyWise API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "applywise-api", "version": "0.1.0"}


# F07 preview endpoint: local development and UI prototyping only, because it
# carries no authentication yet (F01 owns that). Not mounted in production.
if settings.app_env != "production":
    app.include_router(generation_router)
