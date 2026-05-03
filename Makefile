# AutoQA Makefile

.PHONY: help install run dashboard test clean lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  run        Run the main AutoQA application"
	@echo "  dashboard  Start the dashboard"
	@echo "  test       Run all tests"
	@echo "  clean      Clean up generated files"
	@echo "  lint       Run linting"
	@echo "  format     Format code"

# Install dependencies
install:
	pip install -r requirements.txt

# Run the main application
run:
	python -m src.autoqa.cli

# Start the dashboard
dashboard:
	streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0

# Run tests
test:
	pytest tests/ -v --tb=short

# Clean up generated files
clean:
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf .pytest_cache/
	rm -rf data/*.json
	rm -rf reports/*.md
	rm -rf logs/*.log

# Run linting (if ruff is installed)
lint:
	ruff check .

# Format code (if ruff is installed)
format:
	ruff format .