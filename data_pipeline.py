import asyncio
import bz2
import io
import json
import pandas as pd
import aiohttp
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from sqlalchemy import text
from database import engine
import logging
import logging_config  # Ensure logging is configured

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# --- Configuration ---
MARKET_ORDERS_URL = "https://data.everef.net/market-orders/market-orders-latest.v3.csv.bz2"
MARKET_HISTORY_BASE_URL = "https://data.everef.net/market-history"
TOTALS_JSON_URL = f"{MARKET_HISTORY_BASE_URL}/totals.json"
DATA_RETENTION_DAYS = 90

# --- Metadata Management ---
def get_metadata(key):
    """Retrieves a value from the pipeline_metadata table."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT value FROM pipeline_metadata WHERE key = :key"), {"key": key}).scalar_one_or_none()
        return result

def set_metadata(key, value):
    """Saves or updates a value in the pipeline_metadata table."""
    with engine.connect() as conn:
        upsert_sql = text("""
            INSERT INTO pipeline_metadata (key, value)
            VALUES (:key, :value)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value;
        """)
        conn.execute(upsert_sql, {"key": key, "value": value})
        conn.commit()
    logger.debug(f"Set metadata for key '{key}'")

# --- Helper Functions ---
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

# --- Data Fetching and Processing ---
async def process_market_orders():
    """Downloads, processes, and updates market orders if new data is available."""
    logger.info("Checking for new market orders...")
    remote_last_modified = None
    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(MARKET_ORDERS_URL) as response:
                response.raise_for_status()
                remote_last_modified_str = response.headers.get('Last-Modified')
                if remote_last_modified_str:
                    remote_last_modified = parsedate_to_datetime(remote_last_modified_str)
                else:
                    logger.warning("Last-Modified header not found. Proceeding with download.")
        except aiohttp.ClientError as e:
            logger.error(f"Could not perform HEAD request on {MARKET_ORDERS_URL}: {e}", exc_info=True)
            logger.warning("Proceeding with download as a fallback.")

        stored_last_modified_str = get_metadata('market_orders_last_modified')
        if stored_last_modified_str and remote_last_modified:
            stored_last_modified = datetime.fromisoformat(stored_last_modified_str)
            if remote_last_modified <= stored_last_modified:
                logger.info("Market orders data is already up-to-date. Skipping download.")
                return

        logger.info("Newer market orders data found or check was inconclusive. Downloading...")
        bz2_data = await fetch_url(session, MARKET_ORDERS_URL)
        if not bz2_data:
            logger.warning("Failed to download market orders.")
            return

    logger.info("Decompressing and parsing market orders...")
    csv_file = decompress_bz2(bz2_data)
    df = pd.read_csv(csv_file)

    df['issued'] = pd.to_datetime(df['issued'])
    df['http_last_modified'] = pd.to_datetime(df['http_last_modified'])
    logger.info(f"Loaded {len(df)} market orders.")

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE market_orders;"))
        df.to_sql('market_orders', conn, if_exists='append', index=False, chunksize=10000)
        conn.commit()
    logger.info("Market orders table updated successfully.")

    if remote_last_modified:
        set_metadata('market_orders_last_modified', remote_last_modified.isoformat())
        logger.info(f"Updated last modified timestamp for market orders to {remote_last_modified.isoformat()}")

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
    today = datetime.now(timezone.utc).date()

    if latest_db_date:
        start_date = latest_db_date + timedelta(days=1)
        logger.info(f"Resuming market history download from {start_date.strftime('%Y-%m-%d')}.")
    else:
        start_date = today - timedelta(days=DATA_RETENTION_DAYS)
        logger.info(f"No existing history data found. Starting initial download for the past {DATA_RETENTION_DAYS} days.")

    if start_date > today:
        logger.info("Market history is already up-to-date.")
        return

    days_to_fetch = (today - start_date).days + 1
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
        logger.info(f"Checking for available history files from {start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}...")
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

async def main():
    """Main function to run the data pipeline."""
    await process_market_orders()
    await process_market_history()
    cleanup_old_data()
    logger.info("Data pipeline run finished.")

if __name__ == "__main__":
    asyncio.run(main())