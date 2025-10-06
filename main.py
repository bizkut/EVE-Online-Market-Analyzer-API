import logging
import os
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
from contextlib import asynccontextmanager

# Caching imports
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

# Import project modules
import analysis
import predict
import data_pipeline
import sde_utils
from database import get_db_connection
from scheduler import start_scheduler, stop_scheduler

# Use the Uvicorn logger
logger = logging.getLogger("uvicorn.error")

# --- Security ---
API_KEY = os.getenv("API_KEY")

async def verify_api_key(x_api_key: str = Header(...)):
    """Dependency to verify the API key."""
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# --- Pydantic Models for API Responses ---
class ItemAnalysis(BaseModel):
    type_id: int
    region_id: int
    item_name: str
    avg_buy_price: Optional[float]
    avg_sell_price: Optional[float]
    predicted_buy_price: Optional[float]
    predicted_sell_price: Optional[float]
    profit_per_unit: Optional[float]
    roi_percent: Optional[float]
    avg_daily_volume: Optional[float]
    volatility_30d: Optional[float]
    trend_direction: Optional[int]
    price_volume_correlation: Optional[float]
    last_updated: datetime

class ItemDetail(BaseModel):
    type_id: int
    region_id: int
    item_name: str
    analysis: ItemAnalysis
    prediction_confidence: Optional[float]
    historical_data: list = []

class RefreshStatus(BaseModel):
    status: str
    message: str

class SystemStatus(BaseModel):
    service: str = "EVE Online Market API"
    status: str
    latest_market_order_update: Optional[datetime]
    latest_market_history_update: Optional[datetime]

class Region(BaseModel):
    region_id: int
    name: str

# --- App Lifecycle (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("Application startup...")
    sde_utils.load_sde_data()
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    start_scheduler()
    yield
    # On shutdown
    logger.info("Application shutdown...")
    stop_scheduler()

# --- App Initialization ---
app = FastAPI(
    title="EVE Online Market Profitability API",
    description="Analyzes EVE Online market data to find profitable trading opportunities.",
    version="1.0.0",
    lifespan=lifespan
)

# Placeholder data removed, will be loaded from SDE

# --- API Endpoints ---
@app.get("/api/top-items", response_model=List[ItemAnalysis])
@cache(expire=3600)  # Cache for 1 hour
async def get_top_items(
    limit: int = Query(100, ge=1, le=1000),
    region: int = Query(10000001, description="EVE Online region ID."),
    min_volume: Optional[float] = Query(None, description="Minimum average daily volume."),
    min_roi: Optional[float] = Query(None, description="Minimum Return on Investment (ROI) in percent.")
):
    try:
        results_df = await run_in_threadpool(analysis.analyze_market_data, region)

        # Apply filters
        if min_volume is not None:
            results_df = results_df[results_df['avg_daily_volume'] >= min_volume]
        if min_roi is not None:
            results_df = results_df[results_df['roi_percent'] >= min_roi]

        if results_df.empty:
            return []

        top_items = results_df.head(limit).to_dict(orient='records')

        prediction_tasks = [
            run_in_threadpool(predict.predict_next_day_prices, item['type_id'], region) for item in top_items
        ]
        predictions = await asyncio.gather(*prediction_tasks)

        response_items = []
        for i, item in enumerate(top_items):
            prediction_result = predictions[i]
            response_items.append(
                ItemAnalysis(
                    type_id=item['type_id'],
                    region_id=region,
                    item_name=sde_utils.get_item_name(item['type_id']),
                    avg_buy_price=item.get('avg_buy_price'),
                    avg_sell_price=item.get('avg_sell_price'),
                    predicted_buy_price=prediction_result.get('predicted_buy_price'),
                    predicted_sell_price=prediction_result.get('predicted_sell_price'),
                    profit_per_unit=item.get('profit_per_unit'),
                    roi_percent=item.get('roi_percent'),
                    avg_daily_volume=item.get('avg_daily_volume'),
                    volatility_30d=item.get('volatility_30d'),
                    trend_direction=item.get('trend_direction'),
                    price_volume_correlation=item.get('price_volume_correlation'),
                    last_updated=datetime.now(timezone.utc)
                )
            )
        return response_items
    except Exception as e:
        logger.error(f"Error in get_top_items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@app.get("/api/item/{type_id}", response_model=ItemDetail)
@cache(expire=3600)  # Cache for 1 hour
async def get_item_details(type_id: int, region_id: int = Query(10000001)):
    results_df = await run_in_threadpool(analysis.analyze_market_data, region_id)
    item_data = results_df[results_df['type_id'] == type_id]

    if item_data.empty:
        raise HTTPException(status_code=404, detail="Item not found or no profitable trades available.")

    item = item_data.iloc[0].to_dict()
    prediction_result = await run_in_threadpool(predict.predict_next_day_prices, type_id, region_id)

    analysis_data = ItemAnalysis(
        type_id=type_id,
        region_id=region_id,
        item_name=sde_utils.get_item_name(type_id),
        avg_buy_price=item.get('avg_buy_price'),
        avg_sell_price=item.get('avg_sell_price'),
        predicted_buy_price=prediction_result.get('predicted_buy_price'),
        predicted_sell_price=prediction_result.get('predicted_sell_price'),
        profit_per_unit=item.get('profit_per_unit'),
        roi_percent=item.get('roi_percent'),
        avg_daily_volume=item.get('avg_daily_volume'),
        volatility_30d=item.get('volatility_30d'),
        trend_direction=item.get('trend_direction'),
        price_volume_correlation=item.get('price_volume_correlation'),
        last_updated=datetime.now(timezone.utc)
    )

    return ItemDetail(
        type_id=type_id,
        region_id=region_id,
        item_name=sde_utils.get_item_name(type_id),
        analysis=analysis_data,
        prediction_confidence=prediction_result.get('confidence_score')
    )

@app.post("/api/refresh", response_model=RefreshStatus, dependencies=[Depends(verify_api_key)])
async def force_refresh():
    """
    Triggers a manual refresh of the market datasets, protected by an API key.
    """
    try:
        # Run the pipeline in the background to avoid blocking the response
        asyncio.create_task(data_pipeline.main())
        return RefreshStatus(status="success", message="Data refresh initiated in the background.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start refresh: {e}")

@app.get("/api/status", response_model=SystemStatus)
def get_system_status():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(http_last_modified) FROM market_orders;")
            latest_order_update = cur.fetchone()[0]
            cur.execute("SELECT MAX(date) FROM market_history;")
            latest_history_update = cur.fetchone()[0]
            cur.close()

        return SystemStatus(
            status="online",
            latest_market_order_update=latest_order_update,
            latest_market_history_update=latest_history_update
        )
    except Exception as e:
        return SystemStatus(status="error", latest_market_order_update=None, latest_market_history_update=None)

@app.get("/api/regions", response_model=List[Region])
def get_regions():
    """
    Returns a list of available regions from the SDE.
    """
    return sde_utils.get_all_regions()

@app.get("/")
async def root():
    return {"message": "Welcome to the EVE Online Market Profitability API"}

if __name__ == "__main__":
    import uvicorn
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=log_level)