from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1 import api_router
from app.api.v1.ws import router as ws_router
from app.config import settings
from app.core.rate_limit import limiter, rate_limit_exception_handler
from app.database import Base, engine, session_scope
from app.core.security import hash_password
from app.models import Officer, Station, User, UserRole
from app.realtime import broadcaster
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)


def _run_lightweight_migrations() -> None:
    """Apply additive, idempotent schema tweaks on existing (non-SQLite) DBs.

    ``Base.metadata.create_all`` never ALTERs an already-existing table, so
    columns/constraints introduced after a table was first created must be
    applied by hand. Each statement runs in its own transaction and failures
    (e.g. the change is already applied) are ignored.
    """
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    statements = [
        # Allow phone-only citizen accounts: email may now be NULL.
        "ALTER TABLE users MODIFY email VARCHAR(190) NULL",
        # Phone becomes a unique login identifier.
        "ALTER TABLE users ADD UNIQUE INDEX uq_users_phone (phone)",
        # Link duplicate reports to the original incident they duplicate.
        "ALTER TABLE spam_reports ADD COLUMN duplicate_of_incident_id INT NULL",
        "ALTER TABLE spam_reports ADD INDEX ix_spam_reports_duplicate_of_incident_id (duplicate_of_incident_id)",
    ]
    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Migration applied: %s", stmt)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Migration skipped (%s): %s", stmt, str(exc)[:120])


def _auto_seed() -> None:
    """Create default admin / officer / citizen accounts and stations if missing."""
    with session_scope() as db:
        # Stations
        if db.query(Station).count() == 0:
            db.add_all([
                Station(name="Kigali Central Police Station", district="Nyarugenge",
                        sector="Nyarugenge", latitude=-1.9536, longitude=30.0606,
                        contact_phone="+250788000001"),
                Station(name="Remera Police Station", district="Gasabo", sector="Remera",
                        latitude=-1.9501, longitude=30.1100, contact_phone="+250788000002"),
                Station(name="Kicukiro Police Station", district="Kicukiro", sector="Niboyi",
                        latitude=-1.9806, longitude=30.1100, contact_phone="+250788000003"),
            ])
            db.flush()

        # Admin
        if not db.query(User).filter(User.email == "admin@rnp.gov.rw").first():
            db.add(User(
                full_name="System Administrator",
                email="admin@rnp.gov.rw",
                phone="+250788111111",
                password_hash=hash_password("Admin@123"),
                role=UserRole.admin,
                is_verified=True,
            ))
            db.flush()

        # Officer
        if not db.query(User).filter(User.email == "officer1@rnp.gov.rw").first():
            user = User(
                full_name="Officer John Mugisha",
                email="officer1@rnp.gov.rw",
                phone="+250788222222",
                password_hash=hash_password("Officer@1"),
                role=UserRole.officer,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            station = db.query(Station).first()
            db.add(Officer(
                user_id=user.id,
                badge_number="RNP-0001",
                station_id=station.id if station else None,
                rank="Inspector",
                department="Patrol",
            ))

        # Citizen
        if not db.query(User).filter(User.email == "citizen@example.com").first():
            db.add(User(
                full_name="Jean Citizen",
                email="citizen@example.com",
                phone="+250788333333",
                password_hash=hash_password("Citizen@1"),
                role=UserRole.citizen,
                is_verified=True,
            ))
        logger.info("Auto-seed complete.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    try:
        _run_lightweight_migrations()
    except Exception:
        logger.exception("Lightweight migrations failed (continuing)")
    if settings.AUTO_SEED:
        try:
            _auto_seed()
        except Exception:
            logger.exception("Auto-seed failed (continuing)")
    # Bind the running event loop so background threads (Celery, sync request
    # handlers calling broadcaster.publish) can dispatch WebSocket events.
    broadcaster.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI Incident Reporting Application — Rwanda National Police",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static uploads
upload_path = Path(settings.UPLOAD_DIR).resolve()
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(ws_router, prefix="/ws", tags=["realtime"])


_STARTED_AT = datetime.now(timezone.utc)


def _check_database() -> dict:
    started = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - started) * 1000, 1)
        return {"status": "ok", "latency_ms": latency}
    except Exception as exc:  # pragma: no cover - depends on infra
        return {"status": "down", "error": str(exc)[:200]}


def _check_redis() -> dict:
    started = time.perf_counter()
    try:
        import redis  # type: ignore

        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        ok = client.ping()
        latency = round((time.perf_counter() - started) * 1000, 1)
        return {"status": "ok" if ok else "degraded", "latency_ms": latency}
    except ModuleNotFoundError:
        return {"status": "unknown", "error": "redis client not installed"}
    except Exception as exc:
        return {"status": "down", "error": str(exc)[:200]}


def _check_celery() -> dict:
    try:
        from app.tasks.celery_app import celery_app  # type: ignore

        started = time.perf_counter()
        # inspect.ping returns {worker_name: {'ok': 'pong'}} or None on timeout
        replies = celery_app.control.inspect(timeout=1.0).ping()
        latency = round((time.perf_counter() - started) * 1000, 1)
        if not replies:
            return {"status": "down", "workers": 0, "error": "no workers responded"}
        return {"status": "ok", "workers": len(replies), "latency_ms": latency}
    except ModuleNotFoundError:
        return {"status": "unknown", "error": "celery not installed"}
    except Exception as exc:
        return {"status": "down", "error": str(exc)[:200]}


def _check_websocket() -> dict:
    try:
        connections = sum(len(s) for s in broadcaster._connections.values())  # noqa: SLF001
        topics = len(broadcaster._connections)  # noqa: SLF001
        return {"status": "ok", "connections": connections, "topics": topics}
    except Exception as exc:
        return {"status": "down", "error": str(exc)[:200]}


def _check_storage() -> dict:
    try:
        path = Path(settings.UPLOAD_DIR)
        if not path.exists():
            return {"status": "down", "error": "upload directory missing"}
        # Light count of upload entries
        files = sum(1 for _ in path.glob("**/*") if _.is_file())
        return {"status": "ok", "files": files}
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)[:200]}


@app.get("/health")
def health(detailed: bool = False) -> dict:
    """Lightweight by default; pass ?detailed=true for component status."""
    if not detailed:
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

    components = {
        "database": _check_database(),
        "redis": _check_redis(),
        "celery": _check_celery(),
        "websocket": _check_websocket(),
        "storage": _check_storage(),
    }
    statuses = {c["status"] for c in components.values()}
    if "down" in statuses:
        overall = "degraded"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "ok"

    uptime = (datetime.now(timezone.utc) - _STARTED_AT).total_seconds()
    return {
        "status": overall,
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "1.0.0",
        "uptime_seconds": int(uptime),
        "started_at": _STARTED_AT.isoformat(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }


@app.get("/")
def root() -> dict:
    return {"name": settings.APP_NAME, "docs": "/docs", "api": settings.API_PREFIX}
