# 🧠 EviQAsys Multimodal Paper QA System — Brief Specification

## 1. Directory Structure

```
EviQAsys/
├── app/
│   ├── api/        # FastAPI route layer
│   ├── core/       # Configuration & dependencies (.env)
│   ├── crud/       # OceanBase database operations
│   ├── db/         # SQLAlchemy initialization
│   ├── schemas/    # Pydantic models
│   └── agents/     # Retrieval / Answer / Memory Agents
│
├── dependency/     # External demos, not imported into the main system
├── debug/          # Debug scripts
├── docs/           # Design docs and RoadMap
└── sample_data/    # Sample data
```

> Core logic resides in `EviQAsys/app`;
> `dependency/` is used only for isolated experiments.

---

## 2. Environment & Execution

```bash
conda activate quest
cd EviQAsys
uvicorn app.main:app --reload --port 8068
```

Example `.env` file:

```
OCEANBASE_DSN="root@127.0.0.1:2881/paperqa"
MINERU_API="http://localhost:8000/file_parse"
LLM_API="http://localhost:11434/v1"
```

---

## 3. Code Conventions

| Category   | Rule                                                             |
| ---------- | ---------------------------------------------------------------- |
| Style      | Follow PEP8, use 4-space indentation                             |
| Naming     | Functions/variables: `snake_case`; Classes/Schemas: `PascalCase` |
| Formatting | Run `ruff check EviQAsys/app --fix`                              |
| Structure  | New modules go under `app/`; debugging scripts go under `debug/` |

---

## 4. Testing Workflow

| Test Type           | Tool                   | Command                            |
| ------------------- | ---------------------- | ---------------------------------- |
| API connectivity    | httpx / curl           | `python debug/test_api.py`         |
| Data consistency    | SQLAlchemy             | `python debug/test_db.py`          |
| End-to-end pipeline | FastAPI + MinerU + LLM | `bash debug/test_full_pipeline.sh` |

> Goal: **Upload → Parse → Index → QA → Highlight Evidence**

---

## 5. Security & Version Control

* Keep keys/configs in `.env`, never commit them.
* The main system must **not** import from `dependency/`.
* Commit messages start with a verb, e.g. `fix AnswerAgent retrieval`.
* Each commit should correspond to a self-contained feature.

---

## 6. Logging & Debugging

* All debug code goes under `debug/`.
* Add lightweight `logging.debug` statements in key Agents.
* Logs are stored in `log/` directory with timestamps and request summaries.

---

## 7. Workflow (Single-Developer Iteration)

1. Start OceanBase and MinerU
2. Activate environment and run FastAPI
3. Upload PDF → Ask question → View highlighted Evidence

---

## 8. Future Extensions

* Multi-turn memory and evidence reuse
* ReAct-based frontend with enhanced highlighting
---
