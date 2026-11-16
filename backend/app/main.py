"""FastAPI application factory."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, auth, billing, cron, notifications, sailings, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app() -> FastAPI:
    app = FastAPI(title="CruiseAlert API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(sailings.router, prefix="/sailings", tags=["sailings"])
    app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
    app.include_router(cron.router, prefix="/cron", tags=["cron"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
