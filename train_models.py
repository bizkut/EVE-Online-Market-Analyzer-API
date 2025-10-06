import pandas as pd
from sqlalchemy import text
from database import engine
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
import logging
import logging_config
import joblib
import os
from pathlib import Path
from celery_app import celery_app

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
MIN_DAYS_FOR_TRAINING = 30
MODEL_DIR = Path("models")

def get_distinct_items_for_training(min_days: int) -> list:
    """
    Finds all distinct type_id/region_id pairs that have enough data to be trained.
    """
    logger.info(f"Searching for items with at least {min_days} days of history...")
    query = text(f"""
        SELECT type_id, region_id
        FROM market_history
        GROUP BY type_id, region_id
        HAVING COUNT(date) >= :min_days
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"min_days": min_days}).fetchall()

    items = [(row[0], row[1]) for row in result]
    logger.info(f"Found {len(items)} items eligible for model training.")
    return items

def get_item_history_for_training(type_id: int, region_id: int) -> pd.DataFrame:
    """
    Retrieves all available market history for a specific item in a region.
    """
    query = text("""
        SELECT date, average as price, volume
        FROM market_history
        WHERE region_id = :region_id AND type_id = :type_id
        ORDER BY date ASC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"region_id": region_id, "type_id": type_id})

    if df.empty:
        return pd.DataFrame()

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def _calculate_trend(series: pd.Series) -> int:
    """Calculates the trend direction for a given history Series."""
    df = series.to_frame(name='price').copy()
    df = df.dropna(subset=['price'])
    if len(df) < 2:
        return 0
    df['date_ordinal'] = df.index.map(datetime.toordinal)
    try:
        coeffs = np.polyfit(df['date_ordinal'], df['price'], 1)
        slope = coeffs[0]
        if abs(slope) < 0.01: return 0
        return 1 if slope > 0 else -1
    except (np.linalg.LinAlgError, ValueError):
        return 0

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Creates features for the prediction model."""
    if df.empty or len(df) < MIN_DAYS_FOR_TRAINING:
        return pd.DataFrame()

    df['avg_price_7d'] = df['price'].rolling(window=7).mean()
    df['avg_price_30d'] = df['price'].rolling(window=30).mean()
    df['volume_7d'] = df['volume'].rolling(window=7).mean()
    df['volatility_7d'] = df['price'].rolling(window=7).std()
    df['trend_direction'] = df['price'].rolling(window=30, min_periods=10).apply(_calculate_trend, raw=False)

    df['target_price'] = df['price'].shift(-1)
    df.dropna(inplace=True)
    return df

def train_and_save_model(type_id: int, region_id: int):
    """
    Trains a model for a specific item and saves it to a file.
    """
    history_df = get_item_history_for_training(type_id, region_id)
    if history_df.empty:
        logger.debug(f"[{type_id}@{region_id}] No history found, skipping.")
        return

    features_df = create_features(history_df)
    if features_df.empty:
        logger.debug(f"[{type_id}@{region_id}] Not enough data to create features, skipping.")
        return

    features = ['avg_price_7d', 'avg_price_30d', 'volume_7d', 'volatility_7d', 'trend_direction']
    X = features_df[features]
    y = features_df['target_price']

    model = LinearRegression()
    model.fit(X, y)

    # Ensure the directory exists
    MODEL_DIR.mkdir(exist_ok=True)

    # Save the model
    model_filename = f"{region_id}_{type_id}.joblib"
    model_path = MODEL_DIR / model_filename
    joblib.dump(model, model_path)
    logger.info(f"Successfully trained and saved model for {type_id} in {region_id} to {model_path}")

def run_model_training():
    """Main function to run the training process."""
    logger.info("Starting model training process...")
    items_to_train = get_distinct_items_for_training(min_days=MIN_DAYS_FOR_TRAINING)

    for type_id, region_id in items_to_train:
        try:
            train_and_save_model(type_id, region_id)
        except Exception as e:
            logger.error(f"Failed to train model for {type_id} in {region_id}: {e}", exc_info=True)

    logger.info("Model training process finished.")

@celery_app.task(name="train_models.run_model_training_task")
def run_model_training_task():
    """Celery task to run the model training process."""
    logger.info("Executing run_model_training_task via Celery.")
    run_model_training()
    logger.info("Celery run_model_training_task finished.")

if __name__ == "__main__":
    run_model_training()