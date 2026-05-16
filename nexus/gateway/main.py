from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import from_url as redis_from_url

from gateway.router import router as gateway_router
from governance.main import app as governance_app
from shared.config import settings
from shared.logger import configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.nexus_log_level)
    app = FastAPI(title="Nexus Gateway", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.include_router(gateway_router)
    app.mount("/governance", governance_app)

    @app.on_event("startup")
    async def startup() -> None:
        app.state.redis = redis_from_url(settings.redis_url, decode_responses=True)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await app.state.redis.close()

    return app


app = create_app()

