import pandas as pd
from sqlalchemy import text
from database import engine
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from datetime import datetime
from logging_config import logger

def get_item_history(type_id: int, region_id: int, days: int = 90) -> pd.DataFrame:
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

def _calculate_trend(df: pd.DataFrame) -> int:
    """Calculates the trend direction for a given history DataFrame."""
    df = df.dropna(subset=['price']).copy()
    if len(df) < 2:
        return 0
    # Create a numeric representation of the date for regression
    df['date_ordinal'] = df.index.map(datetime.toordinal)
    try:
        # Fit a linear regression to the price data
        coeffs = np.polyfit(df['date_ordinal'], df['price'], 1)
        slope = coeffs[0]
        # Classify the trend based on the slope
        if slope > 0.1: return 1
        if slope < -0.1: return -1
        return 0
    except np.linalg.LinAlgError:
        return 0

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Creates features for the prediction model."""
    if df.empty or len(df) < 30:
        return pd.DataFrame()

    df['avg_price_7d'] = df['price'].rolling(window=7).mean()
    df['avg_price_30d'] = df['price'].rolling(window=30).mean()
    df['volume_7d'] = df['volume'].rolling(window=7).mean()
    df['volatility_7d'] = df['price'].rolling(window=7).std()

    # Calculate trend direction over the last 30 days
    df['trend_direction'] = df['price'].rolling(window=30).apply(_calculate_trend, raw=False)

    # Target variable: next day's price
    df['target_price'] = df['price'].shift(-1)

    df.dropna(inplace=True)
    return df

def predict_next_day_prices(type_id: int, region_id: int):
    """
    Trains a model and predicts the next day's prices for an item.
    """
    history_df = get_item_history(type_id, region_id)

    if history_df.empty or len(history_df) < 30:
        logger.debug(f"Not enough historical data to generate prediction for type_id {type_id}.")
        return {
            "predicted_buy_price": None,
            "predicted_sell_price": None,
            "confidence_score": 0.0
        }

    features_df = create_features(history_df)

    if features_df.empty:
        logger.debug(f"Could not create features for prediction for type_id {type_id}.")
        return {
            "predicted_buy_price": None,
            "predicted_sell_price": None,
            "confidence_score": 0.0
        }

    # Define features (X) and target (y)
    features = ['avg_price_7d', 'avg_price_30d', 'volume_7d', 'volatility_7d', 'trend_direction']
    X = features_df[features]
    y = features_df['target_price']

    # Split data for a simple validation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Evaluate model to get a confidence score
    predictions = model.predict(X_test)
    confidence = r2_score(y_test, predictions)

    # Predict next day's price using the most recent data
    last_features = features_df[features].iloc[-1:].copy()
    predicted_avg_price = model.predict(last_features)[0]

    # Derive buy/sell from predicted average and recent volatility
    last_volatility = last_features['volatility_7d'].iloc[0]
    spread = last_volatility * 0.5  # Assume spread is half of the weekly std dev

    predicted_buy_price = predicted_avg_price - spread
    predicted_sell_price = predicted_avg_price + spread

    return {
        "predicted_buy_price": round(predicted_buy_price, 2) if pd.notna(predicted_buy_price) else None,
        "predicted_sell_price": round(predicted_sell_price, 2) if pd.notna(predicted_sell_price) else None,
        "confidence_score": round(confidence, 2)
    }

if __name__ == '__main__':
    # Example: Predict prices for Tritanium (type_id=34) in The Forge (region_id=10000001)
    TYPE_ID_TO_TEST = 34
    REGION_ID_TO_TEST = 10000001

    logger.info(f"Predicting prices for type_id={TYPE_ID_TO_TEST} in region={REGION_ID_TO_TEST}...")
    prediction_result = predict_next_day_prices(TYPE_ID_TO_TEST, REGION_ID_TO_TEST)

    if prediction_result["predicted_buy_price"] is not None:
        logger.info(f"  Predicted Buy Price: {prediction_result['predicted_buy_price']}")
        logger.info(f"  Predicted Sell Price: {prediction_result['predicted_sell_price']}")
        logger.info(f"  Confidence (R^2 Score): {prediction_result['confidence_score']}")
    else:
        logger.warning("  Could not generate a prediction. Not enough historical data.")