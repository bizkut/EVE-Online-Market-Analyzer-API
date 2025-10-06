import asyncio
from sqlalchemy import text
from database import engine
from data_pipeline import main as run_data_pipeline
from logging_config import logger

def is_database_empty():
    """
    Checks if the market_orders table is empty.
    Returns True if the table is empty, False otherwise.
    """
    with engine.connect() as connection:
        result = connection.execute(text("SELECT COUNT(*) FROM market_orders;")).scalar()
        return result == 0

async def main():
    """
    Main function to run the initial data loader.
    """
    logger.info("Checking if initial data load is needed...")
    if is_database_empty():
        logger.info("Database is empty. Starting initial data pipeline...")
        await run_data_pipeline()
        logger.info("Initial data pipeline finished.")
    else:
        logger.info("Database already contains data. Skipping initial data load.")

if __name__ == "__main__":
    asyncio.run(main())