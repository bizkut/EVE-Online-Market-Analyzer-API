#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready.
# The `until` loop will repeatedly check for the database connection.
# `pg_isready` is a utility that comes with postgresql-client.
# The -q flag makes it quiet on success.
echo "Waiting for database to be ready..."
until pg_isready -d "$DATABASE_URL" -q; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done
>&2 echo "PostgreSQL is up."

# Run database schema initialization
echo "Initializing database schema..."
python database.py

# Run the data pipeline to populate the database with initial data
echo "Running initial data pipeline..."
python data_pipeline.py

# Start the FastAPI server using exec.
# `exec` replaces the shell process with the uvicorn process,
# which is a good practice for container entrypoints.
echo "Starting server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000