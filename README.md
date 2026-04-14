# StayAgent API

StayAgent is a high-performance asynchronous crawler designed to find and aggregate stay locations from multiple platforms, including **Airbnb** and **Booking.com**, based on check-in/check-out dates and guest counts.

The backend is built with **FastAPI** and uses **Playwright** for robust headless browser scraping to bypass common bot detection.

## 🚀 Features

- **Asynchronous Search**: Trigger a search job and poll for results via a unique operation ID.
- **Multi-Platform Support**: Aggregates results from Airbnb and Booking.com concurrently.
- **Shared Browser Lifecycle**: A single Playwright Chromium instance is shared across all requests. Each crawl job receives an isolated `BrowserContext` (separate cookies and storage), eliminating the ~2-5s per-request browser startup overhead.
- **Resilient Selector Registry**: CSS selectors are centralized in `app/crawlers/config.py` and organized as ordered fallback lists. When a platform changes its UI, only the config needs updating — no logic changes required.
- **Extensible Storage**: Uses an abstract `JobStore` interface, allowing for easy migration from in-memory to persistent databases (Redis/Postgres).
- **Auto-generated Documentation**: Interactive API documentation via Swagger UI.

## 🛠 Prerequisites

- **Python 3.13+** (Recommended)
- **Playwright**

## 📦 Installation

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd stayagent
   ```

2. **Set up a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**

   ```bash
   playwright install chromium
   ```

## 🏃 Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## 🧪 Running Tests

```bash
# Unit tests only (no browser required)
pytest tests/unit/ -v

# Integration tests (requires Playwright Chromium)
pytest tests/integration/ -v
```

## 📖 API Documentation

Once the server is running, you can access the interactive documentation at:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 📡 API Usage Example

### 1. Start a Search Operation

**POST** `/api/v1/search/`

```json
{
  "location": "Boston",
  "checkin": "2026-05-01",
  "checkout": "2026-05-05",
  "guests": 2,
  "limit": 10
}
```

### 2. Poll Status

**GET** `/api/v1/search/{operation_id}/status`

### 3. Retrieve Results

**GET** `/api/v1/search/{operation_id}/results`

## ⚖️ License

MIT
