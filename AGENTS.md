# Repository Guidelines

## Project Structure & Module Organization
- `EviQAsys/backend/app`: FastAPI scaffold with `api`, `repositories`, `schemas`, and service layers (`services/qa_flow`, `services/retrieval`, `services/integrations`). Add concrete modules inside these folders to keep imports stable with the design docs in `docs/en`.
- `EviQAsys/frontend/src`: React skeleton split into `api`, `components`, and `pages`; place new views inside this layout to preserve routing clarity.
- `dependency/`: MinerU, OceanBase, DsPy, and embedding demos. Use them as reference implementations rather than shipping code.
- `docs/`: Authoritative architecture, roadmap, and data-model notes—update these alongside behavioural changes.
- `sample_data/` and `log/`: External mounts; read-only for contributors and never committed upstream.

## Build, Test, and Development Commands
- Backend: `conda activate quest`, add (or reuse) an entrypoint such as `EviQAsys/backend/app/main.py`, then run `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload` for local checks.
- Under normal circumstances, both the MinerU API and OceanBase services are confirmed to be available, so you do not need to perform additional connectivity tests.
- OceanBase demo: `python dependency/oceanBaseDemo/demo1_vector_exact_no_index.py` validates database connectivity.
- MinerU demo: `conda activate jzMinerUVllm && python dependency/minerUparseDemo/parse_pdf_minerU.py` to confirm parsing.
- Frontend: once a `package.json` exists under `EviQAsys/frontend`, execute `npm install` then `npm run dev` to integrate with backend endpoints.

## Coding Style & Naming Conventions
- Python: follow PEP 8, four-space indentation, `snake_case` modules, `PascalCase` classes, and type hints at service boundaries. Place repositories, orchestrators, and integrations inside their matching subpackages and expose top-level imports via `__init__.py`.
- React: use functional components with `PascalCase` filenames grouped by feature folder; colocate API clients in `src/api`.
- Secrets: store keys in environment variables or under `dependency/api_key/` (kept out of version control); never commit credentials or generated PDFs.

## Testing Guidelines
- Use `pytest` for backend units/integration tests in `EviQAsys/backend/tests`, naming files `test_<module>.py`.
- Mock MinerU, OceanBase, and LLM adapters so test runs stay offline; exercise service pipelines and repository CRUD paths.
- For manual verification, follow the M6 acceptance script in `docs/en/Develop_Road_Map.md`, referencing `sample_data/` as a read-only fixture, and record outcomes in pull requests.

## Commit & Pull Request Guidelines
- Keep commit subjects short (<60 characters), imperative, and scope-prefixed (e.g., `backend: add collections repo`); bilingual summaries remain welcome.
- Commit bodies should reference related docs/issues and note config changes or new dependencies.
- Pull requests must summarise behaviour changes, attach validation evidence (`pytest`, `uvicorn`, demo scripts), and include screenshots or logs for UI/API updates so reviewers can reproduce results inside the `quest` environment.
