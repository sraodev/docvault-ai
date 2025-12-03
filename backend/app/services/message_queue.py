"""
Message Queue Service - Celery-based async task processing.

Handles background tasks for million+ user scale:
- Document processing
- Bulk operations
- Email notifications
- Analytics processing

Uses Redis as broker for high-performance message queuing.
"""
from celery import Celery
from ..core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "docvault",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.services.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_routes={
        "app.services.tasks.process_document": {"queue": "processing"},
        "app.services.tasks.bulk_upload": {"queue": "uploads"},
        "app.services.tasks.regenerate_summaries": {"queue": "processing"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
)

