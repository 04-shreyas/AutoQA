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


class TestGeneratorAgent:
	"""Agent responsible for generating test code based on test plans."""

	def __init__(self) -> None:
		"""Initialize the TestGeneratorAgent with OpenAI client and logging."""
		self.logger = get_logger(self.__class__.__name__)
		self.client = OpenAI(
			base_url=f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1",
			api_key="ollama",
		)

	def generate(self, plan: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
		start_time = time.monotonic()
		generated: list[dict[str, Any]] = []
		failed: list[dict[str, Any]] = []

		for plan_item in plan.get("plans", []):
			function_name = plan_item.get("function_name", "")
			file_path = plan_item.get("file_path", "")
			test_type = (plan_item.get("test_type", "unit") or "unit").lower()
			function_source = self._get_function_source(file_path, function_name)

			prompt = (
				"Write complete pytest tests for this Python function:\n"
				f"{function_source}\n\n"
				"Test plan to follow:\n"
				f"{json.dumps(plan_item, indent=2)}\n\n"
				"Requirements:\n"
				"- Use pytest framework\n"
				"- Include fixtures if needed\n"
				"- Add descriptive docstrings to each test\n"
				"- Follow AAA pattern (Arrange, Act, Assert)\n"
				"- Handle edge cases listed in the plan\n"
				"- Import the function correctly\n"
				"Respond with only valid Python code, no explanation."
			)

			test_code = self._generate_for_function(prompt, function_name, file_path)
			if not test_code:
				failed.append(
					{
						"function_name": function_name,
						"file_path": file_path,
					}
				)
				continue

			generated.append(
				{
					"function_name": function_name,
					"file_path": file_path,
					"test_type": test_type,
					"code": test_code,
				}
			)

		generation_time = time.monotonic() - start_time

		return {
			"total_functions": len(plan.get("plans", [])),
			"successfully_generated": len(generated),
			"failed": len(failed),
			"generated": generated,
			"failed_functions": failed,
			"generation_time": generation_time,
		}

	def save_tests(self, results: dict[str, Any], output_dir: str) -> dict[str, Any]:
		tests_root = Path(output_dir) if output_dir else Path("tests")
		unit_dir = tests_root / "unit"
		integration_dir = tests_root / "integration"
		unit_dir.mkdir(parents=True, exist_ok=True)
		integration_dir.mkdir(parents=True, exist_ok=True)

		files_written: list[str] = []
		per_file: dict[tuple[str, str], list[dict[str, Any]]] = {}

		for item in results.get("generated", []):
			key = (item["file_path"], item["test_type"])
			per_file.setdefault(key, []).append(item)

		for (file_path, test_type), items in per_file.items():
			module_path = self._module_from_path(file_path)
			function_names = sorted({item["function_name"] for item in items})
			import_line = ""
			if module_path and function_names:
				import_line = f"from {module_path} import {', '.join(function_names)}"

			content_blocks = []
			for item in items:
				content_blocks.append(self._strip_leading_imports(item["code"]))
			combined_code = "\n\n".join(content_blocks).strip()

			file_name = f"test_{Path(file_path).stem}.py"
			target_dir = unit_dir if test_type != "integration" else integration_dir
			target_path = target_dir / file_name

			parts = []
			if import_line:
				parts.append(import_line)
			parts.append(combined_code)
			final_code = "\n\n".join(parts).rstrip() + "\n"

			target_path.write_text(final_code, encoding="utf-8")
			files_written.append(str(target_path))

		report = {
			"total_functions": results.get("total_functions", 0),
			"successfully_generated": results.get("successfully_generated", 0),
			"failed": results.get("failed", 0),
			"test_files": files_written,
			"generation_time": results.get("generation_time", 0.0),
		}

		return report

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

	def _generate_for_function(self, prompt: str, function_name: str, file_path: str) -> str:
		"""Generate test code for a specific function using the LLM."""
		for attempt in range(1, config.MAX_RETRIES + 1):
			try:
				response_text = self._call_ollama(prompt)
				code = self._extract_code(response_text)
				if self._validate_python(code):
					return code
			except Exception as exc:
				self.logger.warning(
					"Generation attempt %d failed for %s (%s): %s",
					attempt,
					function_name,
					file_path,
					exc,
				)
		return ""

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

	def _module_from_path(self, file_path: str) -> str:
		path = Path(file_path)
		try:
			relative = path.resolve().relative_to(SRC_ROOT.resolve())
		except ValueError:
			return ""
		parts = list(relative.parts)
		if not parts:
			return ""
		module_parts = parts
		if module_parts[-1].endswith(".py"):
			module_parts[-1] = module_parts[-1].replace(".py", "")
		if module_parts[-1] == "__init__":
			module_parts = module_parts[:-1]
		return ".".join([p for p in module_parts if p])

	def _strip_leading_imports(self, code: str) -> str:
		lines = code.splitlines()
		index = 0
		while index < len(lines):
			line = lines[index].strip()
			if not line:
				index += 1
				continue
			if line.startswith("import ") or line.startswith("from "):
				index += 1
				continue
			break
		return "\n".join(lines[index:]).strip()


def _load_latest_json(data_dir: Path, prefix: str) -> dict[str, Any] | None:
	if not data_dir.exists():
		return None

	json_files = sorted(data_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime)
	if not json_files:
		return None

	try:
		return json.loads(json_files[-1].read_text(encoding="utf-8"))
	except OSError:
		return None


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Generate tests from a test plan.")
	parser.add_argument(
		"--data-dir",
		default=config.DATA_DIR,
		help="Directory containing analysis and plan JSON files",
	)
	parser.add_argument(
		"--output-dir",
		default="tests",
		help="Directory to write tests into",
	)
	args = parser.parse_args()

	data_dir = Path(args.data_dir)
	analysis_data = _load_latest_json(data_dir, "analysis")
	plan_data = _load_latest_json(data_dir, "test_plan")
	if not analysis_data or not plan_data:
		print("Missing analysis or test plan JSON in data directory.")
		raise SystemExit(1)

	agent = TestGeneratorAgent()
	results = agent.generate(plan_data, analysis_data)
	report = agent.save_tests(results, args.output_dir)
	print(
		"Generated tests for "
		f"{report['successfully_generated']} functions "
		f"(failed: {report['failed']})."
	)
