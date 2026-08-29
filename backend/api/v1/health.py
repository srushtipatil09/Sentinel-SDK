from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.session import get_async_session
from backend.services.health_service import health_service

router = APIRouter(tags=["System Health & Liveness"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_async_session)):
    """Full system component health check (Database, Redis, Google Pub/Sub, ChromaDB, Gemini)."""
    return await health_service.check_health(session)


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "live"}


@router.post("/health/init-db")
async def init_database():
    """Explicitly provisions all missing PostgreSQL tables and returns database schema inventory."""
    import backend.models
    from sqlalchemy import inspect
    from backend.database.base import Base
    from backend.database.session import async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    def get_tables(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_table_names()

    async with async_engine.connect() as conn:
        tables = await conn.run_sync(get_tables)

    return {
        "status": "success",
        "message": "PostgreSQL relational tables verified and initialized.",
        "tables_count": len(tables),
        "tables": tables
    }


@router.get("/health/db-status")
async def get_db_status():
    """Returns the list of all existing tables in the PostgreSQL database."""
    from sqlalchemy import inspect
    from backend.database.session import async_engine

    def get_tables(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.get_table_names()

    async with async_engine.connect() as conn:
        tables = await conn.run_sync(get_tables)

    return {
        "status": "connected",
        "tables_count": len(tables),
        "tables": sorted(tables)
    }
