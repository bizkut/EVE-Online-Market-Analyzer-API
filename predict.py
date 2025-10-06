import pandas as pd
from sqlalchemy import text
from database import engine
import numpy as np
from datetime import datetime
import logging
import logging_config  # Ensure logging is configured
import joblib
from pathlib import Path

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
MODEL_DIR = Path("models")
MIN_DAYS_FOR_PREDICTION = 30
HISTORY_DAYS_TO_FETCH = 90 # We need enough data to generate features

def get_item_history(type_id: int, region_id: int, days: int) -> pd.DataFrame:
    """Retrieves market history for a specific item in a region for the last N days."""
    query = text(f"""
        SELECT date, average as price, volume
        FROM market_history
        WHERE region_id = :region_id AND type_id = :type_id AND date >= NOW() - INTERVAL '{days} days'
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
    if len(df) < 2: return 0
    df['date_ordinal'] = df.index.map(datetime.toordinal)
    try:
        coeffs = np.polyfit(df['date_ordinal'], df['price'], 1)
        slope = coeffs[0]
        if abs(slope) < 0.01: return 0
        return 1 if slope > 0 else -1
    except (np.linalg.LinAlgError, ValueError):
        return 0

def create_features_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """Creates features for the latest data point in the dataframe."""
    if df.empty or len(df) < MIN_DAYS_FOR_PREDICTION:
        return pd.DataFrame()

    df['avg_price_7d'] = df['price'].rolling(window=7).mean()
    df['avg_price_30d'] = df['price'].rolling(window=30).mean()
    df['volume_7d'] = df['volume'].rolling(window=7).mean()
    df['volatility_7d'] = df['price'].rolling(window=7).std()
    df['trend_direction'] = df['price'].rolling(window=30, min_periods=10).apply(_calculate_trend, raw=False)

    # Return only the last row with complete features
    return df.dropna().iloc[-1:]

def predict_next_day_prices(type_id: int, region_id: int):
    """
    Loads a pre-trained model and predicts the next day's price for an item.
    """
    model_filename = f"{region_id}_{type_id}.joblib"
    model_path = MODEL_DIR / model_filename

    if not model_path.exists():
        logger.warning(f"Prediction model not found for type_id {type_id} in region {region_id}.")
        return {
            "predicted_buy_price": None,
            "predicted_sell_price": None,
            "error": "Model not available for this item."
        }

    # Load the pre-trained model
    try:
        model = joblib.load(model_path)
    except Exception as e:
        logger.error(f"Failed to load model {model_path}: {e}", exc_info=True)
        return {
            "predicted_buy_price": None,
            "predicted_sell_price": None,
            "error": "Failed to load prediction model."
        }

    # Fetch recent history to generate features for the prediction
    history_df = get_item_history(type_id, region_id, days=HISTORY_DAYS_TO_FETCH)

    if history_df.empty or len(history_df) < MIN_DAYS_FOR_PREDICTION:
        logger.debug(f"Not enough recent historical data to generate prediction for type_id {type_id}.")
        return {
            "predicted_buy_price": None,
            "predicted_sell_price": None,
            "error": "Not enough recent data for a prediction."
        }

    # Create features for the most recent day
    last_features_df = create_features_for_prediction(history_df)

    if last_features_df.empty:
        logger.debug(f"Could not create features from recent data for type_id {type_id}.")
        return {
            "predicted_buy_price": None,
            "predicted_sell_price": None,
            "error": "Failed to generate prediction features."
        }

    features = ['avg_price_7d', 'avg_price_30d', 'volume_7d', 'volatility_7d', 'trend_direction']

    # Predict next day's price using the loaded model
    predicted_avg_price = model.predict(last_features_df[features])[0]

    # Derive buy/sell from predicted average and recent volatility
    last_volatility = last_features_df['volatility_7d'].iloc[0]
    spread = last_volatility * 0.5  # Assume spread is half of the weekly std dev

    predicted_buy_price = predicted_avg_price - spread
    predicted_sell_price = predicted_avg_price + spread

    return {
        "predicted_buy_price": round(predicted_buy_price, 2) if pd.notna(predicted_buy_price) else None,
        "predicted_sell_price": round(predicted_sell_price, 2) if pd.notna(predicted_sell_price) else None,
        "prediction_date": (history_df.index.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    }

if __name__ == '__main__':
    # Example: Predict prices for Tritanium (type_id=34) in The Forge (region_id=10000001)
    TYPE_ID_TO_TEST = 34
    REGION_ID_TO_TEST = 10000001

    logger.info(f"Predicting prices for type_id={TYPE_ID_TO_TEST} in region={REGION_ID_TO_TEST}...")
    prediction_result = predict_next_day_prices(TYPE_ID_TO_TEST, REGION_ID_TO_TEST)

    if prediction_result.get("predicted_buy_price") is not None:
        logger.info(f"  Prediction for: {prediction_result['prediction_date']}")
        logger.info(f"  Predicted Buy Price: {prediction_result['predicted_buy_price']}")
        logger.info(f"  Predicted Sell Price: {prediction_result['predicted_sell_price']}")
    else:
        logger.warning(f"  Could not generate a prediction. Reason: {prediction_result.get('error', 'Unknown')}")