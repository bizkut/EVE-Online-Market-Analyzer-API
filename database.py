import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from sqlalchemy import create_engine
from logging_config import logger

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create a single, shared engine for the application
engine = create_engine(DATABASE_URL)

def get_db_connection():
    """Establishes a raw psycopg2 connection to the database."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def initialize_database():
    """Initializes the database by creating necessary tables if they don't exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Create market_orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_orders (
            order_id BIGINT PRIMARY KEY,
            type_id INT,
            location_id BIGINT,
            volume_total BIGINT,
            volume_remain BIGINT,
            min_volume BIGINT,
            price NUMERIC,
            is_buy_order BOOLEAN,
            duration INT,
            issued TIMESTAMP WITH TIME ZONE,
            range VARCHAR(255),
            system_id INT,
            station_id BIGINT,
            region_id INT,
            constellation_id INT,
            http_last_modified TIMESTAMP WITH TIME ZONE
        );
    """)

    # Create market_history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            id SERIAL PRIMARY KEY,
            type_id INT,
            region_id INT,
            date DATE,
            average NUMERIC,
            highest NUMERIC,
            lowest NUMERIC,
            order_count BIGINT,
            volume BIGINT,
            http_last_modified TIMESTAMP WITH TIME ZONE,
            UNIQUE(type_id, region_id, date)
        );
    """)

    # Create regions table (used for caching region names)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            region_id INT PRIMARY KEY,
            name VARCHAR(255) UNIQUE
        );
    """)

    # Create item_names table (used for caching item names)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS item_names (
            type_id INT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT
        );
    """)

    # Create an index on type_id and region_id for faster lookups
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_orders_type_region ON market_orders (type_id, region_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_history_type_region ON market_history (type_id, region_id);")


    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized successfully.")

if __name__ == "__main__":
    initialize_database()