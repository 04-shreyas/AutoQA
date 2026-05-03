from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from openai import OpenAI

from autoqa import config
from autoqa.utils.logger import get_logger


class HallucinationDetectorAgent:
	def __init__(self) -> None:
		self.logger = get_logger(self.__class__.__name__)
		self.client = OpenAI(
			base_url=f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1",
			api_key="ollama",
		)

	def detect(self, run_results: dict[str, Any]) -> dict[str, Any]:
		"""Detect hallucinations in the given run results by scoring each response."""
		scored: list[dict[str, Any]] = []
		for item in run_results.get("results", []):
			prompt = item.get("prompt", "")
			response = item.get("response", "")
			judge_prompt = (
				"You are an expert fact-checker and AI evaluator.\n"
				"Analyze this AI response for hallucinations:\n\n"
				f"Original Question: {prompt}\n"
				f"AI Response: {response}\n\n"
				"Score the response on these criteria (0-100 each):\n"
				"1. Factual Accuracy: Are the facts correct?\n"
				"2. Consistency: Is the response internally consistent?\n"
				"3. Confidence Calibration: Does confidence match accuracy?\n"
				"4. Completeness: Is the answer complete?\n\n"
				"Also provide:\n"
				"- Overall hallucination risk: LOW/MEDIUM/HIGH\n"
				"- Specific hallucinated claims if any\n"
				"- Reasoning for your scores\n\n"
				"Respond in JSON only with this structure:\n"
				"{\n"
				"  factual_accuracy: int,\n"
				"  consistency: int,\n"
				"  confidence_calibration: int,\n"
				"  completeness: int,\n"
				"  overall_score: int,\n"
				"  risk_level: str,\n"
				"  hallucinated_claims: list,\n"
				"  reasoning: str\n"
				"}"
			)

			judge_response = self._call_ollama(judge_prompt)
			score = self._parse_json_response(judge_response)
			overall_score = int(score.get("overall_score", 0))
			scored.append(
				{
					**item,
					"scores": score,
					"hallucination": overall_score < 70,
				}
			)

		statistics = self.get_statistics({"results": scored})
		return {
			"model_config": run_results.get("model_config", {}),
			"total_prompts": run_results.get("total_prompts", 0),
			"results": scored,
			"statistics": statistics,
		}

	def _call_ollama(self, prompt: str) -> str:
		"""Call the Ollama model with the given prompt and return the response."""
		response = self.client.chat.completions.create(
			model=config.OLLAMA_MODEL,
			messages=[{"role": "user", "content": prompt}],
			temperature=0.2,
		)
		return response.choices[0].message.content or ""

	def _parse_json_response(self, response_text: str) -> dict[str, Any]:
		"""Parse the JSON response from the model."""
		response_text = response_text.strip()
		if response_text.startswith("{"):
			return json.loads(response_text)

		start = response_text.find("{")
		end = response_text.rfind("}")
		if start != -1 and end != -1 and start < end:
			return json.loads(response_text[start : end + 1])

		raise ValueError("No JSON object found in judge response")

	def get_statistics(self, scored_results: dict[str, Any]) -> dict[str, Any]:
		"""Compute statistics from the scored results."""
		results = scored_results.get("results", [])
		if not results:
			return {
				"average_scores": {},
				"risk_distribution": {},
				"worst_responses": [],
				"category_risk": {},
			}

		avg_scores = {
			"factual_accuracy": 0.0,
			"consistency": 0.0,
			"confidence_calibration": 0.0,
			"completeness": 0.0,
			"overall_score": 0.0,
		}
		risk_distribution: dict[str, int] = {}
		category_scores: dict[str, list[int]] = {}

		for item in results:
			scores = item.get("scores", {})
			for key in avg_scores:
				avg_scores[key] += float(scores.get(key, 0))
			risk = scores.get("risk_level", "UNKNOWN")
			risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
			category = item.get("category", "uncategorized")
			category_scores.setdefault(category, []).append(int(scores.get("overall_score", 0)))

		count = len(results)
		for key in avg_scores:
			avg_scores[key] = avg_scores[key] / count

		category_risk = {
			category: (sum(scores) / len(scores)) if scores else 0.0
			for category, scores in category_scores.items()
		}

		worst = sorted(
			results,
			key=lambda item: int(item.get("scores", {}).get("overall_score", 0)),
		)[:5]

		return {
			"average_scores": avg_scores,
			"risk_distribution": risk_distribution,
			"worst_responses": worst,
			"category_risk": category_risk,
		}

	def save_results(self, results: dict[str, Any]) -> str:
		"""Save the results to a JSON file and return the path."""
		data_dir = Path(config.DATA_DIR)
		data_dir.mkdir(parents=True, exist_ok=True)
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
		output_path = data_dir / f"hallucination_{timestamp}.json"
		output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
		self.logger.info("Saved hallucination results to %s", output_path)
		return str(output_path)


def _load_latest_run(data_dir: Path) -> dict[str, Any] | None:
	if not data_dir.exists():
		return None
	files = sorted(data_dir.glob("run_*.json"), key=lambda p: p.stat().st_mtime)
	if not files:
		return None
	try:
		return json.loads(files[-1].read_text(encoding="utf-8"))
	except OSError:
		return None


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Detect hallucinations in prompt runs.")
	parser.add_argument(
		"--data-dir",
		default=config.DATA_DIR,
		help="Directory containing run JSON files",
	)
	args = parser.parse_args()

	run_data = _load_latest_run(Path(args.data_dir))
	if not run_data:
		print("No run results found in data directory.")
		raise SystemExit(1)

	agent = HallucinationDetectorAgent()
	results = agent.detect(run_data)
	agent.save_results(results)

	console = Console()
	flagged = [
		item for item in results.get("results", []) if item.get("hallucination")
	]
	if flagged:
		table = Table(title="Flagged Hallucinations")
		table.add_column("ID")
		table.add_column("Score")
		table.add_column("Risk")
		for item in flagged:
			scores = item.get("scores", {})
			table.add_row(
				item.get("id", ""),
				str(scores.get("overall_score", "")),
				str(scores.get("risk_level", "")),
			)
		console.print(table)

	stats = results.get("statistics", {})
	dist = stats.get("risk_distribution", {})
	if dist:
		console.print("Score distribution:")
		for key, value in dist.items():
			console.print(f"- {key}: {value}")
