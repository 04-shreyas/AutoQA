from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Setup path for AutoQA imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from autoqa import config

app = FastAPI(title="AutoQA Backend", version="1.0.0")

# Enable CORS for React frontend (Vite default port)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173", "http://localhost:3000"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Track running processes
_running_processes: dict[str, dict[str, Any]] = {}


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
	"""Check API health and return last run timestamp."""
	latest_run = _get_latest_file(Path(config.DATA_DIR), "run_*.json")
	last_run_timestamp = None
	
	if latest_run:
		try:
			data = json.loads(latest_run.read_text(encoding="utf-8"))
			last_run_timestamp = data.get("timestamp") or latest_run.stat().st_mtime
		except Exception:
			last_run_timestamp = latest_run.stat().st_mtime
	
	return {
		"status": "healthy",
		"api_version": "1.0.0",
		"last_run": last_run_timestamp,
		"timestamp": datetime.utcnow().isoformat(),
	}


@app.get("/api/latest-report")
async def latest_report() -> dict[str, str]:
	"""Get the latest report as JSON."""
	report_file = Path(config.REPORTS_DIR) / "latest_report.md"
	
	if not report_file.exists():
		raise HTTPException(status_code=404, detail="No report found")
	
	try:
		content = report_file.read_text(encoding="utf-8")
		return {
			"content": content,
			"timestamp": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
		}
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/summary")
async def summary() -> dict[str, Any]:
	"""Get combined summary from latest run data."""
	try:
		# Load latest test results
		test_results = _load_latest_json("run_*.json")
		
		# Load latest hallucination results
		hallucin_results = _load_latest_json("hallucination_*.json")
		
		# Load latest drift results
		drift_results = _load_latest_json("drift_*.json")
		
		# Extract key metrics
		tests_generated = 0
		pass_rate = 0.0
		if test_results:
			tests_generated = test_results.get("total_prompts", 0)
			# For test generation results
			if "overall_pass_rate" in test_results:
				pass_rate = test_results.get("overall_pass_rate", 0.0) * 100
		
		avg_hallucin_score = 0.0
		if hallucin_results:
			stats = hallucin_results.get("statistics", {})
			avg_scores = stats.get("average_scores", {})
			avg_hallucin_score = avg_scores.get("overall_score", 0.0)
		
		drift_score = 0.0
		if drift_results:
			drift_score = drift_results.get("drift_score", 0.0)
		
		# Calculate health score
		health_score = _calculate_health_score(pass_rate / 100, avg_hallucin_score / 100, drift_score / 100)
		
		last_run = test_results.get("timestamp") if test_results else None
		
		return {
			"tests_generated": tests_generated,
			"pass_rate": pass_rate,
			"avg_hallucination_score": avg_hallucin_score,
			"drift_score": drift_score,
			"health_score": health_score,
			"last_run": last_run or datetime.utcnow().isoformat(),
		}
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/test-results")
async def test_results() -> dict[str, Any]:
	"""Get test results from latest review report."""
	try:
		# Load latest run file (contains test results)
		data = _load_latest_json("run_*.json")
		if not data:
			raise HTTPException(status_code=404, detail="No test results found")
		
		return {
			"total_tests": data.get("total_tests", 0),
			"passed": data.get("passed", 0),
			"failed": data.get("failed", 0),
			"pass_rate": data.get("pass_rate", 0.0),
			"test_results": data.get("test_results", []),
			"timestamp": data.get("timestamp"),
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/hallucination-results")
async def hallucination_results() -> dict[str, Any]:
	"""Get hallucination detection results."""
	try:
		data = _load_latest_json("hallucination_*.json")
		if not data:
			raise HTTPException(status_code=404, detail="No hallucination results found")
		
		return {
			"total_prompts": data.get("total_prompts", 0),
			"results": data.get("results", []),
			"statistics": data.get("statistics", {}),
			"timestamp": data.get("timestamp"),
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/drift-results")
async def drift_results() -> dict[str, Any]:
	"""Get drift analysis results."""
	try:
		data = _load_latest_json("drift_*.json")
		if not data:
			raise HTTPException(status_code=404, detail="No drift results found")
		
		return {
			"drift_score": data.get("drift_score", 0.0),
			"metrics": data.get("metrics", {}),
			"comparisons": data.get("comparisons", []),
			"regressions": data.get("regressions", []),
			"timestamp": data.get("timestamp"),
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/runs")
async def list_runs() -> dict[str, Any]:
	"""List all available runs with timestamps."""
	try:
		data_dir = Path(config.DATA_DIR)
		if not data_dir.exists():
			return {"runs": []}
		
		run_files = sorted(data_dir.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
		
		runs = []
		for run_file in run_files:
			try:
				data = json.loads(run_file.read_text(encoding="utf-8"))
				runs.append({
					"filename": run_file.name,
					"timestamp": data.get("timestamp") or datetime.fromtimestamp(run_file.stat().st_mtime).isoformat(),
					"total_prompts": data.get("total_prompts", 0),
				})
			except Exception:
				continue
		
		return {"runs": runs}
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/run")
async def trigger_run(request_data: dict[str, str]) -> dict[str, str]:
	"""Trigger a new AutoQA pipeline run."""
	try:
		target_path = request_data.get("target_path", ".")
		prompts_path = request_data.get("prompts_path", "data/sample_prompts.json")
		model = request_data.get("model", "ollama/qwen2.5-coder:7b")
		
		# Generate run ID
		run_id = str(uuid.uuid4())
		
		# Build command
		cmd = [
			sys.executable,
			str(PROJECT_ROOT / "src" / "autoqa" / "cli.py"),
			"run",
			"--target",
			target_path,
			"--prompts",
			prompts_path,
		]
		
		# Start subprocess in background
		process = subprocess.Popen(
			cmd,
			cwd=str(PROJECT_ROOT),
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
		)
		
		# Store process info
		_running_processes[run_id] = {
			"process": process,
			"start_time": datetime.utcnow().isoformat(),
			"status": "running",
			"step": "initialization",
			"progress": 0,
		}
		
		return {
			"status": "started",
			"run_id": run_id,
			"message": f"AutoQA pipeline started with ID {run_id}",
		}
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/run-status/{run_id}")
async def run_status(run_id: str) -> dict[str, Any]:
	"""Get the status of a running pipeline."""
	if run_id not in _running_processes:
		raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
	
	run_info = _running_processes[run_id]
	process = run_info["process"]
	
	# Check if process is still running
	if process.poll() is None:
		# Still running
		return {
			"status": "running",
			"run_id": run_id,
			"progress": run_info.get("progress", 0),
			"current_step": run_info.get("step", "processing"),
			"start_time": run_info.get("start_time"),
		}
	else:
		# Process finished
		return_code = process.returncode
		status = "completed" if return_code == 0 else "failed"
		
		# Update stored info
		run_info["status"] = status
		run_info["end_time"] = datetime.utcnow().isoformat()
		
		return {
			"status": status,
			"run_id": run_id,
			"progress": 100 if status == "completed" else 0,
			"current_step": "finished" if status == "completed" else "error",
			"start_time": run_info.get("start_time"),
			"end_time": run_info.get("end_time"),
			"return_code": return_code,
		}


# Helper functions

def _get_latest_file(directory: Path, pattern: str) -> Path | None:
	"""Get the latest file matching a pattern."""
	if not directory.exists():
		return None
	
	files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
	return files[0] if files else None


def _load_latest_json(pattern: str) -> dict[str, Any] | None:
	"""Load the latest JSON file matching a pattern."""
	latest_file = _get_latest_file(Path(config.DATA_DIR), pattern)
	
	if not latest_file:
		return None
	
	try:
		return json.loads(latest_file.read_text(encoding="utf-8"))
	except Exception:
		return None


def _calculate_health_score(pass_rate: float, hallucin_score: float, drift_score: float) -> int:
	"""Calculate overall health score from component scores.
	
	Args:
		pass_rate: 0-1 range
		hallucin_score: 0-1 range
		drift_score: 0-1 range (lower is better, so invert it)
	
	Returns:
		Health score 0-100
	"""
	# Formula: (pass_rate × 0.4) + (hallucin_score × 0.4) + ((1 - drift_score) × 0.2)
	health = (pass_rate * 0.4) + (hallucin_score * 0.4) + ((1.0 - drift_score) * 0.2)
	return int(round(health * 100))


if __name__ == "__main__":
	import uvicorn
	
	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=8000,
		reload=True,
	)
