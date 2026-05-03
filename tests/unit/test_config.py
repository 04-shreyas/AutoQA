import os
from unittest.mock import patch

import pytest
import requests

from src.autoqa.config import Config


class TestConfig:
    """Unit tests for Config class."""

    def test_init_defaults(self):
        """Test Config initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            assert config.OLLAMA_BASE_URL == "http://localhost:11434"
            assert config.OLLAMA_MODEL == "qwen2.5-coder:7b"
            assert config.GOOGLE_API_KEY == ""
            assert config.REPORTS_DIR == "reports/"
            assert config.DATA_DIR == "data/"
            assert config.MAX_RETRIES == 3
            assert config.LOG_LEVEL == "INFO"

    def test_init_with_env_vars(self):
        """Test Config initialization with environment variables."""
        env_vars = {
            "OLLAMA_BASE_URL": "http://custom:8080",
            "OLLAMA_MODEL": "custom-model",
            "GOOGLE_API_KEY": "test-key",
            "REPORTS_DIR": "/custom/reports",
            "DATA_DIR": "/custom/data",
            "MAX_RETRIES": "5",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            config = Config()

            assert config.OLLAMA_BASE_URL == "http://custom:8080"
            assert config.OLLAMA_MODEL == "custom-model"
            assert config.GOOGLE_API_KEY == "test-key"
            assert config.REPORTS_DIR == "/custom/reports"
            assert config.DATA_DIR == "/custom/data"
            assert config.MAX_RETRIES == 5
            assert config.LOG_LEVEL == "DEBUG"

    @patch("requests.get")
    def test_validate_success(self, mock_get):
        """Test validate method when Ollama is reachable."""
        mock_get.return_value.status_code = 200

        config = Config()
        config.validate()  # Should not raise

        mock_get.assert_called_once_with("http://localhost:11434", timeout=2)

    @patch("requests.get")
    def test_validate_failure(self, mock_get):
        """Test validate method when Ollama is not reachable."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        config = Config()

        with pytest.raises(ConnectionError, match="Ollama not reachable"):
            config.validate()

    def test_get_ollama_headers(self):
        """Test get_ollama_headers method."""
        config = Config()
        headers = config.get_ollama_headers()

        expected = {"Content-Type": "application/json"}
        assert headers == expected

    def test_get_google_headers_with_key(self):
        """Test get_google_headers method with API key."""
        config = Config()
        config.GOOGLE_API_KEY = "test-api-key"

        headers = config.get_google_headers()

        expected = {
            "Content-Type": "application/json",
            "x-goog-api-key": "test-api-key",
        }
        assert headers == expected

    def test_get_google_headers_without_key(self):
        """Test get_google_headers method without API key."""
        config = Config()
        config.GOOGLE_API_KEY = ""

        headers = config.get_google_headers()

        expected = {"Content-Type": "application/json"}
        assert headers == expected