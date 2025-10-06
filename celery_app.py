import os
from celery import Celery
from celery.schedules import crontab

# --- Celery Configuration ---
# Set the default Django settings module for the 'celery' program.
# Note: This project does not use Django, but Celery's architecture uses a similar setup.
# We will configure the broker and backend directly.
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Initialize the Celery app
# The first argument is the name of the current module, which is used for generating task names.
# The `broker` and `backend` arguments specify the message broker and result backend to use.
celery_app = Celery(
    "tasks",
    broker=redis_url,
    backend=redis_url,
    include=[
        "data_pipeline",
        "analysis",
        "train_models"
    ]
)

# Optional configuration, can be moved to a separate config file
celery_app.conf.update(
    task_track_started=True,
    timezone='UTC',
    enable_utc=True,
)

# --- Celery Beat Periodic Task Schedule ---
# This section defines the periodic tasks that Celery Beat will run.
# It replaces the functionality previously handled by APScheduler.
celery_app.conf.beat_schedule = {
    # Executes the data pipeline every 30 minutes
    'periodic_data_refresh': {
        'task': 'data_pipeline.run_data_pipeline_task',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    # Executes market analysis every hour
    'hourly_market_analysis': {
        'task': 'analysis.run_analysis_task',
        'schedule': crontab(hour='*'),  # Every hour
    },
    # Executes model training once a day at midnight
    'daily_model_training': {
        'task': 'train_models.run_model_training_task',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}

if __name__ == '__main__':
    celery_app.start()