# AutoQA

```
   ___   _ _   ___   ___    _    ___
  / _ \ / / | | \ \ / / |  / \  / _ \
 | | | / /| | | |\ V /| | / _ \| | | |
 | |_| / /_| |_| | | | |/ ___ \ |_| |
  \___/____|\___/ |_| |_/_/   \_\___/
```

AutoQA is an autonomous AI quality assurance platform that generates tests, detects hallucinations, monitors drift, and delivers operational reports.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Mac%20%7C%20Linux-lightgrey)](https://github.com/04-shreyas/AutoQA)

## What is AutoQA?

AutoQA is a multi-agent AI platform designed to automate software quality assurance for Python projects. It combines code analysis, test generation, model evaluation, hallucination detection, and drift monitoring into a single workflow with a React-based dashboard.

---

## Architecture

```
              +---------------------------+
              |      User / Project       |
              |  (Source code + prompts)  |
              +-------------+-------------+
                            |
                            v
                 +-------------------------+
                 |  Test Generation Engine  |
                 +-------------------------+
                 |  Analyzer Agent          |
                 |  Planner Agent           |
                 |  Generator Agent         |
                 |  Reviewer Agent          |
                 +-------------------------+
                            |
                            v
                Generated tests + test report
                            |
                            v
             +-------------------------------+
             |   Model Evaluation Engine      |
             +-------------------------------+
             |  Prompt Runner Agent           |
             |  Hallucination Detector Agent  |
             |  Drift Monitor Agent           |
             |  Report Writer Agent           |
             +-------------------------------+
                            |
                            v
             Evaluation metrics + health report
                            |
                            v
                 +-------------------------+
                 |     Dashboard + GUI     |
                 +-------------------------+
```

### Agent input/output flow

- `Analyzer Agent` receives the target project and source files, outputs a code analysis plan.
- `Planner Agent` consumes analysis results and prompt structure, outputs test generation plans.
- `Generator Agent` produces concrete test cases and pytest suites.
- `Reviewer Agent` validates test quality and readiness.
- `Prompt Runner Agent` executes model prompts through Ollama / Google AI Studio.
- `Hallucination Detector Agent` checks model outputs for factual errors.
- `Drift Monitor Agent` compares evaluation runs to detect concept drift.
- `Report Writer Agent` assembles results into reports and dashboard summaries.

---

## Features

-  🤖 **Multi-agent workflow** with dedicated test generation and evaluation agents
-  🧪 **Auto test generation** using AI-driven planning and code analysis
-  🔍 **Hallucination detection** for model output validation
-  📊 **Drift monitoring** to track evaluation behavior over time
-  🖥️ **Interactive dashboard** for results, metrics, and reports
-  📝 **Report generation** with health scoring and actionable findings
-  ⚡ **Multi-provider support** for Ollama and Google AI Studio
-  💻 **CLI-first developer experience** with reusable pipeline commands

---

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/04-shreyas/AutoQA.git
   ```
2. Install dependencies:
   ```bash
   cd autoqa && pip install -r requirements.txt
   ```
3. Run the pipeline:
   ```bash
   python src/autoqa/cli.py run --target ./myproject --prompts data/sample_prompts.json
   ```

---

## Usage

### CLI Commands

```bash
python src/autoqa/cli.py analyze --target ./myproject
```
- Runs the test generation engine against a Python project.

```bash
python src/autoqa/cli.py eval --prompts data/sample_prompts.json
```
- Runs the model evaluation engine using the specified prompt file.

```bash
python src/autoqa/cli.py run --target ./myproject --prompts data/sample_prompts.json
```
- Runs the full AutoQA pipeline: test generation, model evaluation, hallucination analysis, drift monitoring, and report output.

```bash
python src/autoqa/cli.py report
```
- Opens the latest generated report.

### Dashboard Usage

- Start the backend:
  ```bash
  cd dashboard/backend
  python main.py
  ```
- Start the frontend:
  ```bash
  cd dashboard/frontend
  npm run dev
  ```
- Open the dashboard in your browser at `http://localhost:5173`.
- Use the dashboard to view:
  - Overview metrics
  - Test results
  - Hallucination analysis
  - Drift monitoring
  - Run new evaluation jobs

### Configuration Options

Configure environment values in `.env` or create one from `.env.example`.

- `OLLAMA_BASE_URL` � Local Ollama endpoint for model execution
- `OLLAMA_MODEL` � Default model identifier (e.g. `qwen2.5-coder:7b`)
- `GOOGLE_API_KEY` � API key for Google AI Studio
- `REPORTS_DIR` � Report output directory
- `DATA_DIR` � Data and evaluation storage directory
- `MAX_RETRIES` � Retry limit for external requests
- `LOG_LEVEL` � Logging verbosity

---

## Project Structure

```
autoqa/
+-- agents/                  # Eight agent implementations
�   +-- test_generation/    # Analyzer, Planner, Generator, Reviewer
�   +-- model_eval/         # Prompt Runner, Hallucination Detector, Drift Monitor, Report Writer
+-- dashboard/               # Web dashboard code
�   +-- backend/            # FastAPI backend API
�   +-- frontend/           # React + Vite dashboard UI
+-- data/                    # Generated artifacts, evaluation inputs
+-- engine/                  # Orchestrator engines for each pipeline
+-- pipelines/               # High-level AutoQA pipeline definitions
+-- reports/                 # Generated markdown reports
+-- src/autoqa/              # Core application package
�   +-- cli.py              # CLI entrypoint
�   +-- config.py           # Configuration loader
�   +-- utils/              # Shared utilities and helpers
+-- tests/                   # Validation and unit tests
+-- requirements.txt        # Python dependencies
+-- .env.example            # Environment variable template
+-- README.md               # Project documentation
```

---

## How It Works

### Engine 1: Test Generation

AutoQA first analyzes the target Python project with the Test Generation Engine:

1. `Analyzer Agent` inspects source files and builds a code understanding map.
2. `Planner Agent` turns the analysis into a test generation plan.
3. `Generator Agent` produces pytest-compatible test cases.
4. `Reviewer Agent` validates and refines generated tests.

The output is a generated test suite and initial test metrics.

### Engine 2: Model Evaluation

The Model Evaluation Engine validates AI outputs and monitors model behavior:

1. `Prompt Runner Agent` sends prompts to the configured provider (Ollama or Google AI Studio).
2. `Hallucination Detector Agent` flags outputs that deviate from expected facts.
3. `Drift Monitor Agent` compares results against prior evaluations.
4. `Report Writer Agent` synthesizes findings into the final report.

### Report Generation

The final report includes:
- Generated test counts and pass rates
- Hallucination risk scores
- Drift metrics across runs
- Combined health score and recommended actions

Reports are written into `reports/` and can be opened with `python src/autoqa/cli.py report`.

---

## Tech Stack

- Python 3.11+
- Ollama (local LLM inference)
- FastAPI (backend API)
- React + Vite (frontend)
- Tailwind CSS (styling)
- Recharts (charts)
- Google AI Studio (cloud LLM)
- pytest (test validation)
- rich (CLI output)
- openai Python library (Ollama API calls)

---

## Configuration

Set the following environment variables in `.env`:

- `OLLAMA_BASE_URL` � Ollama API endpoint (default: `http://localhost:11434`)
- `OLLAMA_MODEL` � Model to use for code and prompt evaluation
- `GOOGLE_API_KEY` � Google AI Studio API key for cloud model access
- `REPORTS_DIR` � Directory for generated reports
- `DATA_DIR` � Directory for pipeline artifacts and stored data
- `MAX_RETRIES` � Retry count for external API calls
- `LOG_LEVEL` � Logging level (e.g. `INFO`, `DEBUG`)

---

## Contributing

We welcome contributions:

1. Fork the repository
2. Create a branch for your feature or bugfix
3. Write tests and update documentation
4. Open a pull request describing your changes

Please follow standard GitHub contribution practices and keep changes focused.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
