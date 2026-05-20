from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from openai import OpenAI

from autoqa import config
from autoqa.utils.logger import get_logger


class PromptRunnerAgent:
	"""Agent responsible for executing prompts against AI models."""

	def __init__(self) -> None:
		"""Initialize the PromptRunnerAgent with OpenAI client and logging."""
		self.logger = get_logger(self.__class__.__name__)
		self.client = OpenAI(
			base_url=f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1",
			api_key="ollama",
			timeout=120,
			max_retries=config.MAX_RETRIES,
		)

	def run(self, prompts: list[dict[str, Any]], model_config: dict[str, Any]) -> dict[str, Any]:
		results: list[dict[str, Any]] = []
		latencies: list[float] = []
		provider = model_config.get("provider", "ollama")

		total = len(prompts)
		for index, item in enumerate(prompts, start=1):
			prompt_text = item.get("prompt", "")
			prompt_id = item.get("id", "")
			self.logger.info("Running prompt %s/%s (%s)", index, total, prompt_id)
			start = time.monotonic()
			try:
				if provider == "google":
					response = self._call_google(prompt_text, model_config)
				else:
					response = self._call_ollama(prompt_text, model_config)
			except Exception as exc:
				self.logger.warning("Prompt %s failed: %s", prompt_id or index, exc)
				response = ""
			end = time.monotonic()
			latency_ms = (end - start) * 1000
			latencies.append(latency_ms)

			result = {
				"id": item.get("id", ""),
				"prompt": prompt_text,
				"response": response,
				"latency_ms": latency_ms,
				"token_count": self._estimate_tokens(prompt_text + response),
				"timestamp": datetime.utcnow().isoformat(),
			}
			results.append(result)

		avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
		return {
			"model_config": model_config,
			"total_prompts": len(prompts),
			"avg_latency": avg_latency,
			"results": results,
		}

	def _call_ollama(self, prompt: str, model_config: dict[str, Any]) -> str:
		"""Call the Ollama model with the given prompt and return the response."""
		response = self.client.chat.completions.create(
			model=model_config.get("model", config.OLLAMA_MODEL),
			messages=[{"role": "user", "content": prompt}],
			temperature=model_config.get("temperature", 0.2),
		)
		return response.choices[0].message.content or ""

	def _call_google(self, prompt: str, model_config: dict[str, Any]) -> str:
		"""Call the Google AI Studio model with the given prompt and return the response."""
		model = model_config.get("model", "gemini-2.0-flash")
		url = (
			"https://generativelanguage.googleapis.com/v1beta/"
			f"models/{model}:generateContent?key={config.GOOGLE_API_KEY}"
		)
		payload = {
			"contents": [
				{
					"parts": [
						{"text": prompt},
					]
				}
			],
			"generationConfig": {
				"temperature": model_config.get("temperature", 0.2),
			},
		}
		response = requests.post(url, json=payload, timeout=60)
		response.raise_for_status()
		data = response.json()
		candidates = data.get("candidates", [])
		if not candidates:
			return ""
		parts = candidates[0].get("content", {}).get("parts", [])
		if not parts:
			return ""
		return parts[0].get("text", "")

	def save_results(self, results: dict[str, Any]) -> str:
		data_dir = Path(config.DATA_DIR)
		data_dir.mkdir(parents=True, exist_ok=True)
		timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
		output_path = data_dir / f"run_{timestamp}.json"
		output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
		self.logger.info("Saved prompt run to %s", output_path)
		return str(output_path)

	def _estimate_tokens(self, text: str) -> int:
		"""Estimate the number of tokens in the given text."""
		return max(1, len(text.split()))


def _load_sample_prompts(path: Path) -> list[dict[str, Any]]:
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except OSError:
		return []


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Run prompts against a model.")
	parser.add_argument(
		"--provider",
		default="ollama",
		choices=["ollama", "google"],
		help="Model provider",
	)
	parser.add_argument("--model", default=config.OLLAMA_MODEL, help="Model name")
	parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
	args = parser.parse_args()

	sample_path = PROJECT_ROOT / "data" / "sample_prompts.json"
	prompts = _load_sample_prompts(sample_path)
	if not prompts:
		print("No sample prompts found.")
		raise SystemExit(1)

	agent = PromptRunnerAgent()
	model_config = {
		"provider": args.provider,
		"model": args.model,
		"temperature": args.temperature,
	}
	results = agent.run(prompts, model_config)
	agent.save_results(results)

	console = Console()
	table = Table(title="Prompt Run Results")
	table.add_column("ID")
	table.add_column("Latency (ms)")
	table.add_column("Tokens")
	for row in results["results"]:
		table.add_row(row["id"], f"{row['latency_ms']:.0f}", str(row["token_count"]))
	console.print(table)
