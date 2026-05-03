from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from autoqa import config
from autoqa.utils.logger import get_logger
from agents.model_eval.drift_monitor_agent import DriftMonitorAgent
from agents.model_eval.hallucination_detector_agent import HallucinationDetectorAgent
from agents.model_eval.prompt_runner_agent import PromptRunnerAgent
from agents.model_eval.report_writer_agent import ReportWriterAgent


class ModelEvalEngine:
	def __init__(self) -> None:
		self.logger = get_logger(self.__class__.__name__)
		self.console = Console()
		self.runner = PromptRunnerAgent()
		self.detector = HallucinationDetectorAgent()
		self.drift_monitor = DriftMonitorAgent()
		self.report_writer = ReportWriterAgent()

	def run(self, prompts_path: str, model_config: dict[str, Any]) -> dict[str, Any]:
		step_times: dict[str, float] = {}
		with Progress(
			SpinnerColumn(),
			TextColumn("{task.description}"),
			BarColumn(),
			TimeElapsedColumn(),
			console=self.console,
			transient=True,
		) as progress:
			task_id = progress.add_task("Starting...", total=4)

			progress.update(task_id, description="🚀 Running prompts... [PromptRunnerAgent]")
			self.logger.info("Running prompts...")
			start = time.monotonic()
			prompts = self._load_prompts(Path(prompts_path))
			run_results = self.runner.run(prompts, model_config)
			run_path = self.runner.save_results(run_results)
			step_times["run"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Prompt run completed in {step_times['run']:.2f}s")

			progress.update(task_id, description="🔍 Detecting hallucinations... [HallucinationDetectorAgent]")
			self.logger.info("Detecting hallucinations...")
			start = time.monotonic()
			hallucination_results = self.detector.detect(run_results)
			hallucination_path = self.detector.save_results(hallucination_results)
			step_times["detect"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Hallucination detection completed in {step_times['detect']:.2f}s")

			progress.update(task_id, description="📊 Analyzing drift... [DriftMonitorAgent]")
			self.logger.info("Analyzing drift...")
			start = time.monotonic()
			drift_report = self._run_drift_analysis(hallucination_path)
			drift_path = self.drift_monitor.save_report(drift_report)
			step_times["drift"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Drift analysis completed in {step_times['drift']:.2f}s")

			progress.update(task_id, description="📝 Writing report... [ReportWriterAgent]")
			self.logger.info("Writing report...")
			start = time.monotonic()
			all_results = {
				"test_generation_results": {},
				"hallucination_results": hallucination_results,
				"drift_results": drift_report,
			}
			report_content = self.report_writer.generate(all_results)
			report_path = self.report_writer.save_report(report_content)
			step_times["report"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Report writing completed in {step_times['report']:.2f}s")

		return {
			"engine": "model_eval",
			"model_config": model_config,
			"run_summary": {
				"results_path": run_path,
				"total_prompts": run_results.get("total_prompts", 0),
				"avg_latency": run_results.get("avg_latency", 0.0),
			},
			"hallucination_summary": {
				"results_path": hallucination_path,
				"avg_score": hallucination_results.get("statistics", {})
				.get("average_scores", {})
				.get("overall_score", 0.0),
			},
			"drift_summary": {
				"results_path": drift_path,
				"drift_score": drift_report.get("drift_score", 0.0),
			},
			"report_path": report_path,
			"timestamp": datetime.utcnow().isoformat(),
		}

	def _load_prompts(self, path: Path) -> list[dict[str, Any]]:
		try:
			return json.loads(path.read_text(encoding="utf-8"))
		except OSError:
			return []

	def _run_drift_analysis(self, current_path: str) -> dict[str, Any]:
		data_dir = Path(config.DATA_DIR)
		previous = self._find_previous_hallucination_file(data_dir, Path(current_path))
		if not previous:
			return self.drift_monitor._baseline_report()
		return self.drift_monitor.compare(str(previous), current_path)

	def _find_previous_hallucination_file(self, data_dir: Path, current: Path) -> Path | None:
		files = sorted(data_dir.glob("hallucination_*.json"), key=lambda p: p.stat().st_mtime)
		files = [path for path in files if path.resolve() != current.resolve()]
		return files[-1] if files else None


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Run the AutoQA model evaluation pipeline.")
	parser.add_argument(
		"--prompts",
		default=str(PROJECT_ROOT / "data" / "sample_prompts.json"),
		help="Path to prompts JSON",
	)
	parser.add_argument(
		"--model",
		default=f"ollama/{config.OLLAMA_MODEL}",
		help="Model in provider/model format",
	)
	parser.add_argument("--temperature", type=float, default=0.2)
	args = parser.parse_args()

	provider, _, model_name = args.model.partition("/")
	model_config = {
		"provider": provider if provider else "ollama",
		"model": model_name or config.OLLAMA_MODEL,
		"temperature": args.temperature,
	}

	engine = ModelEvalEngine()
	result = engine.run(args.prompts, model_config)

	console = Console()
	table = Table(title="Model Eval Summary")
	table.add_column("Metric")
	table.add_column("Value")
	table.add_row("Run Results", result["run_summary"]["results_path"])
	table.add_row("Hallucination", result["hallucination_summary"]["results_path"])
	table.add_row("Drift", result["drift_summary"]["results_path"])
	table.add_row("Report", result["report_path"])
	console.print(table)
