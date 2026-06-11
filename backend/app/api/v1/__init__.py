from fastapi import APIRouter

from app.api.v1 import ai, analytics, auth, incidents, notifications, officers, reports, spam, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(officers.router, prefix="/officers", tags=["officers"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(spam.router, prefix="/spam", tags=["spam"])
