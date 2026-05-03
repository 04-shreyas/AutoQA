from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from autoqa import config
from autoqa.utils.logger import get_logger


class ReportWriterAgent:
	def __init__(self) -> None:
		self.logger = get_logger(self.__class__.__name__)

	def generate(self, all_results: dict[str, Any]) -> str:
		"""Generate a comprehensive report from all evaluation results."""
		timestamp = datetime.utcnow().isoformat()
		test_results = all_results.get("test_generation_results", {})
		hallucination_results = all_results.get("hallucination_results", {})
		drift_results = all_results.get("drift_results", {})

		health_score = self.calculate_health_score(all_results)

		pass_rate = float(test_results.get("review_summary", {}).get("pass_rate", 0.0))
		pass_chart = self.generate_ascii_chart({"pass_rate": pass_rate * 100})

		hallucination_stats = hallucination_results.get("statistics", {})
		avg_hallucination_score = hallucination_stats.get("average_scores", {}).get("overall_score", 0.0)
		risk_dist = hallucination_stats.get("risk_distribution", {})
		category_risk = hallucination_stats.get("category_risk", {})
		worst_responses = hallucination_stats.get("worst_responses", [])

		drift_score = drift_results.get("drift_score", 0.0)
		regressions = drift_results.get("regressions", [])
		improvements = drift_results.get("metrics", {}).get("improvement_count", 0)
		trend = self._trend_direction(drift_results)

		key_findings = self._build_key_findings(test_results, hallucination_results, drift_results)
		critical_issues = self._build_critical_issues(test_results, hallucination_results, drift_results)
		recommendations = self._build_recommendations(test_results, hallucination_results, drift_results)

		report_lines = [
			"# AutoQA Evaluation Report",
			f"Generated: {timestamp}",
			"",
			"## Executive Summary",
			f"- Overall health score: {health_score}",
			"- Key findings:",
		] + [f"  - {item}" for item in key_findings] + ["- Critical issues:"]

		if critical_issues:
			report_lines.extend([f"  - {item}" for item in critical_issues])
		else:
			report_lines.append("  - None detected")

		analysis_summary = test_results.get("analysis_summary", {})
		generation_summary = test_results.get("generation_summary", {})
		review_summary = test_results.get("review_summary", {})
		report_lines.extend(
			[
				"",
				"## Test Generation Results",
				f"- Total functions analyzed: {analysis_summary.get('total_functions', 0)}",
				f"- Tests generated: {generation_summary.get('successfully_generated', 0)}",
				"- Pass rate:",
				"```",
				pass_chart,
				"````",
				f"- Top failing tests: {self._top_failing_tests(review_summary)}",
			]
		)

		report_lines.extend(
			[
				"",
				"## Hallucination Analysis",
				f"- Average hallucination score: {avg_hallucination_score:.2f}",
				"- Risk distribution:",
				f"  - LOW: {risk_dist.get('LOW', 0)}",
				f"  - MEDIUM: {risk_dist.get('MEDIUM', 0)}",
				f"  - HIGH: {risk_dist.get('HIGH', 0)}",
				"- Score breakdown table per category:",
				self._category_table(category_risk),
				"- Top 5 flagged responses:",
			] + [f"  - {item.get('id', '')}: {item.get('scores', {}).get('overall_score', '')}" for item in worst_responses]
		)

		report_lines.extend(
			[
				"",
				"## Drift Analysis",
				f"- Overall drift score: {drift_score:.2f}",
				f"- Regressions detected: {len(regressions)}",
				f"- Improvements detected: {improvements}",
				f"- Trend direction: {trend}",
			]
		)

		report_lines.extend(
			[
				"",
				"## Recommendations",
			] + [f"- {item}" for item in recommendations]
		)

		report_lines.extend(
			[
				"",
				"## Raw Data",
				f"- Data directory: {config.DATA_DIR}",
			]
		)

		return "\n".join(report_lines)

	def calculate_health_score(self, all_results: dict[str, Any]) -> int:
		"""Calculate an overall health score from the results."""
		test_results = all_results.get("test_generation_results", {})
		hallucination_results = all_results.get("hallucination_results", {})
		drift_results = all_results.get("drift_results", {})

		pass_rate = float(test_results.get("review_summary", {}).get("pass_rate", 0.0)) * 100
		hallucination_score = float(
			hallucination_results.get("statistics", {}).get("average_scores", {}).get("overall_score", 0.0)
		)
		drift_score = float(drift_results.get("drift_score", 0.0))

		health = (pass_rate * 0.4) + (hallucination_score * 0.4) + (100 - drift_score) * 0.2
		return int(round(max(0.0, min(100.0, health))))

	def generate_ascii_chart(self, data: dict[str, float]) -> str:
		"""Generate an ASCII chart from the data."""
		lines = []
		for label, value in data.items():
			bar_length = int(max(0.0, min(100.0, value)) / 5)
			bar = "#" * bar_length
			lines.append(f"{label:12} | {bar} {value:.1f}")
		return "\n".join(lines)

	def save_report(self, report: str) -> str:
		"""Save the report to a file and return the path."""
		reports_dir = Path(config.REPORTS_DIR)
		reports_dir.mkdir(parents=True, exist_ok=True)
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
		path = reports_dir / f"{timestamp}_autoqa_report.md"
		path.write_text(report, encoding="utf-8")

		latest_path = reports_dir / "latest_report.md"
		latest_path.write_text(report, encoding="utf-8")

		self.logger.info("Saved report to %s", path)
		return str(path)

	def _build_key_findings(
		self,
		test_results: dict[str, Any],
		hallucination_results: dict[str, Any],
		drift_results: dict[str, Any],
	) -> list[str]:
		"""Build a list of key findings from the results."""
		findings = []
		pass_rate = float(test_results.get("review_summary", {}).get("pass_rate", 0.0)) * 100
		if pass_rate < 80:
			findings.append(f"Pass rate below target ({pass_rate:.1f}%).")
		else:
			findings.append(f"Pass rate healthy at {pass_rate:.1f}%.")

		avg_score = float(
			hallucination_results.get("statistics", {}).get("average_scores", {}).get("overall_score", 0.0)
		)
		findings.append(f"Average hallucination score: {avg_score:.1f}.")

		drift_score = float(drift_results.get("drift_score", 0.0))
		findings.append(f"Drift score: {drift_score:.1f}.")
		return findings[:3]

	def _build_critical_issues(
		self,
		test_results: dict[str, Any],
		hallucination_results: dict[str, Any],
		drift_results: dict[str, Any],
	) -> list[str]:
		"""Build a list of critical issues from the results."""
		issues = []
		pass_rate = float(test_results.get("review_summary", {}).get("pass_rate", 0.0)) * 100
		if pass_rate < 50:
			issues.append("Pass rate below 50%.")
		avg_score = float(
			hallucination_results.get("statistics", {}).get("average_scores", {}).get("overall_score", 0.0)
		)
		if avg_score and avg_score < 70:
			issues.append("Hallucination score below 70.")
		if drift_results.get("drift_score", 0.0) > 70:
			issues.append("High drift detected across runs.")
		return issues

	def _build_recommendations(
		self,
		test_results: dict[str, Any],
		hallucination_results: dict[str, Any],
		drift_results: dict[str, Any],
	) -> list[str]:
		"""Build a list of recommendations based on the results."""
		recs = []
		pass_rate = float(test_results.get("review_summary", {}).get("pass_rate", 0.0)) * 100
		if pass_rate < 90:
			recs.append("Review failing tests and improve generator prompts.")
		avg_score = float(
			hallucination_results.get("statistics", {}).get("average_scores", {}).get("overall_score", 0.0)
		)
		if avg_score and avg_score < 80:
			recs.append("Add stricter grounding and citations for factual prompts.")
		if drift_results.get("drift_score", 0.0) > 50:
			recs.append("Pin model versions or add regression tests for prompts.")
		if not recs:
			recs.append("Continue monitoring; current performance is stable.")
		return recs

	def _top_failing_tests(self, review_summary: dict[str, Any]) -> str:
		"""Get a summary of the top failing tests."""
		failed = review_summary.get("failed", 0)
		return "None" if failed == 0 else f"{failed} failing tests"

	def _category_table(self, category_risk: dict[str, float]) -> str:
		"""Generate a markdown table for category risks."""
		if not category_risk:
			return "No category data available."
		lines = ["| Category | Avg Score |", "| --- | --- |"]
		for category, score in category_risk.items():
			lines.append(f"| {category} | {score:.1f} |")
		return "\n".join(lines)

	def _trend_direction(self, drift_results: dict[str, Any]) -> str:
		"""Determine the trend direction from drift results."""
		drift_score = float(drift_results.get("drift_score", 0.0))
		if drift_score > 60:
			return "worse"
		if drift_score < 30:
			return "better"
		return "stable"


