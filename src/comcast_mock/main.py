import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from comcast_mock import database
from comcast_mock.config import settings
from comcast_mock.exceptions import register_exception_handlers
from comcast_mock.routers.analytics import router as analytics_router
from comcast_mock.routers.categories import router as categories_router
from comcast_mock.routers.health import router as health_router
from comcast_mock.routers.investigations import router as investigations_router
from comcast_mock.routers.tickets import router as tickets_router
from comcast_mock.routers.tools import router as tools_router
from comcast_mock.seed import seed_database

logger = logging.getLogger("comcast_mock")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database.init_engine()

    if database.engine is None:
        logger.warning("Database engine could not be initialized")
        database.db_connected = False
    else:
        try:
            async with database.engine.begin() as conn:
                await conn.run_sync(database.Base.metadata.create_all)
            async with database.session_factory() as session:
                await seed_database(session)
            database.db_connected = True
            logger.info("Database connection established and seed data applied.")
        except Exception:
            logger.exception("Database setup failed; continuing in mock-only mode.")
            database.db_connected = False

    yield

    await database.dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "http://localhost:3000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(tickets_router, prefix=settings.api_prefix)
    app.include_router(categories_router, prefix=settings.api_prefix)
    app.include_router(tools_router, prefix=f"{settings.api_prefix}/tools")
    app.include_router(investigations_router, prefix=settings.api_prefix)
    app.include_router(analytics_router, prefix=settings.api_prefix)

    return app


app = create_app()
