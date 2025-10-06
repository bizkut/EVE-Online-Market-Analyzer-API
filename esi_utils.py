import aiohttp
import asyncio
from sqlalchemy import text
from database import engine
import logging
import logging_config  # Ensure logging is configured

# --- Setup Logger ---
logger = logging.getLogger(__name__)

ESI_BASE_URL = "https://esi.evetech.net/latest"

# In-memory cache, loaded from the database on startup
ITEM_DETAILS_CACHE = {}  # Will store {'name': str, 'description': str}
REGION_NAMES_CACHE = {}
ALL_REGIONS_CACHE = None

async def fetch_esi(session, url):
    """A helper function to fetch data from the ESI API."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.warning(f"ESI API request failed for {url} with status: {response.status}")
                return None
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching from ESI: {e}", exc_info=True)
        return None

async def fetch_esi_paginated(session, url: str) -> list:
    """
    Asynchronously fetches all pages from a paginated ESI endpoint.
    """
    all_data = []
    try:
        # Initial request to get the first page and total number of pages
        async with session.get(url) as response:
            response.raise_for_status()
            pages_header = response.headers.get('X-Pages')
            total_pages = int(pages_header) if pages_header else 1
            data = await response.json()
            all_data.extend(data)

        # If there are more pages, fetch them concurrently
        if total_pages > 1:
            tasks = []
            for page in range(2, total_pages + 1):
                page_url = f"{url}?page={page}"
                # We create a new task for each page fetch
                tasks.append(fetch_esi(session, page_url))

            results = await asyncio.gather(*tasks)
            for page_data in results:
                if page_data:
                    all_data.extend(page_data)

    except aiohttp.ClientError as e:
        logger.error(f"Error fetching paginated data from {url}: {e}", exc_info=True)
        return [] # Return empty list on error
    except Exception as e:
        logger.error(f"An unexpected error occurred during pagination for {url}: {e}", exc_info=True)
        return []

    return all_data

async def get_item_details(type_id: int) -> dict:
    """Fetches an item's details (name, desc), using a multi-level cache."""
    default_details = {"name": f"Unknown Item ({type_id})", "description": ""}

    # 1. Check in-memory cache
    if type_id in ITEM_DETAILS_CACHE:
        return ITEM_DETAILS_CACHE[type_id]

    # 2. Check database cache
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name, description FROM item_names WHERE type_id = :type_id"), {"type_id": type_id}).first()
            if result:
                details = {"name": result[0], "description": result[1]}
                ITEM_DETAILS_CACHE[type_id] = details
                return details
    except Exception as e:
        logger.error(f"Database error while fetching item details for type_id {type_id}: {e}", exc_info=True)

    # 3. Fetch from ESI
    async with aiohttp.ClientSession() as session:
        url = f"{ESI_BASE_URL}/universe/types/{type_id}/"
        data = await fetch_esi(session, url)
        if data:
            name = data.get('name', f"Unknown Item ({type_id})")
            description = data.get('description', '')
            details = {"name": name, "description": description}
            ITEM_DETAILS_CACHE[type_id] = details

            # Save to database cache
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text("INSERT INTO item_names (type_id, name, description) VALUES (:type_id, :name, :description) ON CONFLICT (type_id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description"),
                        {"type_id": type_id, "name": name, "description": description}
                    )
                    conn.commit()
            except Exception as e:
                 logger.error(f"Database error while saving item details for type_id {type_id}: {e}", exc_info=True)
            return details

    return default_details

async def get_region_name(region_id: int) -> str:
    """Fetches a region's name, using a multi-level cache (memory -> DB -> ESI)."""
    if region_id in REGION_NAMES_CACHE:
        return REGION_NAMES_CACHE[region_id]

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM regions WHERE region_id = :region_id"), {"region_id": region_id}).first()
            if result:
                name = result[0]
                REGION_NAMES_CACHE[region_id] = name
                return name
    except Exception as e:
        logger.error(f"Database error while fetching region name for region_id {region_id}: {e}", exc_info=True)


    async with aiohttp.ClientSession() as session:
        url = f"{ESI_BASE_URL}/universe/regions/{region_id}/"
        data = await fetch_esi(session, url)
        if data and 'name' in data:
            name = data['name']
            REGION_NAMES_CACHE[region_id] = name
            try:
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO regions (region_id, name) VALUES (:region_id, :name) ON CONFLICT (region_id) DO UPDATE SET name = EXCLUDED.name"), {"region_id": region_id, "name": name})
                    conn.commit()
            except Exception as e:
                logger.error(f"Database error while saving region name for region_id {region_id}: {e}", exc_info=True)
            return name

    return f"Unknown Region ({region_id})"

async def get_all_regions() -> list:
    """Fetches all region IDs and their names from ESI, populating caches."""
    global ALL_REGIONS_CACHE
    if ALL_REGIONS_CACHE is not None:
        return ALL_REGIONS_CACHE

    async with aiohttp.ClientSession() as session:
        regions_url = f"{ESI_BASE_URL}/universe/regions/"
        region_ids = await fetch_esi(session, regions_url)
        if not region_ids:
            return []

        tasks = [get_region_name(region_id) for region_id in region_ids]
        await asyncio.gather(*tasks)

        all_regions = [{"region_id": rid, "name": name} for rid, name in REGION_NAMES_CACHE.items()]
        ALL_REGIONS_CACHE = all_regions
        return all_regions

def pre_populate_caches_from_db():
    """
    Loads all cached names from the database into the in-memory cache on startup.
    """
    logger.info("Pre-populating ESI caches from database...")
    try:
        with engine.connect() as conn:
            # Load item details
            items = conn.execute(text("SELECT type_id, name, description FROM item_names")).fetchall()
            for type_id, name, description in items:
                ITEM_DETAILS_CACHE[type_id] = {"name": name, "description": description}

            # Load region names
            regions = conn.execute(text("SELECT region_id, name FROM regions")).fetchall()
            for region_id, name in regions:
                REGION_NAMES_CACHE[region_id] = name

        logger.info(f"Pre-populated {len(ITEM_DETAILS_CACHE)} item details and {len(REGION_NAMES_CACHE)} region names from DB.")
    except Exception as e:
        logger.error(f"Failed to pre-populate caches from DB: {e}", exc_info=True)