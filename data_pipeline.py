import asyncio
import bz2
import io
import json
import pandas as pd
import aiohttp
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from database import engine
from logging_config import logger

# --- Configuration ---
MARKET_ORDERS_URL = "https://data.everef.net/market-orders/market-orders-latest.v3.csv.bz2"
MARKET_HISTORY_BASE_URL = "https://data.everef.net/market-history"
TOTALS_JSON_URL = f"{MARKET_HISTORY_BASE_URL}/totals.json"
DATA_RETENTION_DAYS = 90

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
    """Downloads, processes, and updates market orders."""
    logger.info("Fetching latest market orders...")
    async with aiohttp.ClientSession() as session:
        bz2_data = await fetch_url(session, MARKET_ORDERS_URL)
        if not bz2_data:
            logger.warning("Failed to download market orders.")
            return

    logger.info("Decompressing and parsing market orders...")
    csv_file = decompress_bz2(bz2_data)
    df = pd.read_csv(csv_file)

    # Data cleaning and type conversion
    df['issued'] = pd.to_datetime(df['issued'])
    df['http_last_modified'] = pd.to_datetime(df['http_last_modified'])

    logger.info(f"Loaded {len(df)} market orders.")

    # Update database (truncate and load)
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE market_orders;"))
        df.to_sql('market_orders', conn, if_exists='append', index=False, chunksize=10000)
        conn.commit()
    logger.info("Market orders table updated successfully.")

async def process_market_history():
    """Downloads, processes, and updates market history for the last 90 days."""
    logger.info("Fetching market history totals...")
    async with aiohttp.ClientSession() as session:
        totals_data = await fetch_url(session, TOTALS_JSON_URL)
        if not totals_data:
            logger.warning("Failed to fetch market history totals.")
            return

    available_dates_str = json.loads(totals_data).keys()

    tasks = []
    today = datetime.now(timezone.utc).date()
    date_range = [today - timedelta(days=i) for i in range(DATA_RETENTION_DAYS)]

    logger.info(f"Checking for history data for the past {DATA_RETENTION_DAYS} days...")
    async with aiohttp.ClientSession() as session:
        for date_obj in date_range:
            date_str = date_obj.strftime('%Y-%m-%d')
            if date_str in available_dates_str:
                year = date_obj.strftime('%Y')
                url = f"{MARKET_HISTORY_BASE_URL}/{year}/market-history-{date_str}.csv.bz2"
                tasks.append(fetch_url(session, url))

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
        logger.info("No new market history data found.")
        return

    history_df = pd.concat(all_history_df, ignore_index=True)

    # Data cleaning and type conversion
    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df['http_last_modified'] = pd.to_datetime(history_df['http_last_modified'])

    logger.info(f"Loaded {len(history_df)} total market history records.")

    # Insert into a temporary table first
    with engine.connect() as conn:
        history_df.to_sql('market_history_temp', conn, if_exists='replace', index=False)

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