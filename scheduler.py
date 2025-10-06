from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_pipeline import main as run_data_pipeline
from train_models import main as run_model_training
import asyncio
import logging
import logging_config  # Ensure logging is configured

# --- Setup Logger ---
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    """
    Starts the APScheduler and adds jobs for data refresh and model training.
    """
    # Schedule the data pipeline to run every hour
    scheduler.add_job(run_data_pipeline, 'interval', hours=1, id='hourly_data_refresh')

    # Schedule the model training to run once a day
    scheduler.add_job(run_model_training, 'interval', days=1, id='daily_model_training')

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started. Data refreshed hourly, models trained daily.")

def stop_scheduler():
    """
    Stops the APScheduler.
    """
    scheduler.shutdown()
    logger.info("Scheduler stopped.")