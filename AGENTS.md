
# Repository Guidelines

## Project Structure & Module Organization

* `EviQAsys/backend/app`: FastAPI scaffold with `api`, `repositories`, `schemas`, and service layers (`services/qa_flow`, `services/retrieval`, `services/integrations`). Add concrete modules inside these folders to keep imports stable with the design docs in `docs/en`.
* `EviQAsys/frontend/src`: React skeleton split into `api`, `components`, and `pages`; place new views inside this layout to preserve routing clarity.
* `dependency/`: MinerU, OceanBase, DsPy, and embedding demos. Use them as reference implementations rather than shipping code.
* `docs/`: Authoritative architecture, roadmap, and data-model notes—update these alongside behavioural changes.
* `sample_data/` and `log/`: External mounts; read-only for contributors and never committed upstream.

## Build, Test, and Development Commands

* Backend: `conda activate quest`, add (or reuse) an entrypoint such as `EviQAsys/backend/app/main.py`, then run `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload` for local checks.
* Under normal circumstances, both the MinerU API and OceanBase services are confirmed to be available, so you do not need to perform additional connectivity tests.
* OceanBase demo: `python dependency/oceanBaseDemo/demo1_vector_exact_no_index.py` validates database connectivity.
* MinerU demo: `conda activate jzMinerUVllm && python dependency/minerUparseDemo/parse_pdf_minerU.py` to confirm parsing.
* Frontend: once a `package.json` exists under `EviQAsys/frontend`, execute `npm install` then `npm run dev` to integrate with backend endpoints.

## Coding Style & Naming Conventions

* Python: follow PEP 8, four-space indentation, `snake_case` modules, `PascalCase` classes, and type hints at service boundaries. Place repositories, orchestrators, and integrations inside their matching subpackages and expose top-level imports via `__init__.py`.
* React: use functional components with `PascalCase` filenames grouped by feature folder; colocate API clients in `src/api`.
* Secrets: store keys in environment variables or under `dependency/api_key/` (kept out of version control); never commit credentials or generated PDFs.

## Testing Guidelines

* **Do not use `pytest` or automated test runners.**
  All test scripts must be **standalone Python files** containing a `main()` function entrypoint, e.g.:

  ```python
  if __name__ == "__main__":
      main()
  ```

* **Do not use mock data.**
  Every test must operate on **real parsed outputs** produced by MinerU or actual database records (e.g., OceanBase).
  Fake or mock elements, documents, or embeddings are strictly disallowed.

* **Manual execution only.**
  All tests are intended to be run manually by contributors via the command line (e.g.,
  `python tests/test_indexer_manual.py`).
  No automation or continuous integration scripts should invoke these tests.

* **AI tools restriction.**
  AI coding assistants may perform **static syntax checks or code-style validation** only.
  They must **not** execute, simulate, or fabricate runtime results from these manual tests.

* Each test script should:

  1. Explicitly call the backend functions or services under test;
  2. Print meaningful console logs (status, counts, sample outputs);
  3. Use real parsed documents located under `sample_data/` or new user-provided PDFs;
  4. Exit gracefully without writing to the production database.

* For validation, users manually inspect the printed results and confirm logical consistency (e.g., number of parsed elements, embedding dimensions, retrieval accuracy).

## Commit & Pull Request Guidelines

* Keep commit subjects short (<60 characters), imperative, and scope-prefixed (e.g., `backend: add collections repo`); bilingual summaries remain welcome.
* Commit bodies should reference related docs/issues and note config changes or new dependencies.
* Pull requests must summarise behaviour changes, attach validation evidence (manual test logs, screenshots, or console traces), and include screenshots or logs for UI/API updates so reviewers can reproduce results inside the `quest` environment.
