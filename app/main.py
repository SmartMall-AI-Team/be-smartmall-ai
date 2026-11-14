import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.core.config import Settings, get_settings
from app.database.session import create_database_engine
from app.routers.health import router as health_router
from app.routers.occurrences import router as occurrences_router
from app.routers.operations import router as operations_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_database_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="SmartMall AI API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(OperationalError)
    async def database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
        logger.warning("Banco de dados indisponível.")
        return JSONResponse(status_code=503, content={"detail": "Banco de dados indisponível."})

    app.include_router(health_router)
    app.include_router(occurrences_router)
    app.include_router(operations_router)
    return app


app = create_app()
