from __future__ import annotations

import argparse
import ast
import json
import os
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


class CodeAnalyzerAgent:
	"""Agent responsible for analyzing Python codebases to extract structural information."""

	def __init__(self) -> None:
		"""Initialize the CodeAnalyzerAgent with logging."""
		self.logger = get_logger(self.__class__.__name__)

	def analyze(self, project_path: str) -> dict[str, Any]:
		project_root = Path(project_path).resolve()
		py_files = list(self._iter_py_files(project_root))
		test_index = self._build_test_index(project_root)

		total_functions = 0
		total_classes = 0
		files: list[dict[str, Any]] = []

		for file_path in py_files:
			try:
				file_info = self._analyze_file(file_path, test_index, project_root)
				total_functions += len(file_info["functions"])
				total_classes += len(file_info["classes"])
				files.append(file_info)
			except Exception as exc:
				self.logger.warning("Skipping %s: %s", file_path, exc)

		summary = (
			f"Scanned {len(py_files)} files with "
			f"{total_functions} functions and {total_classes} classes."
		)

		return {
			"project_path": str(project_root),
			"total_files": len(py_files),
			"total_functions": total_functions,
			"total_classes": total_classes,
			"files": files,
			"summary": summary,
		}

	def save_analysis(self, analysis: dict[str, Any], output_path: str) -> str:
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

		if output_path:
			output_target = Path(output_path)
		else:
			output_target = Path(config.DATA_DIR)

		if output_target.suffix.lower() != ".json":
			output_target.mkdir(parents=True, exist_ok=True)
			output_target = output_target / f"analysis_{timestamp}.json"
		else:
			output_target.parent.mkdir(parents=True, exist_ok=True)

		with output_target.open("w", encoding="utf-8") as handle:
			json.dump(analysis, handle, indent=2)

		self.logger.info("Saved analysis to %s", output_target)
		return str(output_target)

	def get_function_source(self, file_path: str, function_name: str) -> str:
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

	def _iter_py_files(self, project_root: Path) -> list[Path]:
		"""Iterate over all Python files in the project, skipping common directories."""
		skip_dirs = {
			"__pycache__", "venv", ".git", "node_modules",
			"dist", "build", ".pytest_cache", ".mypy_cache",
			".venv", "env", "dashboard"
		}
		results: list[Path] = []
		for root, dirs, files in os.walk(project_root):
			dirs[:] = [d for d in dirs if d not in skip_dirs]
			for filename in files:
				if filename.endswith(".py"):
					results.append(Path(root) / filename)
		return results

	def _build_test_index(self, project_root: Path) -> list[str]:
		"""Build an index of test file contents for test detection."""
		contents: list[str] = []
		for file_path in self._iter_py_files(project_root):
			name = file_path.name
			if name.startswith("test_") or name.endswith("_test.py") or "tests" in file_path.parts:
				try:
					contents.append(file_path.read_text(encoding="utf-8"))
				except OSError:
					self.logger.warning("Unable to read test file %s", file_path)
		return contents

	def _analyze_file(
		self,
		file_path: Path,
		test_index: list[str],
		project_root: Path,
	) -> dict[str, Any]:
		"""Analyze a single Python file and extract functions, classes, and imports."""
		source = file_path.read_text(encoding="utf-8")
		parsed = ast.parse(source)

		functions = []
		classes = []
		imports = []

		local_modules = self._get_local_modules(project_root)

		for node in parsed.body:
			if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
				functions.append(self._extract_function_info(node, test_index))
			elif isinstance(node, ast.ClassDef):
				classes.append(self._extract_class_info(node))
			elif isinstance(node, (ast.Import, ast.ImportFrom)):
				imports.extend(self._extract_import_info(node, local_modules))

		return {
			"path": str(file_path),
			"functions": functions,
			"classes": classes,
			"imports": imports,
		}

	def _extract_function_info(
		self,
		node: ast.FunctionDef | ast.AsyncFunctionDef,
		test_index: list[str],
	) -> dict[str, Any]:
		parameters = []
		for arg in node.args.args:
			parameters.append(
				{
					"name": arg.arg,
					"annotation": self._annotation_to_str(arg.annotation),
				}
			)

		return_type = self._annotation_to_str(node.returns)
		docstring = ast.get_docstring(node)
		complexity = self._calculate_complexity(node)
		has_tests = self._has_tests(node.name, test_index)

		return {
			"name": node.name,
			"parameters": parameters,
			"return_type": return_type,
			"docstring": docstring,
			"line": node.lineno,
			"complexity": complexity,
			"has_tests": has_tests,
		}

	def _extract_class_info(self, node: ast.ClassDef) -> dict[str, Any]:
		"""Extract information about a class definition."""
		bases = [self._annotation_to_str(base) for base in node.bases]
		methods = [
			item.name
			for item in node.body
			if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
		]

		return {
			"name": node.name,
			"bases": bases,
			"methods": methods,
			"docstring": ast.get_docstring(node),
			"line": node.lineno,
		}

	def _extract_import_info(
		self,
		node: ast.Import | ast.ImportFrom,
		local_modules: set[str],
	) -> list[dict[str, Any]]:
		"""Extract information about import statements."""
		imports: list[dict[str, Any]] = []

		if isinstance(node, ast.Import):
			for alias in node.names:
				module = alias.name
				imports.append(
					{
						"module": module,
						"names": [alias.asname or alias.name],
						"type": self._classify_import(module, local_modules),
					}
				)
		else:
			module = node.module or ""
			if node.level > 0:
				module = "." * node.level + module
			names = [alias.name for alias in node.names]
			imports.append(
				{
					"module": module,
					"names": names,
					"type": self._classify_import(module, local_modules, node.level),
				}
			)

		return imports

	def _annotation_to_str(self, annotation: ast.AST | None) -> str | None:
		"""Convert an AST annotation to a string representation."""
		if annotation is None:
			return None
		try:
			return ast.unparse(annotation)
		except Exception:
			return None

	def _calculate_complexity(self, node: ast.AST) -> int:
		"""Calculate the cyclomatic complexity of an AST node."""
		complexity_nodes = (
			ast.If,
			ast.For,
			ast.While,
			ast.Try,
			ast.With,
			ast.BoolOp,
			ast.ExceptHandler,
			ast.Match,
		)
		count = 1
		for child in ast.walk(node):
			if isinstance(child, complexity_nodes):
				count += 1
		return count

	def _has_tests(self, function_name: str, test_index: list[str]) -> bool:
		"""Check if a function has corresponding tests in the test index."""
		needle = f"test_{function_name}"
		return any(needle in content or function_name in content for content in test_index)

	def _get_local_modules(self, project_root: Path) -> set[str]:
		"""Get the set of local module names in the project."""
		modules: set[str] = set()
		for path in self._iter_py_files(project_root):
			try:
				relative = path.relative_to(project_root)
			except ValueError:
				continue
			parts = relative.parts
			if parts:
				modules.add(parts[0])
		return modules

	def _classify_import(
		self,
		module: str,
		local_modules: set[str],
		level: int = 0,
	) -> str:
		if level > 0 or module.startswith("."):
			return "local"
		root = module.split(".")[0]
		if root in local_modules:
			return "local"
		try:
			stdlib = getattr(__import__("sys"), "stdlib_module_names", set())
		except Exception:
			stdlib = set()
		if root in stdlib:
			return "standard"
		return "third_party"

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


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Analyze a Python project.")
	parser.add_argument("path", help="Path to the project to analyze")
	parser.add_argument(
		"--output",
		default=config.DATA_DIR,
		help="Output directory or JSON file for analysis",
	)
	args = parser.parse_args()

	agent = CodeAnalyzerAgent()
	analysis_result = agent.analyze(args.path)
	output_path = agent.save_analysis(analysis_result, args.output)
	print(analysis_result["summary"])
	print(f"Saved analysis to {output_path}")
