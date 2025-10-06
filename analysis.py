import pandas as pd
from sqlalchemy import text
from database import engine
import numpy as np
from datetime import datetime
from logging_config import logger

# --- Constants ---
BROKER_FEE = 0.01  # 1%
TRANSACTION_TAX = 0.01  # 1%

def get_market_history(region_id: int, days: int = 90) -> pd.DataFrame:
    """Retrieves market history for a given region for the last N days."""
    query = text(f"""
        SELECT type_id, date, average, highest, lowest, volume, order_count
        FROM market_history
        WHERE region_id = :region_id AND date >= NOW() - INTERVAL '{days} days'
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"region_id": region_id})
    df['date'] = pd.to_datetime(df['date'])
    return df

def analyze_market_data(region_id: int):
    """
    Performs a full market analysis for a given region based on 90 days of history.
    """
    logger.info(f"Starting 90-day market analysis for region {region_id}...")
    history_df = get_market_history(region_id, days=90)

    if history_df.empty:
        logger.warning(f"No market history found for region {region_id} in the last 90 days.")
        return pd.DataFrame()

    # Group by item type_id to perform calculations
    analysis_groups = history_df.groupby('type_id')

    # --- Perform all calculations on the 90-day historical data ---

    # Calculate core metrics
    analysis_df = analysis_groups.agg(
        avg_buy_price=('lowest', 'mean'),
        avg_sell_price=('highest', 'mean'),
        avg_daily_volume=('volume', 'mean'),
        volatility_30d=('average', 'std') # Note: volatility is over the 90d period for more data
    ).reset_index()

    # Calculate trend direction
    def get_trend(df):
        df = df.dropna(subset=['average', 'date']).copy()
        if len(df) < 2:
            return 0
        df['date_ordinal'] = df['date'].map(datetime.toordinal)
        try:
            coeffs = np.polyfit(df['date_ordinal'], df['average'], 1)
            slope = coeffs[0]
            if abs(slope) < 0.01: return 0 # Flat trend
            return 1 if slope > 0 else -1
        except (np.linalg.LinAlgError, ValueError):
            return 0

    trends = analysis_groups.apply(get_trend, include_groups=False).to_frame('trend_direction').reset_index()

    # Calculate price-volume correlation
    def get_correlation(df):
        if len(df['average']) < 2 or len(df['volume']) < 2:
            return 0.0
        return df['average'].corr(df['volume'])

    correlations = analysis_groups.apply(get_correlation, include_groups=False).to_frame('price_volume_correlation').reset_index()

    # --- Merge all calculated metrics back together ---
    analysis_df = pd.merge(analysis_df, trends, on='type_id', how='left')
    analysis_df = pd.merge(analysis_df, correlations, on='type_id', how='left')

    # --- Final Profitability Calculations ---
    analysis_df.dropna(subset=['avg_buy_price', 'avg_sell_price', 'avg_daily_volume'], inplace=True)
    if analysis_df.empty:
        return pd.DataFrame()

    analysis_df['profit_per_unit'] = analysis_df['avg_sell_price'] * (1 - TRANSACTION_TAX - BROKER_FEE) - analysis_df['avg_buy_price']
    analysis_df['roi_percent'] = (analysis_df['profit_per_unit'] / analysis_df['avg_buy_price']) * 100

    # Filter out items with no volume or negative profit before calculating score
    profitable_items = analysis_df[(analysis_df['profit_per_unit'] > 0) & (analysis_df['avg_daily_volume'] > 0)].copy()

    if profitable_items.empty:
        logger.info("No profitable items found after 90-day analysis.")
        return pd.DataFrame()

    profitable_items['profit_score'] = profitable_items['roi_percent'] * np.log1p(profitable_items['avg_daily_volume'])
    profitable_items.sort_values(by='profit_score', ascending=False, inplace=True)

    # Replace NaN with None for JSON compatibility
    logger.info(f"Completed analysis for region {region_id}, found {len(profitable_items)} profitable items.")
    return profitable_items.replace({np.nan: None})

if __name__ == '__main__':
    DEFAULT_REGION = 10000001
    logger.info(f"Running 90-day analysis for region {DEFAULT_REGION}...")
    results = analyze_market_data(DEFAULT_REGION)

    if not results.empty:
        logger.info("Top 10 most profitable items based on 90-day history:")
        logger.info(f"\n{results.head(10).to_string()}")
    else:
        logger.info("No profitable items found based on 90-day history.")