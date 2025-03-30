from celery import Celery
from ..config import settings

# Initialize Celery
# The first argument is the name of the current module, important for Celery's auto-discovery.
# The broker and backend URLs are taken from the application settings.
celery_app = Celery(
    "worker",  # Should match the directory name or a relevant name
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],  # List of modules where tasks are defined
)

# Optional configuration settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Ignore other content
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Add other Celery settings if needed
    # Example: task_track_started=True
)

# Optional: If you need Celery to access Django settings or similar framework setups
# celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
# celery_app.autodiscover_tasks() # Use this if tasks are spread across many apps in a larger framework

if __name__ == "__main__":
    # This allows running the worker directly using: python -m app.worker.celery_app worker --loglevel=info
    # However, the standard way is: celery -A app.worker.celery_app worker --loglevel=info
    # Or using the project-level celery command if configured.
    celery_app.start()
