from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


load_dotenv()


class Config:
	OLLAMA_BASE_URL: str
	OLLAMA_MODEL: str
	GOOGLE_API_KEY: str
	REPORTS_DIR: str
	DATA_DIR: str
	MAX_RETRIES: int
	LOG_LEVEL: str

	def __init__(self) -> None:
		self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
		self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
		self.REPORTS_DIR = os.getenv("REPORTS_DIR", "reports/")
		self.DATA_DIR = os.getenv("DATA_DIR", "data/")
		self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
		self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

	def validate(self) -> None:
		url = self.OLLAMA_BASE_URL.rstrip("/")
		try:
			requests.get(url, timeout=2)
		except requests.RequestException as exc:
			raise ConnectionError(f"Ollama not reachable at {url}") from exc

	def get_ollama_headers(self) -> dict[str, str]:
		return {
			"Content-Type": "application/json",
		}

	def get_google_headers(self) -> dict[str, str]:
		headers = {
			"Content-Type": "application/json",
		}
		if self.GOOGLE_API_KEY:
			headers["x-goog-api-key"] = self.GOOGLE_API_KEY
		return headers
