import pandas as pd
from sqlalchemy import text
from database import engine
import numpy as np
from datetime import datetime
from logging_config import logger

# --- Constants ---
# NOTE: These are assumed percentages. The prompt is ambiguous.
BROKER_FEE = 0.01  # 1%
TRANSACTION_TAX = 0.01  # 1%

def get_market_orders(region_id: int) -> pd.DataFrame:
    """Retrieves all market orders for a given region."""
    query = text("SELECT type_id, price, is_buy_order, volume_remain FROM market_orders WHERE region_id = :region_id")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"region_id": region_id})
    return df

def get_market_history(region_id: int, days: int = 30) -> pd.DataFrame:
    """Retrieves market history for a given region for the last N days."""
    query = text(f"""
        SELECT type_id, date, average as price, volume
        FROM market_history
        WHERE region_id = :region_id AND date >= NOW() - INTERVAL '{days} days'
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"region_id": region_id})
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_price_metrics(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates average buy and sell prices based on market orders.
    """
    buy_orders = orders_df[orders_df['is_buy_order'] == True].copy()
    sell_orders = orders_df[orders_df['is_buy_order'] == False].copy()

    def get_avg_top_10_percent_price(df):
        if df.empty or len(df) < 2:
            return df['price'].mean() if not df.empty else np.nan
        price_90th_percentile = df['price'].quantile(0.9)
        top_10_percent_orders = df[df['price'] >= price_90th_percentile]
        return top_10_percent_orders['price'].mean()

    avg_buy_prices = buy_orders.groupby('type_id').apply(get_avg_top_10_percent_price, include_groups=False).to_frame('avg_buy_price').reset_index()

    def get_avg_bottom_10_percent_price(df):
        if df.empty or len(df) < 2:
            return df['price'].mean() if not df.empty else np.nan
        price_10th_percentile = df['price'].quantile(0.1)
        bottom_10_percent_orders = df[df['price'] <= price_10th_percentile]
        return bottom_10_percent_orders['price'].mean()

    avg_sell_prices = sell_orders.groupby('type_id').apply(get_avg_bottom_10_percent_price, include_groups=False).to_frame('avg_sell_price').reset_index()

    price_metrics = pd.merge(avg_buy_prices, avg_sell_prices, on='type_id', how='outer')
    return price_metrics

def calculate_history_metrics(history_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates metrics based on historical data."""
    history_metrics = history_df.groupby('type_id').agg(
        avg_daily_volume=('volume', 'mean'),
        volatility_30d=('price', 'std')
    ).reset_index()

    # Calculate trend direction
    def get_trend(df):
        df = df.dropna(subset=['price', 'date']).copy()
        if len(df) < 2:
            return 0
        df['date_ordinal'] = df['date'].map(datetime.toordinal)
        try:
            coeffs = np.polyfit(df['date_ordinal'], df['price'], 1)
            slope = coeffs[0]
            if slope > 0.1: return 1
            if slope < -0.1: return -1
            return 0
        except np.linalg.LinAlgError:
            return 0

    trends_df = history_df.groupby('type_id').apply(get_trend, include_groups=False).reset_index()
    trends = trends_df.rename(columns={trends_df.columns[1]: 'trend_direction'})

    # Calculate price-volume correlation
    def get_correlation(df):
        if len(df['price']) < 2 or len(df['volume']) < 2:
            return 0.0
        return df['price'].corr(df['volume'])

    correlations = history_df.groupby('type_id').apply(get_correlation, include_groups=False).to_frame('price_volume_correlation').reset_index()

    history_metrics = pd.merge(history_metrics, trends, on='type_id', how='left')
    history_metrics = pd.merge(history_metrics, correlations, on='type_id', how='left')

    return history_metrics

def analyze_market_data(region_id: int):
    """
    Performs a full market analysis for a given region.
    """
    orders_df = get_market_orders(region_id)
    history_df_30d = get_market_history(region_id, days=30)

    price_metrics = calculate_price_metrics(orders_df)
    history_metrics = calculate_history_metrics(history_df_30d)

    analysis_df = pd.merge(price_metrics, history_metrics, on='type_id', how='inner')
    analysis_df.dropna(subset=['avg_buy_price', 'avg_sell_price', 'avg_daily_volume'], inplace=True)

    if analysis_df.empty:
        return pd.DataFrame()

    analysis_df['profit_per_unit'] = analysis_df['avg_sell_price'] * (1 - TRANSACTION_TAX - BROKER_FEE) - analysis_df['avg_buy_price']
    analysis_df['roi_percent'] = (analysis_df['profit_per_unit'] / analysis_df['avg_buy_price']) * 100
    analysis_df['profit_score'] = analysis_df['roi_percent'] * np.log1p(analysis_df['avg_daily_volume'])

    profitable_items = analysis_df[analysis_df['profit_per_unit'] > 0].copy()
    profitable_items.sort_values(by='profit_score', ascending=False, inplace=True)

    # Replace NaN with None for JSON compatibility
    return profitable_items.replace({np.nan: None})

if __name__ == '__main__':
    DEFAULT_REGION = 10000001
    logger.info(f"Running analysis for region {DEFAULT_REGION}...")
    results = analyze_market_data(DEFAULT_REGION)

    if not results.empty:
        logger.info("Top 10 most profitable items:")
        logger.info(f"\n{results.head(10).to_string()}")
    else:
        logger.info("No profitable items found.")