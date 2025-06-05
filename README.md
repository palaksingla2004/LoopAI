# Data Ingestion API System

A simple API system that provides endpoints for submitting data ingestion requests and checking their status. The system fetches data from a simulated external API, processes it in batches asynchronously, and respects rate limits and priorities.

## Features

- **Ingestion API**: Submit a list of IDs with a priority level
- **Status API**: Check the status of an ingestion request
- **Asynchronous Processing**: Process batches in the background
- **Rate Limiting**: Process at most 1 batch every 5 seconds
- **Priority Handling**: Process higher priority requests first

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn
- Requests (for testing)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/data-ingestion-api.git
   cd data-ingestion-api
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

Start the application locally:

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

Once the application is running, you can access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Ingestion API

**Endpoint:** `POST /ingest`

**Request Body:**
```json
{
  "ids": [1, 2, 3, 4, 5],
  "priority": "HIGH"  // Options: HIGH, MEDIUM, LOW
}
```

**Response:**
```json
{
  "ingestion_id": "abc123"
}
```

### Status API

**Endpoint:** `GET /status/{ingestion_id}`

**Response:**
```json
{
  "ingestion_id": "abc123",
  "status": "triggered",
  "batches": [
    {"batch_id": "uuid1", "ids": [1, 2, 3], "status": "completed"},
    {"batch_id": "uuid2", "ids": [4, 5], "status": "triggered"}
  ]
}
```

## Testing

Run the test suite to verify the API functionality:

```
python test_api.py
```

The test script will:
1. Test the ingestion endpoint with various payloads
2. Test the status endpoint
3. Verify priority handling (higher priority requests are processed first)
4. Verify rate limiting (max 1 batch per 5 seconds)

## Design Choices

### Asynchronous Processing

The system uses FastAPI's background tasks and asyncio to process batches asynchronously. This allows the API to return immediately while processing continues in the background.

### In-Memory Storage

For simplicity, this implementation uses in-memory storage for ingestion requests and their batches. In a production environment, you would want to use a persistent database.

### Rate Limiting

Rate limiting is implemented using a simple time-based approach. A global timestamp tracks when the last batch was processed, and new batches wait until at least 5 seconds have passed.

### Priority Queue

The processing queue is sorted by priority and creation time, ensuring that higher priority requests are processed first, and within the same priority level, older requests are processed first.

## Deployment

### Deploying to Heroku

1. Create a Heroku account and install the Heroku CLI
2. Login to Heroku:
   ```
   heroku login
   ```
3. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```
4. Create a Procfile in the project root:
   ```
   web: uvicorn main:app --host=0.0.0.0 --port=${PORT:-8000}
   ```
5. Deploy the application:
   ```
   git push heroku main
   ```

### Deploying to Railway

1. Create a Railway account
2. Connect your GitHub repository
3. Add a new service from your repository
4. Set the start command to:
   ```
   uvicorn main:app --host=0.0.0.0 --port=$PORT
   ```
5. Deploy the service

## Screenshots

![Test Run Screenshot](test_run_screenshot.png)

## License

MIT 