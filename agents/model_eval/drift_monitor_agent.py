from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from autoqa import config
from autoqa.utils.logger import get_logger


class DriftMonitorAgent:
	def __init__(self) -> None:
		self.logger = get_logger(self.__class__.__name__)

	def compare(self, run_1_path: str, run_2_path: str) -> dict[str, Any]:
		"""Compare two runs and detect drift."""
		data_1 = self._load_run(Path(run_1_path))
		data_2 = self._load_run(Path(run_2_path))
		if not data_1 or not data_2:
			return self._baseline_report()

		results_1 = {item.get("id"): item for item in data_1.get("results", [])}
		results_2 = {item.get("id"): item for item in data_2.get("results", [])}
		shared_ids = [pid for pid in results_1.keys() if pid in results_2]

		comparisons: list[dict[str, Any]] = []
		score_changes: list[float] = []
		latency_changes: list[float] = []
		similarity_scores: list[float] = []
		regression_count = 0
		improvement_count = 0

		for pid in shared_ids:
			item_1 = results_1[pid]
			item_2 = results_2[pid]
			score_1 = int(item_1.get("scores", {}).get("overall_score", 0))
			score_2 = int(item_2.get("scores", {}).get("overall_score", 0))
			lat_1 = float(item_1.get("latency_ms", 0.0))
			lat_2 = float(item_2.get("latency_ms", 0.0))
			response_1 = item_1.get("response", "")
			response_2 = item_2.get("response", "")
			similarity = SequenceMatcher(None, response_1, response_2).ratio()

			score_change = score_2 - score_1
			lat_change = lat_2 - lat_1

			if score_change < 0:
				regression_count += 1
			elif score_change > 0:
				improvement_count += 1

			score_changes.append(score_change)
			latency_changes.append(lat_change)
			similarity_scores.append(similarity)

			comparisons.append(
				{
					"id": pid,
					"prompt": item_2.get("prompt", item_1.get("prompt", "")),
					"score_run_1": score_1,
					"score_run_2": score_2,
					"score_change": score_change,
					"latency_run_1": lat_1,
					"latency_run_2": lat_2,
					"latency_change": lat_change,
					"response_length_run_1": len(response_1),
					"response_length_run_2": len(response_2),
					"similarity": similarity,
					"risk_run_1": item_1.get("scores", {}).get("risk_level", ""),
					"risk_run_2": item_2.get("scores", {}).get("risk_level", ""),
				}
			)

		metrics = {
			"score_drift": self._average_abs(score_changes),
			"latency_drift": self._average_abs(latency_changes),
			"consistency_drift": (1 - self._average(similarity_scores)) if similarity_scores else 0.0,
			"regression_count": regression_count,
			"improvement_count": improvement_count,
			"total_compared": len(shared_ids),
		}
		drift_score = self.calculate_drift_score(metrics)
		regressions = self.flag_regressions({"comparisons": comparisons})

		return {
			"baseline": False,
			"run_1": run_1_path,
			"run_2": run_2_path,
			"metrics": metrics,
			"drift_score": drift_score,
			"comparisons": comparisons,
			"regressions": regressions,
			"timestamp": datetime.utcnow().isoformat(),
		}

	def calculate_drift_score(self, metrics: dict[str, Any]) -> float:
		"""Calculate the overall drift score from metrics."""
		score_drift = float(metrics.get("score_drift", 0.0))
		consistency = float(metrics.get("consistency_drift", 0.0))
		latency_drift = float(metrics.get("latency_drift", 0.0))

		score_component = min(100.0, score_drift)
		consistency_component = min(100.0, consistency * 100)
		latency_component = min(100.0, latency_drift)

		return (score_component * 0.5) + (consistency_component * 0.3) + (latency_component * 0.2)

	def flag_regressions(self, comparison: dict[str, Any]) -> list[dict[str, Any]]:
		"""Flag regressions in the comparison data."""
		regressions = []
		for item in comparison.get("comparisons", []):
			score_drop = item["score_change"] < -10
			latency_increase = (
				item["latency_run_2"] > 0
				and (item["latency_run_2"] - item["latency_run_1"]) / max(item["latency_run_1"], 1) > 0.5
			)
			risk_jump = item.get("risk_run_1") == "LOW" and item.get("risk_run_2") == "HIGH"

			if score_drop or latency_increase or risk_jump:
				regressions.append(item)

		return regressions

	def save_report(self, report: dict[str, Any]) -> str:
		"""Save the drift report to a JSON file and return the path."""
		data_dir = Path(config.DATA_DIR)
		data_dir.mkdir(parents=True, exist_ok=True)
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
		output_path = data_dir / f"drift_{timestamp}.json"
		output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
		self.logger.info("Saved drift report to %s", output_path)
		return str(output_path)

	def _load_run(self, path: Path) -> dict[str, Any] | None:
		"""Load a run from the given path."""
		try:
			return json.loads(path.read_text(encoding="utf-8"))
		except OSError as exc:
			self.logger.warning("Unable to read %s: %s", path, exc)
			return None

	def _baseline_report(self) -> dict[str, Any]:
		"""Return a baseline report when not enough data is available."""
		return {
			"baseline": True,
			"message": "Not enough runs for drift analysis.",
			"timestamp": datetime.utcnow().isoformat(),
		}

	def _average(self, values: list[float]) -> float:
		"""Calculate the average of the given values."""
		return sum(values) / len(values) if values else 0.0

	def _average_abs(self, values: list[float]) -> float:
		"""Calculate the average of the absolute values."""
		return sum(abs(val) for val in values) / len(values) if values else 0.0


def _find_latest_runs(data_dir: Path) -> list[Path]:
	runs = sorted(data_dir.glob("hallucination_*.json"), key=lambda p: p.stat().st_mtime)
	return runs[-2:]


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Monitor drift between two runs.")
	parser.add_argument(
		"--data-dir",
		default=config.DATA_DIR,
		help="Directory containing hallucination JSON files",
	)
	args = parser.parse_args()

	data_dir = Path(args.data_dir)
	latest_runs = _find_latest_runs(data_dir)
	if len(latest_runs) < 2:
		report = DriftMonitorAgent()._baseline_report()
		console = Console()
		console.print(report["message"])
		raise SystemExit(0)

	agent = DriftMonitorAgent()
	report = agent.compare(str(latest_runs[0]), str(latest_runs[1]))
	agent.save_report(report)

	console = Console()
	metrics = report.get("metrics", {})
	console.print(f"Drift score: {report.get('drift_score', 0.0):.2f}")
	console.print(f"Score drift: {metrics.get('score_drift', 0.0):.2f}")
	console.print(f"Latency drift: {metrics.get('latency_drift', 0.0):.2f}")
	console.print(f"Consistency drift: {metrics.get('consistency_drift', 0.0):.2f}")

	regressions = report.get("regressions", [])
	if regressions:
		table = Table(title="Regressions", show_lines=True)
		table.add_column("ID")
		table.add_column("Score Δ")
		table.add_column("Latency Δ")
		table.add_column("Risk")
		for item in regressions:
			table.add_row(
				item.get("id", ""),
				str(item.get("score_change", "")),
				f"{item.get('latency_change', 0.0):.2f}",
				f"{item.get('risk_run_1', '')}->{item.get('risk_run_2', '')}",
				style="red",
			)
		console.print(table)
