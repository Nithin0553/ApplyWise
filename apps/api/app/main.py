from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title="ApplyWise API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "applywise-api", "version": "0.1.0"}
