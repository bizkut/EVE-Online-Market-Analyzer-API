import asyncio
import bz2
import io
import json
import pandas as pd
import aiohttp
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from database import engine
from esi_utils import get_all_regions, fetch_esi_paginated, ESI_BASE_URL
import logging
import logging_config  # Ensure logging is configured
from celery_app import celery_app

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# --- Configuration ---
MARKET_HISTORY_BASE_URL = "https://data.everef.net/market-history"
TOTALS_JSON_URL = f"{MARKET_HISTORY_BASE_URL}/totals.json"
DATA_RETENTION_DAYS = 180

async def fetch_url(session, url):
    """Asynchronously fetches content from a URL."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching {url}: {e}", exc_info=True)
        return None

def decompress_bz2(data):
    """Decompresses bz2 data and returns a file-like object."""
    return io.StringIO(bz2.decompress(data).decode('utf-8'))

async def process_market_orders():
    """
    Fetches market orders from the ESI API for all regions and efficiently upserts them
    into the database. Also removes orders that are no longer active.
    """
    logger.info("Starting ESI market order processing...")
    processing_start_time = datetime.now(timezone.utc)
    all_orders = []

    regions = await get_all_regions()
    if not regions:
        logger.error("Could not retrieve region list. Aborting market order update.")
        return

    successful_region_ids = []
    async with aiohttp.ClientSession() as session:
        for region in regions:
            region_id = region['region_id']
            logger.info(f"Fetching market orders for region ID: {region_id}...")
            url = f"{ESI_BASE_URL}/markets/{region_id}/orders/"

            orders = await fetch_esi_paginated(session, url)
            if orders is not None: # API call was successful, even if it returned no orders
                successful_region_ids.append(region_id)
                if orders:
                    for order in orders:
                        order['region_id'] = region_id
                    all_orders.extend(orders)
                    logger.info(f"Fetched {len(orders)} orders for region {region_id}.")
                else:
                    logger.info(f"No active orders found for region {region_id}.")
            else:
                logger.warning(f"Failed to fetch orders for region {region_id}.")

    if not all_orders:
        logger.warning("No market orders were fetched from any region. Skipping data upsert.")
    else:
        logger.info(f"Successfully fetched a total of {len(all_orders)} orders from all regions.")
        df = pd.DataFrame(all_orders)

        df['issued'] = pd.to_datetime(df['issued'])
        df['http_last_modified'] = processing_start_time

        final_columns = [
            'order_id', 'type_id', 'location_id', 'volume_total', 'volume_remain',
            'min_volume', 'price', 'is_buy_order', 'duration', 'issued',
            'range', 'system_id', 'region_id', 'http_last_modified'
        ]
        for col in final_columns:
            if col not in df.columns:
                df[col] = None
        df = df[final_columns]

        logger.info("Upserting market orders into the database...")
        with engine.connect() as conn:
            df.to_sql('market_orders_temp', conn, if_exists='replace', index=False, chunksize=10000)

            upsert_sql = text(f"""
            INSERT INTO market_orders ({", ".join(final_columns)})
            SELECT {", ".join(final_columns)} FROM market_orders_temp
            ON CONFLICT (order_id) DO UPDATE SET
                price = EXCLUDED.price,
                volume_remain = EXCLUDED.volume_remain,
                duration = EXCLUDED.duration,
                range = EXCLUDED.range,
                http_last_modified = EXCLUDED.http_last_modified;
            """)
            conn.execute(upsert_sql)
            conn.execute(text("DROP TABLE market_orders_temp;"))
            conn.commit()
            logger.info(f"Upserted {len(df)} market orders.")

    # Clean up stale orders from regions that were successfully processed
    if successful_region_ids:
        with engine.connect() as conn:
            delete_sql = text("DELETE FROM market_orders WHERE region_id = ANY(:region_ids) AND http_last_modified < :timestamp")
            result = conn.execute(delete_sql, {"region_ids": successful_region_ids, "timestamp": processing_start_time})
            conn.commit()
            if result.rowcount > 0:
                logger.info(f"Removed {result.rowcount} stale market orders from processed regions.")

    logger.info("Market order processing finished.")

def get_latest_history_date():
    """Retrieves the most recent date from the market_history table."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT MAX(date) FROM market_history")).scalar_one_or_none()
        # In this case, SQLAlchemy returns a datetime.date object, which is perfect.
        return result

