import pandas as pd
import requests
import zipfile
import io
import os
import json

SDE_URL = "https://sde.riftforeve.online/eve-online-static-data-3041737-jsonl.zip"
SDE_DIR = "sde"
TYPE_IDS_FILE = os.path.join(SDE_DIR, "typeIDs.jsonl")
REGIONS_FILE = os.path.join(SDE_DIR, "regions.jsonl")

# In-memory cache for the data, loaded on app startup
ITEM_NAMES = {}
REGION_NAMES = {}

def setup_sde_files():
    """
    Downloads and extracts the EVE SDE.
    This function is intended to be called during the Docker image build.
    """
    if os.path.exists(SDE_DIR):
        print("SDE directory already exists. Skipping download.")
        return

    print("Downloading EVE SDE...")
    response = requests.get(SDE_URL, stream=True)
    response.raise_for_status()

    print("Extracting SDE...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Extract only the necessary files
        z.extract("typeIDs.jsonl", SDE_DIR)
        z.extract("regions.jsonl", SDE_DIR)
    print("SDE download and extraction complete.")

def load_sde_data():
    """
    Loads item and region names from the SDE files into memory.
    This should be called on application startup.
    """
    global ITEM_NAMES, REGION_NAMES

    if not os.path.exists(TYPE_IDS_FILE) or not os.path.exists(REGIONS_FILE):
        print("SDE files not found. Using fallback placeholder data.")
        ITEM_NAMES = {34: "Tritanium", 20: "Small Shield Booster I"}
        REGION_NAMES = {10000001: "The Forge", 10000002: "Jita"}
        return

    # Load item names (typeIDs.jsonl)
    with open(TYPE_IDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            if 'en' in item.get('name', {}):
                ITEM_NAMES[item['typeID']] = item['name']['en']

    # Load region names (regions.jsonl)
    with open(REGIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            region = json.loads(line)
            if 'en' in region.get('name', {}):
                REGION_NAMES[region['regionID']] = region['name']['en']

    print(f"Loaded {len(ITEM_NAMES)} item names and {len(REGION_NAMES)} region names.")

def get_item_name(type_id: int) -> str:
    """Returns the English name for a given typeID."""
    return ITEM_NAMES.get(type_id, f"Unknown Item ({type_id})")

def get_region_name(region_id: int) -> str:
    """Returns the English name for a given regionID."""
    return REGION_NAMES.get(region_id, f"Unknown Region ({region_id})")

def get_all_regions() -> list:
    """Returns a list of all regions with their IDs and names."""
    return [{"region_id": rid, "name": name} for rid, name in REGION_NAMES.items()]

if __name__ == "__main__":
    # This allows running the script directly to download the SDE data
    setup_sde_files()