import os

from celery import Celery


celery_app = Celery(
    "backend",
    broker=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")),
    include=["app.tasks.video_generation"],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Automatic publishing only polls VideoAgent and writes one DB record.
    # Keep this queue single-threaded on a single host to avoid concurrent
    # publish attempts when several users create videos at once.
    worker_pool=os.getenv("CELERY_WORKER_POOL", "solo"),
    worker_concurrency=int(os.getenv("CELERY_WORKER_CONCURRENCY", "1")),
    task_default_queue="video_generation",
)
