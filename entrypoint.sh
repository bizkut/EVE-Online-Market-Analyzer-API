#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready.
echo "Waiting for database to be ready..."
until pg_isready -d "$DATABASE_URL" -q; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done
>&2 echo "PostgreSQL is up."

# Run database schema initialization
echo "Initializing database schema..."
python database.py

# Run the initial data loader to populate the database if it's empty
echo "Running initial data loader..."
python initial_data_loader.py

# Set default log level if not provided and convert to lowercase
LOG_LEVEL=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

# Start the FastAPI server using exec.
echo "Starting server with log level: $LOG_LEVEL"
exec uvicorn main:app --host 0.0.0.0 --port 8000 --log-level "$LOG_LEVEL"