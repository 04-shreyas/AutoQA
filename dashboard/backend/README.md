# AutoQA Dashboard Backend

FastAPI backend server for the AutoQA React dashboard.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python dashboard/backend/main.py
```

Or with uvicorn directly:
```bash
uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

## API Endpoints

### Health & Status

- `GET /api/health` - API status and last run timestamp
- `GET /api/runs` - List all available runs with timestamps

### Data Retrieval

- `GET /api/summary` - Combined summary of latest run
- `GET /api/latest-report` - Latest report content
- `GET /api/test-results` - Test generation results
- `GET /api/hallucination-results` - Hallucination detection results
- `GET /api/drift-results` - Drift analysis results

### Pipeline Control

- `POST /api/run` - Start a new pipeline run
  - Body: `{ target_path: str, prompts_path: str, model: str }`
  - Response: `{ status: "started", run_id: str }`

- `GET /api/run-status/{run_id}` - Get status of a running pipeline
  - Response: `{ status: "running/completed/failed", progress: int, current_step: str }`

## CORS Configuration

The backend is configured to allow requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (React default)

Modify the CORS origins in `main.py` if needed.
