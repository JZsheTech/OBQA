# Service Interface Notes (Milestone 2)

## FastAPI Contracts
- Backend instantiated via `EviQAsys.backend.app.main:create_app`.
- Routes operate synchronously and currently return deterministic stub data to
  unblock frontend and repository development.
- Key endpoints:
  - `GET /collections/` → `CollectionListResponse`
  - `POST /collections/` → `CollectionResponse`
  - `POST /collections/{collection_id}/documents` → `DocumentResponse`
  - `POST /collections/{collection_id}/documents/{document_id}/index` → `IndexingResponse`
  - `POST /collections/{collection_id}/chats` → `ChatResponse`
  - `POST /chats/{chat_id}/turns` → `TurnResponse` including `[Evidence#no]` labels
  - `GET /chats/{chat_id}/turns/{turn_id}/evidence` → `EvidenceListResponse`

## MinerU Parsing Adapter
- Implemented at `EviQAsys.backend.app.services.integrations.mineru_client`.
- `MinerUClient.parse_pdf()` accepts `MinerUParseRequest` with `file_path`,
  `file_name`, and optional `collection_id`.
- Returns `MinerUParseResponse` comprised of a `doc_uuid`, `content_list` of
  `MinerUContentBlock`, and rendered `md_text`.
- Calls are blocking and expected to be awaited via standard FastAPI dependency
  injection in later milestones.

## OceanBase Adapter
- Implemented at `EviQAsys.backend.app.services.integrations.oceanbase_client`.
- `OceanBaseClient.execute()` takes raw SQL plus optional parameter dict and
  returns a typed `QueryResult` (`List[Dict[str, Any]]`).
- Adapter stays synchronous with minimal configuration (`dsn`, `username`,
  `password`) and leaves connection pooling decisions to future work.

Both adapters currently yield stubbed responses so interface consumers can be
wired up before live services are reachable.
