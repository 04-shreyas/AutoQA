from __future__ import annotations

import argparse
import ast
import json
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


class TestPlannerAgent:
	"""Agent responsible for planning test cases based on code analysis."""

	def __init__(self) -> None:
		"""Initialize the TestPlannerAgent with OpenAI client and logging."""
		self.logger = get_logger(self.__class__.__name__)
		self.client = OpenAI(
			base_url=f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1",
			api_key="ollama",
			timeout=120,
			max_retries=config.MAX_RETRIES,
		)

	def plan(self, analysis: dict[str, Any]) -> dict[str, Any]:
		plans: list[dict[str, Any]] = []
		high_priority = 0
		medium_priority = 0
		low_priority = 0

		for file_info in analysis.get("files", []):
			file_path = file_info.get("path", "")
			for func in file_info.get("functions", []):
				function_name = func.get("name", "")
				# Skip private functions (starting with _)
				if function_name.startswith("_"):
					continue
				function_code = self._get_function_source(file_path, function_name)
				prompt = (
					"Given this Python function:\n"
					f"{function_code}\n\n"
					"Generate a test plan. Respond with JSON in this exact format:\n"
					'{\n'
					'  "test_type": "unit" or "integration",\n'
					'  "test_cases": ["test case 1", "test case 2"],\n'
					'  "edge_cases": ["edge case 1", "edge case 2"],\n'
					'  "expected_inputs": ["input1", "input2"],\n'
					'  "expected_outputs": ["output1", "output2"],\n'
					'  "priority": "high", "medium", or "low"\n'
					'}\n'
					"Respond with JSON only, no extra text."
				)

				plan_data = self._plan_for_function(prompt, function_name, file_path)
				if not plan_data:
					continue

				priority = plan_data.get("priority", "medium").lower()
				if priority == "high":
					high_priority += 1
				elif priority == "low":
					low_priority += 1
				else:
					medium_priority += 1

				plans.append(
					{
						"function_name": function_name,
						"file_path": file_path,
						"test_type": plan_data.get("test_type", ""),
						"test_cases": plan_data.get("test_cases", []),
						"edge_cases": plan_data.get("edge_cases", []),
						"priority": priority,
						"expected_inputs": plan_data.get("expected_inputs", []),
						"expected_outputs": plan_data.get("expected_outputs", []),
					}
				)

		return {
			"total_functions": len(plans),
			"high_priority": high_priority,
			"medium_priority": medium_priority,
			"low_priority": low_priority,
			"plans": plans,
		}

	def save_plan(self, plan: dict[str, Any], output_path: str) -> str:
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

		if output_path:
			output_target = Path(output_path)
		else:
			output_target = Path(config.DATA_DIR)

		if output_target.suffix.lower() != ".json":
			output_target.mkdir(parents=True, exist_ok=True)
			output_target = output_target / f"test_plan_{timestamp}.json"
		else:
			output_target.parent.mkdir(parents=True, exist_ok=True)

		with output_target.open("w", encoding="utf-8") as handle:
			json.dump(plan, handle, indent=2)

		self.logger.info("Saved plan to %s", output_target)
		return str(output_target)

	def _call_ollama(self, prompt: str) -> str:
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

	def _plan_for_function(
		self,
		prompt: str,
		function_name: str,
		file_path: str,
	) -> dict[str, Any]:
		for attempt in range(1, config.MAX_RETRIES + 1):
			try:
				response_text = self._call_ollama(prompt)
				return self._parse_json_response(response_text)
			except Exception as exc:
				self.logger.warning(
					"Plan attempt %d failed for %s (%s): %s",
					attempt,
					function_name,
					file_path,
					exc,
				)
		self.logger.warning(
			"Falling back to minimal plan for %s (%s)",
			function_name,
			file_path,
		)
		return self._fallback_plan(function_name)

	def _fallback_plan(self, function_name: str) -> dict[str, Any]:
		"""Return a minimal plan when the model output cannot be parsed."""
		return {
			"test_type": "unit",
			"test_cases": [f"basic behavior for {function_name}"],
			"edge_cases": [],
			"expected_inputs": [],
			"expected_outputs": [],
			"priority": "medium",
		}

	def _parse_json_response(self, response_text: str) -> dict[str, Any]:
		response_text = response_text.strip()
		
		# Check for markdown code block
		if "```json" in response_text:
			start = response_text.find("```json") + 7
			end = response_text.find("```", start)
			if end != -1:
				json_str = response_text[start:end].strip()
				try:
					return json.loads(json_str)
				except json.JSONDecodeError as e:
					self.logger.warning("Failed to parse JSON from code block: %s", e)
					self.logger.debug("Raw response: %s", response_text)
					raise
		
		# Check for plain JSON
		if response_text.startswith("{"):
			try:
				return json.loads(response_text)
			except json.JSONDecodeError as e:
				self.logger.warning("Failed to parse plain JSON: %s", e)
				self.logger.debug("Raw response: %s", response_text)
				raise

		# Try to extract JSON between first { and last }
		start = response_text.find("{")
		end = response_text.rfind("}")
		if start != -1 and end != -1 and start < end:
			json_str = response_text[start : end + 1]
			try:
				return json.loads(json_str)
			except json.JSONDecodeError as e:
				self.logger.warning("Failed to parse extracted JSON: %s", e)
				self.logger.debug("Raw response: %s", response_text)
				raise

		self.logger.warning("No JSON object found in response")
		self.logger.debug("Raw response: %s", response_text)
		raise ValueError("No JSON object found in response")

	def _get_function_source(self, file_path: str, function_name: str) -> str:
		"""Extract the source code of a specific function from a file."""
		path = Path(file_path)
		try:
			source = path.read_text(encoding="utf-8")
		except OSError as exc:
			self.logger.warning("Unable to read %s: %s", file_path, exc)
			return ""

		try:
			parsed = ast.parse(source)
		except SyntaxError as exc:
			self.logger.warning("Unable to parse %s: %s", file_path, exc)
			return ""

		for node in ast.walk(parsed):
			if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
				return self._extract_source_segment(source, node)

		return ""

	def _extract_source_segment(self, source: str, node: ast.AST) -> str:
		"""Extract the source code segment corresponding to an AST node."""
		if hasattr(node, "lineno") and hasattr(node, "end_lineno") and node.end_lineno:
			lines = source.splitlines()
			start = node.lineno - 1
			end = node.end_lineno
			return "\n".join(lines[start:end])
		try:
			return ast.get_source_segment(source, node) or ""
		except Exception:
			return ""


def _load_latest_analysis(data_dir: Path) -> dict[str, Any] | None:
	if not data_dir.exists():
		return None

	analysis_files = sorted(data_dir.glob("analysis_*.json"), key=lambda p: p.stat().st_mtime)
	if not analysis_files:
		return None

	try:
		return json.loads(analysis_files[-1].read_text(encoding="utf-8"))
	except OSError:
		return None


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Plan tests from analysis output.")
	parser.add_argument(
		"--data-dir",
		default=config.DATA_DIR,
		help="Directory containing analysis JSON files",
	)
	args = parser.parse_args()

	data_dir = Path(args.data_dir)
	analysis_data = _load_latest_analysis(data_dir)
	if not analysis_data:
		print("No analysis JSON found in data directory.")
		raise SystemExit(1)

	agent = TestPlannerAgent()
	plan = agent.plan(analysis_data)
	agent.save_plan(plan, str(data_dir))
	print(
		"Planned tests for "
		f"{plan['total_functions']} functions "
		f"(high: {plan['high_priority']}, "
		f"medium: {plan['medium_priority']}, "
		f"low: {plan['low_priority']})."
	)
