from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_pipeline import main as run_data_pipeline
import asyncio
import logging
import logging_config  # Ensure logging is configured

# --- Setup Logger ---
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    """
    Starts the APScheduler and adds the hourly data refresh job.
    """
    # Schedule the data pipeline to run every hour
    scheduler.add_job(run_data_pipeline, 'interval', hours=1, id='hourly_refresh')

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started. Data will be refreshed hourly.")

def stop_scheduler():
    """
    Stops the APScheduler.
    """
    scheduler.shutdown()
    logger.info("Scheduler stopped.")