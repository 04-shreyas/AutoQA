from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from openai import OpenAI

from autoqa import config
from autoqa.utils.logger import get_logger


class TestReviewerAgent:
	"""Agent responsible for reviewing and fixing generated tests."""

	def __init__(self) -> None:
		"""Initialize the TestReviewerAgent with OpenAI client and logging."""
		self.logger = get_logger(self.__class__.__name__)
		self.client = OpenAI(
			base_url=f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1",
			api_key="ollama",
		)

	def review(self, test_dir: str) -> dict[str, Any]:
		data_dir = Path(config.DATA_DIR)
		data_dir.mkdir(parents=True, exist_ok=True)
		report_path = data_dir / "pytest_report.json"

		fixed_total = 0
		last_report: dict[str, Any] = {}
		for attempt in range(1, config.MAX_RETRIES + 1):
			result = self._run_pytest(test_dir, report_path)
			last_report = self._load_report(report_path)
			failing = self._get_failing_tests(last_report)

			if not failing:
				break

			before_failures = {item["nodeid"] for item in failing}
			for item in failing:
				self._attempt_fix(item)

			result = self._run_pytest(test_dir, report_path)
			last_report = self._load_report(report_path)
			after_failures = {item["nodeid"] for item in self._get_failing_tests(last_report)}
			fixed_total += len(before_failures - after_failures)
			if not after_failures:
				break

		return self._build_report(last_report, fixed_total)

	def _run_pytest(self, test_dir: str, report_path: Path) -> subprocess.CompletedProcess[str]:
		"""Run pytest on the test directory and generate a JSON report."""
		command = [
			sys.executable,
			"-m",
			"pytest",
			test_dir,
			"--json-report",
			f"--json-report-file={report_path}",
			"-v",
		]
		self.logger.info("Running pytest on %s", test_dir)
		return subprocess.run(command, capture_output=True, text=True, check=False)

	def _load_report(self, report_path: Path) -> dict[str, Any]:
		"""Load the pytest JSON report from file."""
		try:
			return json.loads(report_path.read_text(encoding="utf-8"))
		except OSError as exc:
			self.logger.warning("Unable to read pytest report: %s", exc)
			return {}

	def _get_failing_tests(self, report: dict[str, Any]) -> list[dict[str, Any]]:
		"""Extract the list of failing tests from the pytest report."""
		tests = report.get("tests", [])
		failing = []
		for test in tests:
			if test.get("outcome") == "failed":
				failing.append(test)
		return failing

	def _attempt_fix(self, test_entry: dict[str, Any]) -> None:
		"""Attempt to fix a failing test using the LLM."""
		nodeid = test_entry.get("nodeid", "")
		file_path = nodeid.split("::")[0] if nodeid else ""
		if not file_path:
			return

		error = self._extract_error(test_entry)
		test_code = self._read_file(file_path)
		if not test_code:
			return

		fixed_code = self._fix_test(test_code, error)
		fixed_code = self._extract_code(fixed_code)
		if fixed_code and self._validate_python(fixed_code):
			Path(file_path).write_text(fixed_code, encoding="utf-8")
			self.logger.info("Updated test file %s", file_path)

	def _extract_error(self, test_entry: dict[str, Any]) -> str:
		call_info = test_entry.get("call", {})
		return call_info.get("longrepr", call_info.get("longreprtext", ""))

	def _read_file(self, file_path: str) -> str:
		try:
			return Path(file_path).read_text(encoding="utf-8")
		except OSError as exc:
			self.logger.warning("Unable to read %s: %s", file_path, exc)
			return ""

	def _fix_test(self, test_code: str, error: str) -> str:
		prompt = (
			"This pytest test is failing with this error:\n"
			f"{error}\n\n"
			"Here is the test code:\n"
			f"{test_code}\n\n"
			"Fix the test so it passes. Return only valid "
			"Python code, no explanation."
		)
		return self._call_ollama(prompt)

	def save_report(self, report: dict[str, Any]) -> str:
		data_dir = Path(config.DATA_DIR)
		data_dir.mkdir(parents=True, exist_ok=True)
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
		output_path = data_dir / f"review_report_{timestamp}.json"
		output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
		self.logger.info("Saved review report to %s", output_path)
		return str(output_path)

	def _call_ollama(self, prompt: str) -> str:
		"""Call the Ollama model with the given prompt and return the response."""
		last_error: Exception | None = None
		for attempt in range(1, config.MAX_RETRIES + 1):
			start_time = time.monotonic()
			try:
				response = self.client.chat.completions.create(
					model=config.OLLAMA_MODEL,
					messages=[{"role": "user", "content": prompt}],
					temperature=0.2,
				)
				duration = time.monotonic() - start_time
				self.logger.info("Ollama call %d took %.2fs", attempt, duration)
				return response.choices[0].message.content or ""
			except Exception as exc:
				duration = time.monotonic() - start_time
				self.logger.warning("Ollama call %d failed after %.2fs: %s", attempt, duration, exc)
				last_error = exc

		raise RuntimeError("Ollama call failed") from last_error

	def _validate_python(self, code: str) -> bool:
		"""Validate that the given code is valid Python syntax."""
		try:
			ast.parse(code)
			return True
		except SyntaxError:
			return False

	def _extract_code(self, response: str) -> str:
		"""Extract code from a markdown code block in the response."""
		text = response.strip()
		if text.startswith("```"):
			lines = text.splitlines()
			if lines and lines[0].startswith("```"):
				lines = lines[1:]
			if lines and lines[-1].startswith("```"):
				lines = lines[:-1]
			text = "\n".join(lines).strip()
		return text

	def _build_report(self, report: dict[str, Any], fixed: int) -> dict[str, Any]:
		"""Build a summary report from the pytest results."""
		summary = report.get("summary", {})
		total = summary.get("total", 0)
		passed = summary.get("passed", 0)
		failed = summary.get("failed", 0)
		pass_rate = (passed / total) if total else 0.0
		return {
			"total_tests": total,
			"passed": passed,
			"failed": failed,
			"fixed": fixed,
			"pass_rate": pass_rate,
			"test_results": report.get("tests", []),
			"timestamp": datetime.utcnow().isoformat(),
		}


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Review and fix generated tests.")
	parser.add_argument(
		"--test-dir",
		default="tests",
		help="Directory containing generated tests",
	)
	args = parser.parse_args()

	agent = TestReviewerAgent()
	review_report = agent.review(args.test_dir)
	agent.save_report(review_report)
	print(f"Pass rate: {review_report['pass_rate']:.2%}")
