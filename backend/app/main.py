from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/")
def root() -> dict:
    return {"name": settings.APP_NAME, "docs": "/docs", "api": settings.API_PREFIX}
