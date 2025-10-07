import os
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import RedirectResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
from contextlib import asynccontextmanager
import logging
import logging_config  # Ensure logging is configured
import pandas as pd

# --- Setup Logger ---
logger = logging.getLogger(__name__)

# Caching imports
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

# Import project modules
import analysis
import predict
import data_pipeline
import esi_utils
import train_models
import system_status
from database import get_db_connection, engine
from celery_app import celery_app


# --- Security ---
API_KEY = os.getenv("API_KEY")

async def verify_api_key(x_api_key: str = Header(None)):
    """Dependency to verify the API key. Key is optional."""
    if API_KEY: # Only enforce the key if it's set in the environment
        if x_api_key is None:
            raise HTTPException(status_code=400, detail="X-API-Key header missing")
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")

# --- Pydantic Models for API Responses ---
class PriceHistoryItem(BaseModel):
    date: str
    buy: Optional[float]
    sell: Optional[float]

class VolumeHistoryItem(BaseModel):
    date: str
    volume: int

class ProfitHistoryItem(BaseModel):
    date: str
    profit_per_unit: Optional[float]
    roi_percent: Optional[float]

class Item(BaseModel):
    type_id: int
    name: str
    avg_buy_price: Optional[float] = None
    avg_sell_price: Optional[float] = None
    predicted_buy_price: Optional[float] = None
    predicted_sell_price: Optional[float] = None
    profit_per_unit: Optional[float] = None
    roi_percent: Optional[float] = None
    volume_30d_avg: Optional[float] = None
    volatility: Optional[float] = None
    trend_direction: Optional[str] = None
    last_updated: Optional[datetime] = None

class ItemDetail(Item):
    description: Optional[str] = None
    thumbnail_url: str
    price_history: List[PriceHistoryItem] = []
    volume_history: List[VolumeHistoryItem] = []
    profit_history: List[ProfitHistoryItem] = []

class RefreshStatus(BaseModel):
    status: str
    message: str

class SystemStatusResponse(BaseModel):
    service_name: str = "EVE Online Market API"
    pipeline_status: str
    initial_seeding_complete: bool
    last_data_update: Optional[str]
    last_analysis_update: Optional[str]

class Region(BaseModel):
    region_id: int
    name: str

# --- App Lifecycle (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("Application startup...")
    await run_in_threadpool(system_status.initialize_status_table)
    esi_utils.pre_populate_caches_from_db()

    # Initialize Redis cache
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    redis = aioredis.from_url(redis_url)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

    # --- Initial Data Population Trigger ---
    # On startup, check if the database is empty. If it is, trigger an
    # initial data fetch and analysis asynchronously using Celery.
    # This ensures data is available as soon as possible without blocking
    # the API server from starting.
    async def trigger_initial_setup_if_needed():
        logger.info("Performing initial data check...")
        try:
            def db_check():
                """Synchronous function to check for data in the database."""
                try:
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT EXISTS (SELECT 1 FROM market_history);")
                        return cur.fetchone()[0]
                except Exception:
                    # This can happen if the table doesn't exist yet on the very first run.
                    # In this case, we assume no data exists.
                    logger.warning("Could not check for market history, assuming it's empty.")
                    return False

            history_exists = await run_in_threadpool(db_check)

            if not history_exists:
                logger.info("No market history data found. Triggering initial data pipeline, analysis, and model training task chain via Celery.")
                task_chain = (
                    data_pipeline.run_data_pipeline_task.s() |
                    analysis.run_analysis_task.s() |
                    train_models.run_model_training_task.s()
                )
                task_chain.apply_async()
            else:
                logger.info("Existing market data found. Skipping initial data fetch.")

        except Exception as e:
            logger.error(f"Failed during initial data check: {e}", exc_info=True)

    # Run the check, but don't block the main startup flow for too long.
    # The check itself is quick because of the threadpool.
    await trigger_initial_setup_if_needed()

    logger.info("Celery services will handle all background tasks. No in-app scheduler started.")
    yield
    # On shutdown
    logger.info("Application shutdown...")

