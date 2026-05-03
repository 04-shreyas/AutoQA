from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


class AutoQAPipeline:
	def __init__(self) -> None:
		self.logger = get_logger(self.__class__.__name__)
		self.test_engine = TestGenerationEngine()
		self.eval_engine = ModelEvalEngine()
		self.report_writer = ReportWriterAgent()

	def run(self, target_path: str, prompts_path: str, model_config: dict[str, Any]) -> dict[str, Any]:
		self.logger.info("Running Test Generation Engine...")
		test_results = self.test_engine.run(target_path)

		self.logger.info("Running Model Eval Engine...")
		eval_results = self.eval_engine.run(prompts_path, model_config)

		hallucination_results = self._load_json(eval_results["hallucination_summary"]["results_path"])
		drift_results = self._load_json(eval_results["drift_summary"]["results_path"])

		all_results = {
			"test_generation_results": test_results,
			"hallucination_results": hallucination_results,
			"drift_results": drift_results,
		}

		report_content = self.report_writer.generate(all_results)
		report_path = self.report_writer.save_report(report_content)

		return {
			"engine": "autoqa",
			"test_generation_results": test_results,
			"model_eval_results": eval_results,
			"report_path": report_path,
			"timestamp": datetime.utcnow().isoformat(),
		}

	def _load_json(self, path: str) -> dict[str, Any]:
		try:
			return json.loads(Path(path).read_text(encoding="utf-8"))
		except OSError:
			return {}
