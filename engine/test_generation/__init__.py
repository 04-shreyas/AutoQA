from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from autoqa import config
from autoqa.utils.logger import get_logger
from agents.test_generation.analyzer_agent import CodeAnalyzerAgent
from agents.test_generation.generator_agent import TestGeneratorAgent
from agents.test_generation.planner_agent import TestPlannerAgent
from agents.test_generation.reviewer_agent import TestReviewerAgent


class TestGenerationEngine:
	def __init__(self) -> None:
		self.logger = get_logger(self.__class__.__name__)
		self.console = Console()
		self.analyzer = CodeAnalyzerAgent()
		self.planner = TestPlannerAgent()
		self.generator = TestGeneratorAgent()
		self.reviewer = TestReviewerAgent()

	def run(self, project_path: str) -> dict[str, Any]:
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

			progress.update(task_id, description="🔍 Analyzing codebase... [CodeAnalyzerAgent]")
			self.logger.info("Analyzing codebase...")
			start = time.monotonic()
			analysis = self.analyzer.analyze(project_path)
			self.analyzer.save_analysis(analysis, config.DATA_DIR)
			step_times["analyze"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Analyzing completed in {step_times['analyze']:.2f}s")

			progress.update(task_id, description="📋 Planning tests... [TestPlannerAgent]")
			self.logger.info("Planning tests...")
			start = time.monotonic()
			plan = self.planner.plan(analysis)
			self.planner.save_plan(plan, config.DATA_DIR)
			step_times["plan"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Planning completed in {step_times['plan']:.2f}s")

			progress.update(task_id, description="✍️ Generating tests... [TestGeneratorAgent]")
			self.logger.info("Generating tests...")
			start = time.monotonic()
			generation_results = self.generator.generate(plan, analysis)
			generation_report = self.generator.save_tests(generation_results, "tests")
			step_times["generate"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Generation completed in {step_times['generate']:.2f}s")

			progress.update(task_id, description="✅ Reviewing tests... [TestReviewerAgent]")
			self.logger.info("Reviewing tests...")
			start = time.monotonic()
			review_report = self.reviewer.review("tests")
			self.reviewer.save_report(review_report)
			step_times["review"] = time.monotonic() - start
			progress.advance(task_id)
			self.console.print(f"Review completed in {step_times['review']:.2f}s")

		analysis_summary = {
			"total_files": analysis.get("total_files", 0),
			"total_functions": analysis.get("total_functions", 0),
			"total_classes": analysis.get("total_classes", 0),
			"summary": analysis.get("summary", ""),
		}
		plan_summary = {
			"total_functions": plan.get("total_functions", 0),
			"high_priority": plan.get("high_priority", 0),
			"medium_priority": plan.get("medium_priority", 0),
			"low_priority": plan.get("low_priority", 0),
		}

		return {
			"engine": "test_generation",
			"project_path": str(Path(project_path).resolve()),
			"analysis_summary": analysis_summary,
			"test_plan_summary": plan_summary,
			"generation_summary": generation_report,
			"review_summary": review_report,
			"overall_pass_rate": review_report.get("pass_rate", 0.0),
			"timestamp": datetime.utcnow().isoformat(),
		}


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Run the AutoQA test generation engine.")
	parser.add_argument("--target", default=".", help="Target project directory")
	args = parser.parse_args()

	engine = TestGenerationEngine()
	result = engine.run(args.target)

	table = Table(title="Test Generation Summary")
	table.add_column("Metric")
	table.add_column("Value")
	table.add_row("Project", result["project_path"])
	table.add_row("Files", str(result["analysis_summary"]["total_files"]))
	table.add_row("Functions", str(result["analysis_summary"]["total_functions"]))
	table.add_row("Classes", str(result["analysis_summary"]["total_classes"]))
	table.add_row("Planned Tests", str(result["test_plan_summary"]["total_functions"]))
	table.add_row("Generated", str(result["generation_summary"]["successfully_generated"]))
	table.add_row("Failed", str(result["generation_summary"]["failed"]))
	table.add_row("Pass Rate", f"{result['overall_pass_rate']:.2%}")
	table.add_row("Timestamp", result["timestamp"])

	engine.console.print(table)