def _load_latest_file(data_dir: Path, prefix: str) -> dict[str, Any] | None:
	files = sorted(data_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime)
	if not files:
		return None
	try:
		return json.loads(files[-1].read_text(encoding="utf-8"))
	except OSError:
		return None


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Generate AutoQA evaluation report.")
	parser.add_argument(
		"--data-dir",
		default=config.DATA_DIR,
		help="Directory containing result JSON files",
	)
	args = parser.parse_args()

	data_dir = Path(args.data_dir)
	latest_review = _load_latest_file(data_dir, "review_report")
	latest_analysis = _load_latest_file(data_dir, "analysis")
	latest_plan = _load_latest_file(data_dir, "test_plan")
	latest_generation = {
		"analysis_summary": latest_analysis or {},
		"test_plan_summary": latest_plan or {},
		"generation_summary": {},
		"review_summary": latest_review or {},
	}
	latest_hallucination = _load_latest_file(data_dir, "hallucination") or {}
	latest_drift = _load_latest_file(data_dir, "drift") or {}

	all_results = {
		"test_generation_results": latest_generation,
		"hallucination_results": latest_hallucination,
		"drift_results": latest_drift,
	}

	agent = ReportWriterAgent()
	report = agent.generate(all_results)
	path = agent.save_report(report)

	print(f"Report saved to {path}")
	print("Executive Summary:")
	for line in report.splitlines()[3:10]:
		print(line)
