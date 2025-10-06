# EVE Online Market Analyzer - Frontend

This is the Next.js frontend for the EVE Online Market Analyzer. It provides a dashboard to visualize market data from the FastAPI backend.

## ✨ Features

-   **Dashboard:** A sortable and filterable table of the top 100 most profitable items.
-   **Item Details:** A detailed modal view with price, volume, and profit history charts.
-   **Settings:** User-configurable filters for region, ROI, and volume.
-   **Theme:** A dark/light mode toggle with a sci-fi inspired theme.
-   **Status Bar:** Real-time backend connection status and data freshness information.

## 🛠️ Tech Stack

-   **Framework:** Next.js 15 (React + TypeScript)
-   **Styling:** Tailwind CSS
-   **Charts:** Recharts
-   **State Management:** Zustand
-   **HTTP Requests:** Axios
-   **UI Components:** Headless UI

## 🚀 Getting Started

### Prerequisites

-   Node.js (v18 or later)
-   Yarn

### Installation

1.  **Clone the repository** (if you haven't already).
2.  **Navigate to the `frontend` directory:**
    ```bash
    cd frontend
    ```
3.  **Install dependencies:**
    ```bash
    yarn install
    ```

### Environment Variables

Create a `.env.local` file in the `frontend` directory and add the following environment variable. This URL should point to your running backend API.

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### Running the Development Server

To start the development server, run:

```bash
yarn dev
```

The application will be available at `http://localhost:3000`.

## scripts

-   `yarn dev`: Starts the development server.
-   `yarn build`: Creates a production build of the application.
-   `yarn start`: Starts the production server.
-   `yarn lint`: Lints the code using ESLint.