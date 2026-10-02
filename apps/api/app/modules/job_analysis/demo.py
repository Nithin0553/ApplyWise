"""Run explicitly on localhost; production auth integration is outside this prototype."""

import os

from fastapi import FastAPI

from .router import router


def create_demo_app() -> FastAPI:
    if os.getenv("APP_ENV", "development") != "development":
        raise RuntimeError("F04 prototype demo requires APP_ENV=development")
    app = FastAPI(title="ApplyWise F04 local prototype", version="0.1.0")
    app.include_router(router)
    return app
