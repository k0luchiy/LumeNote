from celery import Celery
from tele_notebook.core.config import settings

celery_app = Celery(
    "tele_notebook_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tele_notebook.tasks.tasks"]
)

celery_app.conf.update(
    task_track_started=True,
)