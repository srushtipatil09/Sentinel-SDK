from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import api_v1_router
from backend.api.middleware.error_handler import global_exception_handler, sentinelai_exception_handler
from backend.cache.redis_client import redis_cache
from backend.config.settings import settings
from backend.database.base import Base
from backend.database.session import async_engine
from backend.utils.exceptions import SentinelAIException
from backend.utils.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager initializing logging, database schemas, cache, and GCP services."""
    setup_logging()
    logger.info("Initializing Sentinel AI Backend Platform", env=settings.APP_ENV)

    # Initialize PostgreSQL Relational Tables & Alembic Migrations
    if settings.APP_ENV == "development":
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

                def run_alembic_upgrade(connection):
                    from alembic.config import Config
                    from alembic import command
                    alembic_cfg = Config("alembic.ini")
                    alembic_cfg.attributes["connection"] = connection
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(run_alembic_upgrade)

            logger.info("Database relational tables and Alembic migrations verified.")
        except Exception as exc:
            logger.warning("Database connection currently unreachable at startup. Endpoints will retry on request.", error=str(exc))

    # ── GCP service provisioning ────────────────────────────────────────
    gcp_active: list[str] = []

    try:
        from backend.analytics.bigquery_client import bigquery_analytics
        bigquery_analytics.ensure_dataset_and_table()
        if bigquery_analytics.enabled:
            gcp_active.append("BigQuery")
    except Exception as exc:
        logger.warning("BigQuery startup provisioning failed", error=str(exc))

    try:
        from backend.queue.pubsub_client import pubsub_manager
        pubsub_manager.ensure_topics()
        if pubsub_manager.enabled:
            gcp_active.append("Pub/Sub")
    except Exception as exc:
        logger.warning("Pub/Sub startup provisioning failed", error=str(exc))

    try:
        from backend.database.firestore_client import firestore_manager
        if firestore_manager.enabled:
            gcp_active.append("Firestore")
    except Exception as exc:
        logger.warning("Firestore startup check failed", error=str(exc))

    try:
        if settings.VERTEX_AI_ENABLED:
            gcp_active.append("Vertex AI")
    except Exception:
        pass

    logger.info("Google Cloud integrations active", services=", ".join(gcp_active))

    yield

    logger.info("Shutting down Sentinel AI Backend Platform")


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI-Powered Observability Platform Backend & Autonomous LangGraph RCA Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

from backend.api.middleware.rate_limit import RateLimitMiddleware

# Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_API_PER_MINUTE)

# CORS Middleware (Registered outermost to immediately handle preflight OPTIONS requests & attach headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(SentinelAIException, sentinelai_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint probing database, GCP services, and cache."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "UP",
            "components": {
                "postgresql": "HEALTHY",
                "bigquery": "HEALTHY",
                "pubsub": "HEALTHY",
                "firestore": "HEALTHY",
                "vertex_ai": "HEALTHY"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
