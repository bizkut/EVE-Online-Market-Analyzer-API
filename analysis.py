import pandas as pd
from sqlalchemy import text
from database import engine
import numpy as np
from datetime import datetime
import logging
import logging_config  # Ensure logging is configured

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
BROKER_FEE = 0.01  # 1%
TRANSACTION_TAX = 0.01  # 1%

def get_market_orders(region_id: int) -> pd.DataFrame:
    """Retrieves all market orders for a given region."""
    query = text("SELECT type_id, price, is_buy_order FROM market_orders WHERE region_id = :region_id")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"region_id": region_id})
    return df

def get_market_history(region_id: int, days: int) -> pd.DataFrame:
    """Retrieves market history for a given region for the last N days."""
    query = text(f"""
        SELECT type_id, date, average, volume
        FROM market_history
        WHERE region_id = :region_id AND date >= NOW() - INTERVAL '{days} days'
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"region_id": region_id})
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_price_metrics(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates current profitability metrics from live market orders.
    - avg_buy_price: Mean of the lowest 10% of buy orders.
    - avg_sell_price: Mean of the highest 10% of sell orders.
    """
    buy_orders = orders_df[orders_df['is_buy_order'] == True].copy()
    sell_orders = orders_df[orders_df['is_buy_order'] == False].copy()

    def get_avg_bottom_10_percent_price(df):
        if df.empty: return np.nan
        if len(df) < 2: return df['price'].mean()
        price_10th_percentile = df['price'].quantile(0.1)
        return df[df['price'] <= price_10th_percentile]['price'].mean()

    def get_avg_top_10_percent_price(df):
        if df.empty: return np.nan
        if len(df) < 2: return df['price'].mean()
        price_90th_percentile = df['price'].quantile(0.9)
        return df[df['price'] >= price_90th_percentile]['price'].mean()

    avg_buy_prices = buy_orders.groupby('type_id').apply(get_avg_bottom_10_percent_price, include_groups=False).to_frame('avg_buy_price').reset_index()
    avg_sell_prices = sell_orders.groupby('type_id').apply(get_avg_top_10_percent_price, include_groups=False).to_frame('avg_sell_price').reset_index()

    price_metrics = pd.merge(avg_buy_prices, avg_sell_prices, on='type_id', how='outer')
    return price_metrics

def calculate_history_metrics(history_df_30d: pd.DataFrame, history_df_90d: pd.DataFrame) -> pd.DataFrame:
    """Calculates metrics based on historical data."""
    # 30-day metrics
    history_metrics_30d = history_df_30d.groupby('type_id').agg(
        avg_daily_volume=('volume', 'mean'),
        volatility_30d=('average', 'std')
    ).reset_index()

    # 90-day metrics
    history_groups_90d = history_df_90d.groupby('type_id')

    def get_trend(df):
        df = df.dropna(subset=['average', 'date']).copy()
        if len(df) < 2: return 0
        df['date_ordinal'] = df['date'].map(datetime.toordinal)
        try:
            coeffs = np.polyfit(df['date_ordinal'], df['average'], 1)
            slope = coeffs[0]
            if abs(slope) < 0.01: return 0
            return 1 if slope > 0 else -1
        except (np.linalg.LinAlgError, ValueError):
            return 0

    trends = history_groups_90d.apply(get_trend, include_groups=False).to_frame('trend_direction').reset_index()

    def get_correlation(df):
        if len(df['average']) < 2 or len(df['volume']) < 2: return 0.0
        return df['average'].corr(df['volume'])

    correlations = history_groups_90d.apply(get_correlation, include_groups=False).to_frame('price_volume_correlation').reset_index()

    # Merge all historical metrics
    history_metrics = pd.merge(history_metrics_30d, trends, on='type_id', how='left')
    history_metrics = pd.merge(history_metrics, correlations, on='type_id', how='left')
    return history_metrics

def analyze_market_data(region_id: int):
    """
    Performs a hybrid market analysis for a given region.
    - Current profitability from live orders.
    - Historical context from 90-day history.
    """
    logger.info(f"Starting hybrid market analysis for region {region_id}...")

    # Fetch both live and historical data
    orders_df = get_market_orders(region_id)
    history_df_30d = get_market_history(region_id, days=30)
    history_df_90d = get_market_history(region_id, days=90)

    if history_df_30d.empty or history_df_90d.empty or orders_df.empty:
        logger.warning(f"Insufficient data to perform analysis for region {region_id}.")
        return pd.DataFrame()

    price_metrics = calculate_price_metrics(orders_df)
    history_metrics = calculate_history_metrics(history_df_30d, history_df_90d)

    # Merge live and historical data
    analysis_df = pd.merge(price_metrics, history_metrics, on='type_id', how='inner')

    # Final Profitability Calculations
    analysis_df.dropna(subset=['avg_buy_price', 'avg_sell_price', 'avg_daily_volume'], inplace=True)
    if analysis_df.empty:
        return pd.DataFrame()

    analysis_df['profit_per_unit'] = analysis_df['avg_sell_price'] * (1 - TRANSACTION_TAX - BROKER_FEE) - analysis_df['avg_buy_price']
    analysis_df['roi_percent'] = (analysis_df['profit_per_unit'] / analysis_df['avg_buy_price']) * 100

    profitable_items = analysis_df[(analysis_df['profit_per_unit'] > 0) & (analysis_df['avg_daily_volume'] > 0)].copy()

    if profitable_items.empty:
        logger.info("No profitable items found after hybrid analysis.")
        return pd.DataFrame()

    profitable_items['profit_score'] = profitable_items['roi_percent'] * np.log1p(profitable_items['avg_daily_volume'])
    profitable_items.sort_values(by='profit_score', ascending=False, inplace=True)

    logger.info(f"Completed hybrid analysis for region {region_id}, found {len(profitable_items)} profitable items.")
    return profitable_items.replace({np.nan: None})

if __name__ == '__main__':
    DEFAULT_REGION = 10000001
    logger.info(f"Running hybrid analysis for region {DEFAULT_REGION}...")
    results = analyze_market_data(DEFAULT_REGION)

    if not results.empty:
        logger.info("Top 10 most profitable items based on hybrid analysis:")
        logger.info(f"\n{results.head(10).to_string()}")
    else:
        logger.info("No profitable items found based on hybrid analysis.")