# --- App Initialization ---
app = FastAPI(
    title="EVE Online Market Profitability API",
    description="Analyzes EVE Online market data to find profitable trading opportunities.",
    version="1.0.0",
    lifespan=lifespan
)

# --- API Endpoints ---
def map_trend_direction(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    return {1: "Up", -1: "Down", 0: "Stable"}.get(value, "Unknown")

@app.get("/api/top-items", response_model=List[Item])
@cache(expire=600)  # Cache for 10 minutes
async def get_top_items(
    limit: int = Query(100, ge=1, le=1000),
    region: int = Query(10000002, description="EVE Online region ID."),
    min_volume: Optional[float] = Query(None, description="Minimum average daily volume."),
    min_roi: Optional[float] = Query(None, description="Minimum Return on Investment (ROI) in percent.")
):
    try:
        # Build the query to fetch pre-computed analysis data
        params = {"region": region, "limit": limit}
        query_parts = [
            "SELECT * FROM market_analysis",
            "WHERE region_id = %(region)s"
        ]
        if min_volume is not None:
            query_parts.append("AND avg_daily_volume >= %(min_volume)s")
            params["min_volume"] = min_volume
        if min_roi is not None:
            query_parts.append("AND roi_percent >= %(min_roi)s")
            params["min_roi"] = min_roi

        query_parts.append("ORDER BY profit_score DESC LIMIT %(limit)s")
        query = " ".join(query_parts)

        # Fetch data from the database
        results_df = await run_in_threadpool(pd.read_sql, query, engine, params=params)

        if results_df.empty:
            return []

        top_items = results_df.to_dict(orient='records')

        # Fetch predictions concurrently
        prediction_tasks = [
            run_in_threadpool(predict.predict_next_day_prices, item['type_id'], region) for item in top_items
        ]
        predictions = await asyncio.gather(*prediction_tasks)

        # Helper to build response items concurrently
        async def create_response_item(item, prediction_result):
            item_details = await esi_utils.get_item_details(item['type_id'])
            return Item(
                type_id=item['type_id'],
                name=item_details['name'],
                avg_buy_price=item.get('avg_buy_price'),
                avg_sell_price=item.get('avg_sell_price'),
                predicted_buy_price=prediction_result.get('predicted_buy_price'),
                predicted_sell_price=prediction_result.get('predicted_sell_price'),
                profit_per_unit=item.get('profit_per_unit'),
                roi_percent=item.get('roi_percent'),
                volume_30d_avg=item.get('avg_daily_volume'), # Field name mapping
                volatility=item.get('volatility_30d'), # Field name mapping
                trend_direction=map_trend_direction(item.get('trend_direction')), # Value mapping
                last_updated=item.get('last_updated')
            )

        response_tasks = [create_response_item(top_items[i], predictions[i]) for i in range(len(top_items))]
        return await asyncio.gather(*response_tasks)
    except Exception as e:
        logger.error(f"Error in get_top_items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@app.get("/api/item/{type_id}", response_model=ItemDetail)
@cache(expire=600)
async def get_item_details(type_id: int, region_id: int = Query(10000002)):
    # Fetch pre-computed analysis data for a specific item
    analysis_query = "SELECT * FROM market_analysis WHERE type_id = %(type_id)s AND region_id = %(region_id)s"
    params = {"type_id": type_id, "region_id": region_id}
    item_df = await run_in_threadpool(pd.read_sql, analysis_query, engine, params=params)

    if item_df.empty:
        raise HTTPException(status_code=404, detail="Item analysis data not found for the given type and region.")

    item_analysis = item_df.iloc[0].to_dict()

    # Fetch historical data for the last 30 days
    history_query = """
        SELECT date, average, volume, lowest, highest
        FROM market_history
        WHERE type_id = %(type_id)s AND region_id = %(region_id)s
          AND date >= (CURRENT_DATE - INTERVAL '30 days')
        ORDER BY date ASC
    """
    history_df = await run_in_threadpool(pd.read_sql, history_query, engine, params=params)

    price_history = []
    volume_history = []
    profit_history = []
    if not history_df.empty:
        price_history = [
            PriceHistoryItem(date=row['date'].strftime('%Y-%m-%d'), buy=row['lowest'], sell=row['highest'])
            for _, row in history_df.iterrows()
        ]
        volume_history = [
            VolumeHistoryItem(date=row['date'].strftime('%Y-%m-%d'), volume=row['volume'])
            for _, row in history_df.iterrows()
        ]
        profit_history = [
            ProfitHistoryItem(
                date=row['date'].strftime('%Y-%m-%d'),
                profit_per_unit=(row['highest'] - row['lowest']) if row['highest'] and row['lowest'] else 0,
                roi_percent=((row['highest'] - row['lowest']) / row['lowest'] * 100) if row['lowest'] and row['highest'] else 0
            )
            for _, row in history_df.iterrows()
        ]

    # Concurrently fetch prediction and ESI item details
    prediction_task = run_in_threadpool(predict.predict_next_day_prices, type_id, region_id)
    esi_details_task = esi_utils.get_item_details(type_id)
    prediction_result, esi_details = await asyncio.gather(prediction_task, esi_details_task)

    return ItemDetail(
        type_id=type_id,
        name=esi_details['name'],
        description=esi_details.get('description'),
        thumbnail_url=f"https://images.evetech.net/types/{type_id}/icon?size=128",
        avg_buy_price=item_analysis.get('avg_buy_price'),
        avg_sell_price=item_analysis.get('avg_sell_price'),
        predicted_buy_price=prediction_result.get('predicted_buy_price'),
        predicted_sell_price=prediction_result.get('predicted_sell_price'),
        profit_per_unit=item_analysis.get('profit_per_unit'),
        roi_percent=item_analysis.get('roi_percent'),
        volume_30d_avg=item_analysis.get('avg_daily_volume'),
        volatility=item_analysis.get('volatility_30d'),
        trend_direction=map_trend_direction(item_analysis.get('trend_direction')),
        last_updated=item_analysis.get('last_updated'),
        price_history=price_history,
        volume_history=volume_history,
        profit_history=profit_history
    )

@app.post("/api/refresh", response_model=RefreshStatus, dependencies=[Depends(verify_api_key)])
async def force_refresh():
    """
    Triggers a manual refresh of the market datasets and analysis via Celery.
    """
    try:
        logger.info("Manual refresh triggered. Chaining data pipeline and analysis tasks.")
        # Chain the tasks: run analysis only after the data pipeline succeeds.
        task_chain = (
            data_pipeline.run_data_pipeline_task.s() |
            analysis.run_analysis_task.s()
        )
        task_chain.apply_async()

        return RefreshStatus(
            status="success",
            message="Full data and analysis refresh initiated in the background via Celery."
        )
    except Exception as e:
        logger.error(f"Failed to trigger Celery refresh task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start refresh: {e}")

@app.get("/status", include_in_schema=False)
async def redirect_status():
    """
    Redirects legacy /status endpoint to /api/status.
    This is to handle external health checks that may not have been updated.
    """
    return RedirectResponse(url="/api/status", status_code=308)


@app.get("/api/status", response_model=SystemStatusResponse)
def get_system_status():
    """
    Returns the current status of the data pipeline and analysis tasks.
    """
    try:
        pipeline_status = system_status.get_status("pipeline_status", "idle")
        seeding_complete_str = system_status.get_status("initial_seeding_complete", "false")
        seeding_complete = seeding_complete_str.lower() == 'true'
        last_data_update = system_status.get_status("last_data_update", None)
        last_analysis_update = system_status.get_status("last_analysis_update", None)

        return SystemStatusResponse(
            pipeline_status=pipeline_status,
            initial_seeding_complete=seeding_complete,
            last_data_update=last_data_update,
            last_analysis_update=last_analysis_update
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching system status.")

@app.get("/api/regions", response_model=List[Region])
async def get_regions():
    """
    Returns a list of all available regions from the ESI.
    """
    return await esi_utils.get_all_regions()

@app.get("/")
async def root():
    return {"message": "Welcome to the EVE Online Market Profitability API"}

if __name__ == "__main__":
    import uvicorn
    # The centralized logger is already configured, so we just run the server.
    # The log level is handled by the logging_config module.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)