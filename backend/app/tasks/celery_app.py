from celery import Celery

from app.config import settings

celery_app = Celery(
    "aira",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.ai_tasks"],
)

celery_app.conf.task_default_queue = "aira"
celery_app.conf.timezone = "UTC"
celery_app.conf.task_acks_late = True
celery_app.conf.broker_connection_retry_on_startup = True
