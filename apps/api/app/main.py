from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.applications.router import router as applications_router
from app.modules.auth import auth_router
from app.modules.evidence.router import router as evidence_router
from app.modules.generation.router import router as generation_router
from app.modules.sharing.router import router as sharing_router

app = FastAPI(
    title="ApplyWise API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(evidence_router)
app.include_router(generation_router)
app.include_router(applications_router)
app.include_router(sharing_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "applywise-api", "version": "0.1.0"}
