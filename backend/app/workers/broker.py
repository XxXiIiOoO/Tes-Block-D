"""TaskIQ broker configuration for async background task processing."""

from taskiq_redis import ListQueueBroker

from app.core.config import settings


broker = ListQueueBroker(
    url=settings.redis_url,
    queue_name=settings.taskiq_queue_name,
)
