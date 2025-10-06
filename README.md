# EVE Online Market Profitability API

This project is a FastAPI-based backend system that analyzes the EVE Online market using Everef datasets to determine and expose the most profitable tradable items through API endpoints. The system calculates current profitability, market trends, and predicted buy/sell prices based on historical data.

## Features

- **Live ESI Integration**: Fetches item names and descriptions directly from the EVE Online ESI API.
- **Rich Item Data**: API responses include item descriptions and a constructed image URL for easy frontend integration.
- **Robust Caching**: Uses a multi-level cache (in-memory -> database -> API) for static data and **Redis** for API endpoint caching to ensure high performance and reliability.
- **Data-Driven Analysis**: Performs a hybrid analysis using live market orders for current profitability and historical data for long-term trends.
- **Profitability Metrics**: Calculates key metrics such as `profit_per_unit`, `roi_percent`, `price_volume_correlation`, and a custom `profit_score` to rank items.
- **Price Prediction**: Includes a simple machine learning model to predict next-day buy/sell prices.
- **Scheduled Data Refreshes**: Automatically updates market data, runs analysis, and trains models using a distributed task queue (Celery).
- **Optional API Key**: The data refresh endpoint can be optionally secured with an API key.
- **Advanced Filtering**: Allows filtering of top items by minimum volume and ROI.
- **Containerized**: Fully containerized with Docker for easy and reliable deployment.

## Technical Stack

- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery
- **Key Libraries**: Pandas, SQLAlchemy, Scikit-learn, AIOHTTP

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Running the Application with Docker

This is the recommended method for running the application, as it provides a consistent and isolated environment.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create a `.env` file:**
    Copy the example environment variables into a new `.env` file.
    ```bash
    cp .env.example .env
    ```
    You can optionally set the `API_KEY` in this file to secure the `/api/refresh` endpoint.

3.  **Build and run the containers:**
    ```bash
    docker-compose up --build
    ```
    This command will:
    - Build the Docker image for the application.
    - Start all services, including the FastAPI backend, PostgreSQL database, Redis cache, Celery worker, and Celery beat scheduler.
    - Automatically run the `entrypoint.sh` script, which waits for the database to be ready, initializes the schema, and runs the initial data pipeline.

    The API will be available at `http://localhost:8000`. The initial data load may take several minutes.

## API Documentation

Once the application is running, the interactive API documentation (Swagger UI) will be available at `http://localhost:8000/docs`. The API response for items includes `description` and `image_url` fields for easy frontend integration.

### Main Endpoints

| Endpoint                                   | Method | Description                                                |
| ------------------------------------------ | ------ | ---------------------------------------------------------- |
| `/api/top-items` | GET    | Returns top profitable items with analysis and predictions. Supports filtering by `limit`, `region`, `min_volume`, and `min_roi`. |
| `/api/item/{type_id}`                      | GET    | Returns detailed stats and trend data for an item.          |
| `/api/refresh`                             | POST   | Forces a dataset refresh (background task). Can be secured with an `X-API-Key` header. |
| `/api/status`                              | GET    | System health, dataset timestamps, and update status.       |
| `/api/regions`                             | GET    | List of all available regions from the ESI.                |

## Project Structure

```
.
├── .github/workflows/debug.yml  # GitHub Actions workflow for debugging
├── .env.example                 # Example environment variables
├── analysis.py                  # Profitability and trend analysis logic
├── celery_app.py                # Celery application and task scheduling
├── data_pipeline.py             # Data fetching, parsing, and storage
├── database.py                  # Database connection and schema initialization
├── Dockerfile                   # Defines the application container
├── docker-compose.yml           # Defines the application and database services
├── entrypoint.sh                # Automates setup on container start
├── esi_utils.py                 # ESI API fetching and caching logic
├── main.py                      # FastAPI application entrypoint
├── predict.py                   # Price prediction model
├── README.md                    # This file
└── requirements.txt             # Python dependencies
```