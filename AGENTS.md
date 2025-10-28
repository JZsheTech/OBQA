# Repository Guidelines

## Project Structure & Module Organization
- The FastAPI backend lives in `EviQAsys/app`; `api/` exposes routers, `core/` handles configuration, `crud/` wraps database access, `db/` configures SQLAlchemy, `schemas/` defines Pydantic models, and `main.py` is the ASGI entrypoint.
- Supporting assets sit in `docs/` (architecture notes and data models), `sample_data/` (PDF fixtures for MinerU parsing, dspy logging file and big dataset files), and `log/` (environment snapshots). Treat `dependency/` as integration demos for OceanBase, DSPy, and MinerU—do not import them from production code.
- Place new backend features under `EviQAsys/app` with a matching directory name, keep notebooks and large datasets out of git, and store throwaway experiments under `debug/` if they must be versioned.

## Build, Test, and Development Commands
- Create the backend environment once with `conda create -n quest python=3.10` and install the packages listed in `env_install.md`; start every session with `conda activate quest`.
- Run the API from `EviQAsys/` via `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`, ensuring OceanBase and MinerU services referenced in `.env` are reachable.
- Bring up local OceanBase with `docker run -p 2881:2881 -e OB_TENANT_PASSWORD=12345678 --name obstandalone oceanbase/oceanbase-ce:4.3.5-lts`, and launch MinerU’s parser service using `mineru-api --host 0.0.0.0 --port 8000` when PDF conversion is required.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation and type hints, as in `EviQAsys/app/core/config.py` and `EviQAsys/app/db/session.py`.
- Use snake_case for modules, functions, and SQLAlchemy tables, and PascalCase for Pydantic models and ORM classes under `schemas/` and `db/models.py`.
- Format and lint Python code with `ruff check EviQAsys/app --fix`; the configuration shipped in `testpy/dspy/pyproject.toml` defines the shared rule set.

## Testing Guidelines
- Pytest is the expected framework; execute current suites with `pytest testpy/dspy/tests` after activating `quest`.
- Add backend tests under a mirrored `tests/` tree (for example, `tests/api/test_documents.py`) using `test_*.py` naming, and rely on fixtures instead of hard-coded credentials.
- For database-dependent tests, target the OceanBase `test` tenant and drop temporary tables or vectors as part of teardown.

## Commit & Pull Request Guidelines
- Recent history favours compact, descriptive commit titles (e.g., `设计文档完善`); write the subject in imperative mood and add focused body text when extra context is useful.
- Before opening a PR, rebase on `main`, run linting, unit tests, and a smoke request against the running API, and note any environment or sample-data prerequisites in the description.
- Link issues, attach API responses or screenshots for user-facing updates, and call out changes to `.env` expectations so reviewers can reproduce the setup.

## Security & Configuration Tips
- Sensitive settings live in `.env` and are loaded through `app/core/config.py`; never commit real credentials or API keys.
- Prefer tenant-specific OceanBase accounts for experiments, and rotate passwords in both the environment file and the Docker run command together.
