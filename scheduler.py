from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_pipeline import main as run_data_pipeline
import asyncio

scheduler = AsyncIOScheduler()

def start_scheduler():
    """
    Starts the APScheduler and adds the hourly data refresh job.
    """
    # Schedule the data pipeline to run every hour
    scheduler.add_job(run_data_pipeline, 'interval', hours=1, id='hourly_refresh')

    # Start the scheduler
    scheduler.start()
    print("Scheduler started. Data will be refreshed hourly.")

def stop_scheduler():
    """
    Stops the APScheduler.
    """
    scheduler.shutdown()
    print("Scheduler stopped.")