# EVE Online Market Profitability API

This project is a FastAPI-based backend system that analyzes the EVE Online market using Everef datasets to determine and expose the most profitable tradable items through API endpoints. The system calculates current profitability, market trends, and predicted buy/sell prices based on historical data from the past 90 days.

## Features

- **Data-Driven Analysis**: Utilizes Everef's market orders and history datasets for comprehensive market analysis.
- **Profitability Metrics**: Calculates key metrics such as `profit_per_unit`, `roi_percent`, and a custom `profit_score` to rank items.
- **Trend Analysis**: Determines market trends and volatility to inform trading decisions.
- **Price Prediction**: Includes a simple machine learning model to predict next-day buy/sell prices.
- **Scheduled Data Refreshes**: Automatically updates market data every hour to ensure freshness.
- **Caching**: Caches API responses to improve performance and reduce load.
- **Containerized**: Fully containerized with Docker for easy and reliable deployment.

## Technical Stack

- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Scheduler**: APScheduler
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
    Copy the example environment variables into a new `.env` file. This file will provide the necessary credentials to the application and database services.
    ```bash
    cp .env.example .env
    ```

3.  **Build and run the containers:**
    ```bash
    docker-compose up --build
    ```
    This command will:
    - Build the Docker image for the FastAPI application.
    - Start the `web` (FastAPI) and `db` (PostgreSQL) services.
    - Automatically run the `entrypoint.sh` script, which waits for the database to be ready, initializes the schema, and runs the initial data pipeline.

    The API will be available at `http://localhost:8000`. The initial data load may take several minutes.

## API Documentation

Once the application is running, the interactive API documentation (Swagger UI) will be available at `http://localhost:8000/docs`.

### Main Endpoints

| Endpoint                                   | Method | Description                                                |
| ------------------------------------------ | ------ | ---------------------------------------------------------- |
| `/api/top-items?limit=100&region=10000001` | GET    | Returns top profitable items with analysis and predictions |
| `/api/item/{type_id}`                      | GET    | Returns detailed stats and trend data for an item          |
| `/api/refresh`                             | POST   | Forces a dataset refresh and re-analysis (background task) |
| `/api/status`                              | GET    | System health, dataset timestamps, and update status       |
| `/api/regions`                             | GET    | List of available regions and names (placeholder data)     |

## Project Structure

```
.
├── .github/workflows/debug.yml  # GitHub Actions workflow for debugging
├── .env.example                 # Example environment variables
├── analysis.py                  # Profitability and trend analysis logic
├── data_pipeline.py             # Data fetching, parsing, and storage
├── database.py                  # Database connection and schema initialization
├── Dockerfile                   # Defines the application container
├── docker-compose.yml           # Defines the application and database services
├── entrypoint.sh                # Automates setup on container start
├── main.py                      # FastAPI application entrypoint
├── predict.py                   # Price prediction model
├── README.md                    # This file
├── requirements.txt             # Python dependencies
└── scheduler.py                 # Scheduled data refresh logic
```

## Future Enhancements

-   **Populate Item and Region Names**: Replace the placeholder dictionaries with a proper data source, such as the EVE Online SDE (Static Data Export).
-   **Improve Prediction Model**: Enhance the prediction model with more features or a more sophisticated algorithm (e.g., Prophet, LSTMs).
-   **Add Authentication**: Secure the `/api/refresh` endpoint and any other sensitive endpoints.
-   **Implement Robust Caching**: Replace the in-memory cache with a more scalable solution like Redis.
-   **Add User-Facing Frontend**: Build a dashboard to visualize the market data and profitability insights.