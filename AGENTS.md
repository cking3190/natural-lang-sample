# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python Streamlit ESG demo with a small, modular layout:
- `app.py`: Streamlit UI entrypoint (`streamlit run app.py`).
- `agent/`: query workflow, prompts, guardrails, and tool helpers.
- `data/`: constants, synthetic data generation, and schema registry helpers.
- `tests/`: unit/integration-style tests for parsing, guardrails, and data generation.
- `config.py`: environment-driven runtime configuration.
- `.env.example`: required local environment variables.

Keep new logic in `agent/` or `data/` (not in `app.py`) unless it is strictly UI code.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create and activate a virtual env.
- `pip install -r requirements.txt`: install dependencies.
- `streamlit run app.py`: run the app locally.
- `python -m unittest discover -s tests`: run the full test suite (currently 38 tests).

Use `.env.example` as the template before running the app:
`cp .env.example .env` and set `OPENAI_API_KEY` / MongoDB settings.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and clear type hints where practical.
- Use `snake_case` for functions/variables/modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep modules single-purpose (for example, guardrail checks stay in `agent/guardrails.py`).
- Prefer small pure functions for query/data transforms to keep tests straightforward.

## Testing Guidelines
- Framework: `unittest` (discoverable with `python -m unittest discover -s tests`).
- Test files should be named `test_*.py`; test classes should start with `Test`.
- Add tests for any guardrail, parsing, or schema logic change before opening a PR.
- For data/query changes, include both pass and fail-path assertions where possible.

## Commit & Pull Request Guidelines
No `.git` metadata is present in this workspace, so historical commit conventions cannot be derived here. Use this standard:
- Commit subject: imperative, concise, scoped (example: `guardrails: enforce index prefix validation`).
- PRs should include: summary, behavior impact, test evidence (`python -m unittest discover -s tests`), and UI screenshots for `app.py` changes.
- Link related issue/task IDs when available.

## Security & Configuration Tips
- Never commit `.env` or API keys.
- Keep `MAX_QUERY_TIME_MS` and `MAX_RESULT_LIMIT` aligned with guardrail expectations in `config.py`.
