import os
from fastapi import FastAPI, HTTPException, Query, Depends, Header
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
class ItemAnalysis(BaseModel):
    type_id: int
    region_id: int
    item_name: str
    description: Optional[str]
    image_url: str
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
    last_updated: Optional[datetime]

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
                logger.info("No market history data found. Triggering initial data pipeline and analysis task chain via Celery.")
                task_chain = (
                    data_pipeline.run_data_pipeline_task.s() |
                    analysis.run_analysis_task.s()
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
@app.get("/top-items", response_model=List[ItemAnalysis])
@cache(expire=600)  # Cache for 10 minutes
async def get_top_items(
    limit: int = Query(100, ge=1, le=1000),
    region: int = Query(10000001, description="EVE Online region ID."),
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
            return ItemAnalysis(
                type_id=item['type_id'],
                region_id=region,
                item_name=item_details['name'],
                description=item_details['description'],
                image_url=f"https://images.evetech.net/types/{item['type_id']}/icon?size=64",
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
                last_updated=item.get('last_updated')
            )

        response_tasks = [create_response_item(top_items[i], predictions[i]) for i in range(len(top_items))]
        return await asyncio.gather(*response_tasks)
    except Exception as e:
        logger.error(f"Error in get_top_items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@app.get("/item/{type_id}", response_model=ItemDetail)
@cache(expire=600)  # Cache for 10 minutes
async def get_item_details(type_id: int, region_id: int = Query(10000001)):
    # Fetch pre-computed analysis data for a specific item
    query = "SELECT * FROM market_analysis WHERE type_id = %(type_id)s AND region_id = %(region_id)s"
    params = {"type_id": type_id, "region_id": region_id}
    item_df = await run_in_threadpool(pd.read_sql, query, engine, params=params)

    if item_df.empty:
        raise HTTPException(status_code=404, detail="Item analysis data not found for the given type and region.")

    item = item_df.iloc[0].to_dict()

    # Concurrently fetch prediction and ESI item details
    prediction_task = run_in_threadpool(predict.predict_next_day_prices, type_id, region_id)
    item_details_task = esi_utils.get_item_details(type_id)
    prediction_result, item_details = await asyncio.gather(prediction_task, item_details_task)

    analysis_data = ItemAnalysis(
        type_id=type_id,
        region_id=region_id,
        item_name=item_details['name'],
        description=item_details['description'],
        image_url=f"https://images.evetech.net/types/{type_id}/icon?size=64",
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
        last_updated=item.get('last_updated')
    )

    return ItemDetail(
        type_id=type_id,
        region_id=region_id,
        item_name=item_details['name'],
        analysis=analysis_data,
        prediction_confidence=prediction_result.get('confidence_score')
    )

@app.post("/refresh", response_model=RefreshStatus, dependencies=[Depends(verify_api_key)])
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

@app.get("/status", response_model=SystemStatusResponse)
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

@app.get("/regions", response_model=List[Region])
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