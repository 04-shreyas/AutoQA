from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from autoqa import config
from autoqa.utils.logger import get_logger
from agents.model_eval.report_writer_agent import ReportWriterAgent
from engine.model_eval import ModelEvalEngine
from engine.test_generation import TestGenerationEngine
from pipelines import AutoQAPipeline


BANNER = "\n".join(
	[
		"╔═══════════════════════════════╗",
		"║  AutoQA — AI Quality Platform ║",
		"║  v1.0.0                       ║",
		"╚═══════════════════════════════╝",
	]
)


def _print_banner(console: Console) -> None:
	console.print(BANNER, style="bold cyan")


def _summary_table(metrics: dict[str, str]) -> Table:
	table = Table(show_header=True, header_style="bold magenta")
	table.add_column("Metric")
	table.add_column("Value")
	for key, value in metrics.items():
		table.add_row(key, value)
	return table


def _open_latest_report(console: Console) -> None:
	report_path = Path(config.REPORTS_DIR) / "latest_report.md"
	if not report_path.exists():
		console.print("No report found.", style="yellow")
		return

	try:
		os.startfile(report_path)
		console.print(f"Opened {report_path}")
	except OSError:
		console.print(f"Report path: {report_path}")


def _health_score(report_writer: ReportWriterAgent, combined: dict[str, Any]) -> int:
	return report_writer.calculate_health_score(combined)


def main() -> None:
	console = Console()
	logger = get_logger("AutoQA.CLI")
	_print_banner(console)

	parser = argparse.ArgumentParser(prog="autoqa")
	subparsers = parser.add_subparsers(dest="command")

	analyze_parser = subparsers.add_parser("analyze", help="Run test generation engine")
	analyze_parser.add_argument("--target", default=".", help="Target project path")

	eval_parser = subparsers.add_parser("eval", help="Run model eval engine")
	eval_parser.add_argument("--prompts", required=True, help="Path to prompts JSON")
	eval_parser.add_argument("--model", default=f"ollama/{config.OLLAMA_MODEL}")
	eval_parser.add_argument("--temperature", type=float, default=0.2)

	run_parser = subparsers.add_parser("run", help="Run full AutoQA pipeline")
	run_parser.add_argument("--target", default=".", help="Target project path")
	run_parser.add_argument("--prompts", required=True, help="Path to prompts JSON")
	run_parser.add_argument("--model", default=f"ollama/{config.OLLAMA_MODEL}")
	run_parser.add_argument("--temperature", type=float, default=0.2)

	subparsers.add_parser("report", help="Open latest report")

	args = parser.parse_args()
	if args.command is None:
		parser.print_help()
		return

	if args.command == "report":
		_open_latest_report(console)
		return

	report_writer = ReportWriterAgent()

	if args.command == "analyze":
		engine = TestGenerationEngine()
		result = engine.run(args.target)
		metrics = {
			"Tests Generated": str(result.get("generation_summary", {}).get("successfully_generated", 0)),
			"Pass Rate": f"{result.get('overall_pass_rate', 0.0) * 100:.0f}%",
		}
		console.print(_summary_table(metrics))
		return

	if args.command == "eval":
		provider, _, model_name = args.model.partition("/")
		model_config = {
			"provider": provider if provider else "ollama",
			"model": model_name or config.OLLAMA_MODEL,
			"temperature": args.temperature,
		}
		engine = ModelEvalEngine()
		result = engine.run(args.prompts, model_config)
		hallucination_score = result.get("hallucination_summary", {}).get("avg_score", 0.0)
		drift_score = result.get("drift_summary", {}).get("drift_score", 0.0)
		metrics = {
			"Halluc. Score": f"{hallucination_score:.0f}/100",
			"Drift Score": f"{drift_score:.0f}/100",
		}
		console.print(_summary_table(metrics))
		return

	if args.command == "run":
		provider, _, model_name = args.model.partition("/")
		model_config = {
			"provider": provider if provider else "ollama",
			"model": model_name or config.OLLAMA_MODEL,
			"temperature": args.temperature,
		}
		pipeline = AutoQAPipeline()
		result = pipeline.run(args.target, args.prompts, model_config)

		test_results = result.get("test_generation_results", {})
		hallucination_results = pipeline._load_json(
			result.get("model_eval_results", {}).get("hallucination_summary", {}).get("results_path", "")
		)
		drift_results = pipeline._load_json(
			result.get("model_eval_results", {}).get("drift_summary", {}).get("results_path", "")
		)
		combined = {
			"test_generation_results": test_results,
			"hallucination_results": hallucination_results,
			"drift_results": drift_results,
		}
		health = _health_score(report_writer, combined)

		halluc_score = (
			hallucination_results.get("statistics", {})
			.get("average_scores", {})
			.get("overall_score", 0.0)
		)
		metrics = {
			"Tests Generated": str(test_results.get("generation_summary", {}).get("successfully_generated", 0)),
			"Pass Rate": f"{test_results.get('overall_pass_rate', 0.0) * 100:.0f}%",
			"Halluc. Score": f"{halluc_score:.0f}/100",
			"Drift Score": f"{drift_results.get('drift_score', 0.0):.0f}/100",
			"Health Score": f"{health}/100",
		}
		console.print(_summary_table(metrics))
		console.print(f"Report: {result.get('report_path', '')}")
		return

	logger.warning("Unknown command")


if __name__ == "__main__":
	main()