async def process_market_history():
    """
    Downloads and processes market history files from everef.
    On first run, it fetches the last 90 days.
    On subsequent runs, it only fetches data since the last recorded date.
    """
    logger.info("Starting market history processing...")

    latest_db_date = get_latest_history_date()
    # Fetch data only up to yesterday to avoid 404 errors for today's unpublished data
    end_date = datetime.now(timezone.utc).date() - timedelta(days=1)

    if latest_db_date:
        start_date = latest_db_date + timedelta(days=1)
        logger.info(f"Resuming market history download from {start_date.strftime('%Y-%m-%d')}.")
    else:
        start_date = end_date - timedelta(days=DATA_RETENTION_DAYS)
        logger.info(f"No existing history data found. Starting initial download for the past {DATA_RETENTION_DAYS} days.")

    if start_date > end_date:
        logger.info("Market history is already up-to-date.")
        return

    days_to_fetch = (end_date - start_date).days + 1
    date_range = [start_date + timedelta(days=i) for i in range(days_to_fetch)]

    results = []
    async with aiohttp.ClientSession() as session:
        logger.info("Fetching market history totals to see available data...")
        totals_data = await fetch_url(session, TOTALS_JSON_URL)
        if not totals_data:
            logger.warning("Failed to fetch market history totals. Cannot proceed.")
            return

        available_dates = set(json.loads(totals_data).keys())

        tasks = []
        logger.info(f"Checking for available history files from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        for date_obj in date_range:
            date_str = date_obj.strftime('%Y-%m-%d')
            if date_str in available_dates:
                year = date_obj.strftime('%Y')
                url = f"{MARKET_HISTORY_BASE_URL}/{year}/market-history-{date_str}.csv.bz2"
                tasks.append(fetch_url(session, url))

        if not tasks:
            logger.info("No new market history files found in the specified date range.")
            return

        logger.info(f"Found {len(tasks)} new market history files to download.")
        results = await asyncio.gather(*tasks)

    all_history_df = []
    for bz2_data in results:
        if bz2_data:
            try:
                csv_file = decompress_bz2(bz2_data)
                df = pd.read_csv(csv_file)
                all_history_df.append(df)
            except Exception as e:
                logger.error(f"Could not process a history file: {e}", exc_info=True)

    if not all_history_df:
        logger.info("No new market history data to process.")
        return

    history_df = pd.concat(all_history_df, ignore_index=True)

    # Data cleaning and type conversion
    history_df['date'] = pd.to_datetime(history_df['date']).dt.date
    history_df['http_last_modified'] = pd.to_datetime(history_df['http_last_modified'])

    logger.info(f"Loaded {len(history_df)} total new market history records.")

    # Insert into a temporary table first
    with engine.connect() as conn:
        history_df.to_sql('market_history_temp', conn, if_exists='replace', index=False, chunksize=10000)

        # Use INSERT ON CONFLICT to upsert data into the main table
        upsert_sql = text("""
        INSERT INTO market_history (type_id, region_id, date, average, highest, lowest, order_count, volume, http_last_modified)
        SELECT type_id, region_id, date, average, highest, lowest, order_count, volume, http_last_modified
        FROM market_history_temp
        ON CONFLICT (type_id, region_id, date) DO UPDATE SET
            average = EXCLUDED.average,
            highest = EXCLUDED.highest,
            lowest = EXCLUDED.lowest,
            order_count = EXCLUDED.order_count,
            volume = EXCLUDED.volume,
            http_last_modified = EXCLUDED.http_last_modified;
        """)
        conn.execute(upsert_sql)
        conn.execute(text("DROP TABLE market_history_temp;"))
        conn.commit()

    logger.info("Market history table updated successfully.")

def cleanup_old_data():
    """Removes data older than the retention period."""
    logger.info("Cleaning up old market data...")
    ninety_days_ago = datetime.now(timezone.utc).date() - timedelta(days=DATA_RETENTION_DAYS)

    with engine.connect() as conn:
        delete_sql = text("DELETE FROM market_history WHERE date < :date;")
        result = conn.execute(delete_sql, {"date": ninety_days_ago.strftime('%Y-%m-%d')})
        conn.commit()
        logger.info(f"Removed {result.rowcount} old market history records.")

async def run_data_pipeline():
    """
    Main async function to run the data pipeline.
    Fetches market orders and market history concurrently.
    """
    logger.info("Starting concurrent data fetching for market orders and history...")
    # Run market order and history processing concurrently
    await asyncio.gather(
        process_market_orders(),
        process_market_history()
    )
    logger.info("Concurrent data fetching finished.")

    # After fetching, clean up old data
    cleanup_old_data()
    logger.info("Data pipeline run finished.")

@celery_app.task(name="data_pipeline.run_data_pipeline_task")
def run_data_pipeline_task():
    """Celery task to run the full data pipeline."""
    logger.info("Executing run_data_pipeline_task via Celery.")
    asyncio.run(run_data_pipeline())
    logger.info("Celery run_data_pipeline_task finished.")

if __name__ == "__main__":
    # This allows running the script directly for testing or manual runs
    logger.info("Running data pipeline directly.")
    asyncio.run(run_data_pipeline())