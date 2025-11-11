# M1 Pre-flight Check — Contradictions and Unclear Points

This note surfaces high‑impact inconsistencies and ambiguities that affect system behavior, interfaces, and data integrity. It is intentionally high level to steer decisions before implementation.

## API Contract & Envelope
- Envelope mismatch: M1 shows `{"code":"OK","data":...}` while `docs/en/backend_frontend_interactive_design.md` specifies `{ data, meta, error }`. Confirm the single canonical envelope for all endpoints starting in M1.
- Endpoint scope in M1: DoD only requires `GET /collections` (empty list), but plan also adds `POST/DELETE` stubs. Confirm whether to expose write endpoints in M1 or defer to M5 to avoid premature API surface commitment.

## Schema DDL Strategy
- Idempotency vs. safety: Should `schema.sql` be strictly additive (CREATE IF NOT EXISTS) or include destructive drops? Running at startup must never wipe data in future milestones.
- Database creation: M1 mentions `USE/CREATE DATABASE` “guard comments” using env vars. Comments cannot parameterize execution. Decide the real mechanism (e.g., read env in a Python initializer that issues `CREATE DATABASE IF NOT EXISTS <db>; USE <db>;`).
- Vector dimension: Data model doesn’t pin a dimension; demos use `VECTOR(64)`; M1 proposes a placeholder comment. Decide the actual default (e.g., 64) and whether to make it configurable (env `VECTOR_DIM`).
- Cascade rules: `docs/en/Data_Model.md` leaves cascade behavior “depending on business logic.” Decide ON DELETE actions for FKs (e.g., `documents.collection_id`, `elements.doc_id`, `turns.chat_id`, `turn2evidence.*`).
- ENUM feasibility: `elements.elem_type` is `ENUM('text','header','image','table','equation')`. Confirm OceanBase MySQL‑mode support and whether we prefer `VARCHAR` + CHECK for forward compatibility.
- Timestamps: Use of `DEFAULT CURRENT_TIMESTAMP` and whether to include `updated_at`/`ON UPDATE CURRENT_TIMESTAMP` across tables is unspecified. Confirm convention.

## Migration Trigger & Startup Behavior
- Dual migration paths: M1 proposes both a manual runner (execute `schema.sql`) and an app startup hook gated by `RUN_SCHEMA_MIGRATION`. Decide the single source of truth and trigger to avoid drift.
- Failure semantics: If OceanBase is unavailable at startup, should the API fail hard, skip migration, or retry? Define behavior to keep `/healthz` and non‑DB routes usable.

## Repository Layer & Naming
- File naming inconsistency: Roadmap lists `t2e_repo.py`; M1 uses `turn2evidence_repo.py`. Pick one canonical name (and table alias) to avoid import churn.
- Package exposure: Confirm we will re‑export repository classes via `EviQAsys/backend/app/repositories/__init__.py` and adopt consistent import paths in services.
- SQL builder helpers: M1 proposes helpers like `dict_to_insert`. Confirm whether repositories will remain raw SQL (no ORM) and the minimal helper surface to standardize across repos.

## Connection & Configuration
- Location: Plan places DB connection helper at `repositories/db.py`, but the scaffold also has `services/db_access/`. Choose one location to avoid split responsibility.
- DSN and charset: Examples use `charset=utf8mb4`. Confirm default charset/collation and whether to enforce at DB/table creation.
- Env var contract: Finalize names (`OB_HOST/PORT/USER/PASSWORD/DATABASE/TIMEOUT`, `VECTOR_DIM`, `RUN_SCHEMA_MIGRATION`) and their defaults. Clarify whether the code may create the database and with which credentials.

## Data Access Semantics
- Transactions and autocommit: DDL + multi‑statement script execution via SQLAlchemy requires clear handling (splitting statements vs. driver autocommit). Decide the execution strategy to ensure predictable migrations.
- Row mapping: Repos will return dict rows; schemas plan to allow “orm_mode‑like” behavior. Confirm Pydantic v2 configuration and the expected shape of dicts from repositories.

## Cross‑Doc Alignment
- Index names and placement: M1 references `idx_chat_turn`, `idx_turn_element` (bridge table). Confirm exact index definitions match `docs/en/Data_Model.md`.
- Unified schema principle: All collections share global tables. Confirm there is no per‑collection table creation anywhere in M1 scaffolding.

## Validation Scope (Manual Tests)
- Runtime environment: Tests require a real OceanBase instance. Confirm contributors can assume availability without additional connectivity checks (per root guidelines) and specify the minimal env vars to run the scripts.
- Test data hygiene: Confirm manual tests should create and clean up their own rows; migrations must not drop existing data.

## FastAPI Surface in M1
- Router structure: Confirm router mount path(s) (e.g., `/api` prefix or root) and CORS policy baseline for early endpoints.
- Empty state response: For `GET /collections`, confirm empty list `[]` is returned under the unified envelope, and whether pagination/sorting metadata is required now or deferred.

Please confirm or adjust the above to lock the M1 contract before implementation.

