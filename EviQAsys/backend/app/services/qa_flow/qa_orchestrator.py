from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Mapping

from ...env_setting import QAFlowSettings, get_qa_flow_settings
from ...repositories import (
    ChatsRepository,
    DocumentsRepository,
    ElementsRepository,
    Turn2ElementRepository,
    TurnsRepository,
)
from ..integrations import VisionVQAClient, VisionVQAError
from ..llm import AnswerComposer, ImageQuestionGenerator, QueryRewriter, RetrievalDecider
from ..mapping import evidence_mapper
from ..memory import MemoryService
from ..retrieval import ChunkRetrievalResult, Retriever
from .history_loader import format_history_text
from .models import EvidenceText, QATurnResult

logger = logging.getLogger(__name__)


class QAFlowError(RuntimeError):
    """Base class for QA orchestration errors."""


class ChatNotFoundError(QAFlowError):
    """Raised when chat metadata cannot be located."""


@dataclass
class QAFlowConfig:
    max_history_turns: int = 8
    text_evidence_limit: int = 8
    image_evidence_limit: int = 4
    enable_memory_summarizer: bool = False
    enable_image_vqa: bool = False
    retrieval_mode: str = "auto"
    search_mode: str = "hybrid"
    elem_types: tuple[str, ...] | None = ("text", "header", "table", "image")
    chunk_top_k: int = 8
    page_top_k: int = 3
    enable_page_filter: bool = False

    def __post_init__(self) -> None:
        self.max_history_turns = max(0, int(self.max_history_turns))
        self.text_evidence_limit = max(0, int(self.text_evidence_limit))
        self.image_evidence_limit = max(0, int(self.image_evidence_limit))
        self.enable_memory_summarizer = bool(self.enable_memory_summarizer)
        self.enable_image_vqa = bool(self.enable_image_vqa)
        self.retrieval_mode = self._normalize_retrieval_mode(self.retrieval_mode) or "auto"
        self.search_mode = self._normalize_search_mode(self.search_mode) or "hybrid"
        self.elem_types = self._normalize_elem_types(self.elem_types) or None
        self.chunk_top_k = max(1, int(self.chunk_top_k))
        self.page_top_k = max(1, int(self.page_top_k))
        self.enable_page_filter = bool(self.enable_page_filter)

    @classmethod
    def from_settings(cls, settings: QAFlowSettings | None = None) -> "QAFlowConfig":
        settings = settings or get_qa_flow_settings()
        return cls(
            max_history_turns=settings.max_history_turns,
            text_evidence_limit=settings.text_evidence_limit,
            image_evidence_limit=settings.image_evidence_limit,
            enable_memory_summarizer=settings.enable_memory_summarizer,
            enable_image_vqa=settings.enable_image_vqa,
            retrieval_mode=settings.default_retrieval_mode,
            search_mode=settings.default_search_mode,
            elem_types=settings.default_elem_types,
            chunk_top_k=settings.retrieval_topk_chunk,
            page_top_k=settings.retrieval_topk_page,
            enable_page_filter=settings.enable_page_chunk_retrieval,
        )

    def with_overrides(
        self,
        *,
        max_history_turns: int | None = None,
        text_evidence_limit: int | None = None,
        image_evidence_limit: int | None = None,
        enable_memory_summarizer: bool | None = None,
        enable_image_vqa: bool | None = None,
        retrieval_mode: str | None = None,
        search_mode: str | None = None,
        elem_types: Iterable[str] | None = None,
        chunk_top_k: int | None = None,
        page_top_k: int | None = None,
        enable_page_filter: bool | None = None,
    ) -> "QAFlowConfig":
        return QAFlowConfig(
            max_history_turns=self._normalize_int(max_history_turns, fallback=self.max_history_turns),
            text_evidence_limit=self._normalize_int(text_evidence_limit, fallback=self.text_evidence_limit),
            image_evidence_limit=self._normalize_int(image_evidence_limit, fallback=self.image_evidence_limit),
            enable_memory_summarizer=self._normalize_bool(enable_memory_summarizer, fallback=self.enable_memory_summarizer),
            enable_image_vqa=self._normalize_bool(enable_image_vqa, fallback=self.enable_image_vqa),
            retrieval_mode=self._normalize_retrieval_mode(retrieval_mode) or self.retrieval_mode,
            search_mode=self._normalize_search_mode(search_mode) or self.search_mode,
            elem_types=self._normalize_elem_types(elem_types) if elem_types is not None else self.elem_types,
            chunk_top_k=self._normalize_int(chunk_top_k, fallback=self.chunk_top_k, min_value=1),
            page_top_k=self._normalize_int(page_top_k, fallback=self.page_top_k, min_value=1),
            enable_page_filter=self._normalize_bool(enable_page_filter, fallback=self.enable_page_filter),
        )

    @staticmethod
    def _normalize_int(value: int | None, *, fallback: int, min_value: int = 0) -> int:
        if value is None:
            return max(min_value, fallback)
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return max(min_value, fallback)
        return max(min_value, numeric)

    @staticmethod
    def _normalize_bool(value: bool | None, *, fallback: bool) -> bool:
        if value is None:
            return bool(fallback)
        return bool(value)

    @staticmethod
    def _normalize_retrieval_mode(value: str | None) -> str | None:
        if not value:
            return None
        lowered = str(value).lower()
        if lowered in {"auto", "force", "skip"}:
            return lowered
        return None

    @staticmethod
    def _normalize_search_mode(value: str | None) -> str | None:
        if not value:
            return None
        lowered = str(value).lower()
        if lowered in {"vector", "fulltext", "hybrid"}:
            return lowered
        return None

    @staticmethod
    def _normalize_elem_types(elem_types: Iterable[str] | None) -> tuple[str, ...] | None:
        if not elem_types:
            return None
        normalized: list[str] = []
        for entry in elem_types:
            cleaned = str(entry or "").strip().lower()
            if not cleaned or cleaned in normalized:
                continue
            normalized.append(cleaned)
        return tuple(normalized) or None


class QAOrchestrator:
    """Coordinates memory, retrieval, DSPy programs, and persistence."""

    def __init__(
        self,
        *,
        chats_repo: ChatsRepository | None = None,
        documents_repo: DocumentsRepository | None = None,
        turns_repo: TurnsRepository | None = None,
        turn2element_repo: Turn2ElementRepository | None = None,
        elements_repo: ElementsRepository | None = None,
        retriever: Retriever | None = None,
        memory_service: MemoryService | None = None,
        retrieval_decider: RetrievalDecider | None = None,
        query_rewriter: QueryRewriter | None = None,
        answer_composer: AnswerComposer | None = None,
        image_question_generator: ImageQuestionGenerator | None = None,
        vision_client: VisionVQAClient | None = None,
        config: QAFlowConfig | None = None,
        qa_settings: QAFlowSettings | None = None,
    ) -> None:
        self._qa_settings = qa_settings or get_qa_flow_settings()
        self._chats_repo = chats_repo or ChatsRepository()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._turns_repo = turns_repo or TurnsRepository()
        self._turn2element_repo = turn2element_repo or Turn2ElementRepository()
        self._elements_repo = elements_repo or ElementsRepository()
        self._retriever = retriever or Retriever()
        self._memory_service = memory_service or MemoryService()
        base_config = config or QAFlowConfig.from_settings(self._qa_settings)
        self._retrieval_decider = retrieval_decider or RetrievalDecider(default_types=base_config.elem_types)
        self._query_rewriter = query_rewriter or QueryRewriter()
        self._answer_composer = answer_composer or AnswerComposer()
        self._image_question_generator = image_question_generator or ImageQuestionGenerator()
        self._vision_client = vision_client
        self._config = base_config

    def run(
        self,
        *,
        chat_id: int,
        question: str,
        top_k: int = 8,
        retrieval_mode: str | None = None,
        elem_types: Iterable[str] | None = None,
        search_mode: str | None = None,
        max_history_turns: int | None = None,
        enable_image_vqa: bool | None = None,
        enable_memory_summarizer: bool | None = None,
        text_evidence_limit: int | None = None,
        image_evidence_limit: int | None = None,
        enable_page_filter: bool | None = None,
        page_top_k: int | None = None,
    ) -> QATurnResult:
        question_text = (question or "").strip()
        if not question_text:
            raise QAFlowError("question must be provided.")
        chat = self._chats_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found.")
        collection_id, document_id = self._resolve_chat_scope(chat)
        history_turns = self._turns_repo.list_by_chat(chat_id)
        requested_elem_types = QAFlowConfig._normalize_elem_types(elem_types) if elem_types is not None else None
        config = self._config.with_overrides(
            max_history_turns=max_history_turns,
            text_evidence_limit=text_evidence_limit,
            image_evidence_limit=image_evidence_limit,
            enable_memory_summarizer=enable_memory_summarizer,
            enable_image_vqa=enable_image_vqa,
            retrieval_mode=retrieval_mode,
            search_mode=search_mode,
            elem_types=requested_elem_types if elem_types is not None else None,
            chunk_top_k=top_k,
            page_top_k=page_top_k,
            enable_page_filter=enable_page_filter,
        )
        history_text = format_history_text(history_turns, max_turns=config.max_history_turns)
        memory_summary = history_text
        if config.enable_memory_summarizer and history_text:
            memory_summary = self._memory_service.summarize_history(history_text)

        decision = None
        need_retrieve = False
        elem_types_for_retrieval = requested_elem_types or config.elem_types
        if config.retrieval_mode != "skip":
            decision = self._retrieval_decider.decide(question_text, memory_summary)
            if config.retrieval_mode == "force":
                need_retrieve = True
            else:
                need_retrieve = bool(decision.need_retrieve) if decision else False
            elem_types_for_retrieval = (
                requested_elem_types
                or (decision.element_types if decision else None)
                or config.elem_types
            )
        logger.info(
            "QAFlow: chat=%s mode=%s need_retrieve=%s search_mode=%s elem_types=%s",
            chat_id,
            config.retrieval_mode,
            need_retrieve,
            config.search_mode,
            elem_types_for_retrieval,
        )
        logger.info(
            "QAFlow limits: max_history=%s text_limit=%s image_limit=%s memory=%s vqa=%s",
            config.max_history_turns,
            config.text_evidence_limit,
            config.image_evidence_limit,
            config.enable_memory_summarizer,
            config.enable_image_vqa,
        )
        text_evidences: list[EvidenceText] = []
        image_candidates: list[dict[str, object]] = []
        chunk_results: list[ChunkRetrievalResult] = []
        element_map: dict[int, dict[str, object]] = {}
        if need_retrieve:
            search_query = self._query_rewriter.rewrite(question_text, memory_summary) or question_text
            try:
                chunk_results = self._retriever.retrieve_topk(
                    collection_id=collection_id,
                    doc_id=document_id,
                    query_text=search_query,
                    top_k=config.chunk_top_k,
                    chunk_types=self._map_chunk_types(elem_types_for_retrieval),
                    search_mode=config.search_mode,
                    enable_page_filter=config.enable_page_filter,
                    page_top_k=config.page_top_k,
                )
                expanded_elements = self._retriever.expand_chunks_to_elements(chunk_results)
                element_map = {
                    int(row["element_id"]): row
                    for row in expanded_elements
                    if row.get("element_id") is not None
                }
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning("Retriever failed for chat %s: %s", chat_id, exc)
                chunk_results = []
                element_map = {}
            text_evidences = self._build_text_evidences_from_chunks(
                chunks=chunk_results,
                element_map=element_map,
                evidence_limit=config.text_evidence_limit,
            )
            image_candidates = self._collect_image_candidates(
                chunks=chunk_results,
                element_map=element_map,
            )

        vision_client = self._vision_client if config.enable_image_vqa else None
        if config.enable_image_vqa and vision_client is None:
            vision_client = VisionVQAClient()
            self._vision_client = vision_client

        image_evidences = self._build_image_evidences(
            candidates=image_candidates,
            question=question_text,
            memory_summary=memory_summary,
            enable_image_vqa=config.enable_image_vqa,
            image_evidence_limit=config.image_evidence_limit,
            vision_client=vision_client,
        )

        answer_text = self._answer_composer.compose(
            question=question_text,
            memory_summary=memory_summary,
            text_evidences=text_evidences,
            image_evidences=image_evidences,
        )

        next_order = self._compute_next_order(history_turns, chat)
        turn = self._turns_repo.create_turn(
            chat_id=chat_id,
            order=next_order,
            user_question=question_text,
            llm_answer_text=answer_text,
        )
        self._chats_repo.update_chat(chat_id, max_turn_order=next_order)
        used_element_ids = evidence_mapper.extract_element_ids_from_answer(answer_text)
        if used_element_ids:
            records = [
                {
                    "chat_id": chat_id,
                    "turn_id": int(turn["id"]),
                    "turn_order": next_order,
                    "element_id": elem_id,
                }
                for elem_id in used_element_ids
            ]
            try:
                self._turn2element_repo.bulk_bind(records)
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning("Failed to persist turn2element mappings: %s", exc)
        history_turns.append(turn)
        history_element_ids = evidence_mapper.collect_element_ids_from_turns(history_turns)
        mapping = evidence_mapper.build_evidence_no_mapping(history_element_ids)
        elements = self._load_elements_for_ids(used_element_ids)
        evidences = evidence_mapper.build_evidences_payload(
            mapping=mapping,
            elements=elements,
            used_element_ids=used_element_ids,
        )
        logger.info(
            "QAFlow completed chat=%s turn=%s cited_elements=%s",
            chat_id,
            turn.get("id"),
            used_element_ids,
        )
        return QATurnResult(
            turn_id=int(turn["id"]),
            chat_id=chat_id,
            answer_text=answer_text,
            evidences=evidences,
        )

    def _build_text_evidences_from_chunks(
        self,
        *,
        chunks: Iterable[ChunkRetrievalResult],
        element_map: dict[int, dict[str, object]],
        evidence_limit: int,
    ) -> list[EvidenceText]:
        evidences: list[EvidenceText] = []
        used_element_ids: set[int] = set()
        for chunk in chunks:
            if len(evidences) >= evidence_limit:
                break
            chunk_type = (chunk.get("chunk_type") or "").lower()
            if chunk_type == "image":
                continue
            context_text = self._compose_chunk_context(
                chunk=chunk,
                element_map=element_map,
                used_element_ids=used_element_ids,
            )
            if not context_text:
                continue
            main_elem_id = next(
                (elem_id for elem_id in chunk.get("elem_ids") or [] if elem_id in element_map),
                None,
            )
            if main_elem_id is None:
                continue
            evidences.append(
                EvidenceText(
                    element_id=int(main_elem_id),
                    elem_type=chunk_type or "text",
                    text_content=context_text,
                    score=float(chunk.get("score") or 0.0),
                ),
            )
        return evidences

    def _collect_image_candidates(
        self,
        *,
        chunks: Iterable[ChunkRetrievalResult],
        element_map: dict[int, dict[str, object]],
    ) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        for chunk in chunks:
            chunk_type = (chunk.get("chunk_type") or "").lower()
            if chunk_type != "image":
                continue
            elem_ids = chunk.get("elem_ids") or []
            if not elem_ids:
                continue
            elem_id = int(elem_ids[0])
            element = element_map.get(elem_id)
            caption = ""
            if element:
                caption = (
                    element.get("text_caption")
                    or element.get("raw_text_content")
                    or ""
                )
            chunk_caption = caption or (chunk.get("chunk_text_main") or "")
            payload = {
                "element_id": elem_id,
                "elem_type": "image",
                "text_content": (f"[Elem#{elem_id}] {chunk_caption}".strip() if chunk_caption else None),
                "score": float(chunk.get("score") or 0.0),
            }
            candidates.append(payload)
        return candidates

    def _compose_chunk_context(
        self,
        *,
        chunk: ChunkRetrievalResult,
        element_map: dict[int, dict[str, object]],
        used_element_ids: set[int],
    ) -> str:
        parts: list[str] = []
        for elem_id in chunk.get("elem_ids") or []:
            if elem_id in used_element_ids:
                continue
            element = element_map.get(int(elem_id))
            if not element:
                continue
            text = (
                element.get("raw_text_content")
                or element.get("text_caption")
                or ""
            )
            snippet = (text or "").strip()
            if not snippet:
                continue
            parts.append(f"[Elem#{elem_id}] {snippet}")
            used_element_ids.add(int(elem_id))
        return "\n".join(parts).strip()

    def _build_image_evidences(
        self,
        *,
        candidates: Iterable[dict[str, object]],
        question: str,
        memory_summary: str,
        enable_image_vqa: bool,
        image_evidence_limit: int,
        vision_client: VisionVQAClient | None,
    ) -> list[EvidenceText]:
        evidences: list[EvidenceText] = []
        if not candidates or image_evidence_limit <= 0:
            return evidences
        for row in candidates:
            if len(evidences) >= image_evidence_limit:
                break
            elem_id = int(row["element_id"])
            base_text = (row.get("text_content") or "").strip()
            merged_text = base_text
            if enable_image_vqa and vision_client is not None:
                local_context = base_text
                derived_question = self._image_question_generator.generate(
                    question=question,
                    memory_summary=memory_summary,
                    local_context=local_context,
                )
                try:
                    vqa_summary = vision_client.summarize(
                        element_id=elem_id,
                        derived_question=derived_question,
                        local_context=local_context,
                    )
                    if vqa_summary:
                        merged_text = f"{base_text}\nVision summary: {vqa_summary}".strip()
                except VisionVQAError as exc:
                    logger.warning("Vision VQA failed for element %s: %s", elem_id, exc)
            if not merged_text:
                continue
            evidences.append(
                EvidenceText(
                    element_id=elem_id,
                    elem_type="image",
                    text_content=merged_text,
                    score=float(row.get("score") or 0.0),
                ),
            )
        return evidences

    @staticmethod
    def _map_chunk_types(elem_types: Iterable[str] | None) -> set[str] | None:
        if not elem_types:
            return None
        normalized = {entry.strip().lower() for entry in elem_types if entry}
        chunk_types: set[str] = set()
        if any(entry in normalized for entry in {"text", "header", "equation"}):
            chunk_types.add("text")
        if "table" in normalized:
            chunk_types.add("table")
        if "image" in normalized:
            chunk_types.add("image")
        return chunk_types or None

    def _load_elements_for_ids(self, element_ids: Iterable[int]) -> dict[int, dict[str, object]]:
        rows = self._elements_repo.list_by_ids(element_ids)
        mapping: dict[int, dict[str, object]] = {}
        for row in rows:
            mapping[int(row["id"])] = {
                "id": row["id"],
                "doc_id": row["doc_id"],
                "page_no": row.get("page_no"),
                "bbox": row.get("bbox"),
                "elem_type": row.get("elem_type"),
                "text_content": row.get("text_content") or row.get("raw_text_content"),
                "raw_text_content": row.get("raw_text_content"),
                "text_caption": row.get("text_caption"),
                "level_nav": row.get("level_nav"),
            }
        return mapping

    @staticmethod
    def _compute_next_order(
        turns: list[dict[str, object]],
        chat_row: Mapping[str, object],
    ) -> int:
        last_turn_order = max([int(turn.get("order") or 0) for turn in turns], default=0)
        chat_order = int(chat_row.get("max_turn_order") or 0)
        return max(last_turn_order, chat_order) + 1

    def _resolve_chat_scope(self, chat: Mapping[str, object]) -> tuple[int, int | None]:
        chat_type = str(chat.get("type") or "collection").lower()
        if chat_type == "collection":
            collection_id = chat.get("collection_id")
            if collection_id is None:
                raise QAFlowError("collection_id is required when chat type is 'collection'.")
            return int(collection_id), None
        if chat_type == "document":
            document_id = chat.get("document_id")
            if document_id is None:
                raise QAFlowError("document_id is required when chat type is 'document'.")
            document = self._documents_repo.get_by_id(int(document_id))
            if not document:
                raise QAFlowError(f"Document {document_id} not found for chat {chat.get('id')}.")
            return int(document["collection_id"]), int(document_id)
        raise QAFlowError(f"Unsupported chat type: {chat_type}")


def run_qa_turn(
    *,
    chat_id: int,
    question: str,
    top_k: int = 8,
    retrieval_mode: str | None = None,
    elem_types: Iterable[str] | None = None,
    search_mode: str | None = None,
    max_history_turns: int | None = None,
    enable_image_vqa: bool | None = None,
    enable_memory_summarizer: bool | None = None,
    text_evidence_limit: int | None = None,
    image_evidence_limit: int | None = None,
    enable_page_filter: bool | None = None,
    page_top_k: int | None = None,
) -> QATurnResult:
    settings = get_qa_flow_settings()
    orchestrator = QAOrchestrator(
        config=QAFlowConfig.from_settings(settings),
        qa_settings=settings,
    )
    return orchestrator.run(
        chat_id=chat_id,
        question=question,
        top_k=top_k,
        enable_image_vqa=enable_image_vqa,
        enable_memory_summarizer=enable_memory_summarizer,
        retrieval_mode=retrieval_mode,
        elem_types=elem_types,
        search_mode=search_mode,
        max_history_turns=max_history_turns,
        text_evidence_limit=text_evidence_limit,
        image_evidence_limit=image_evidence_limit,
        enable_page_filter=enable_page_filter,
        page_top_k=page_top_k,
    )


__all__ = ["QAOrchestrator", "QAFlowError", "ChatNotFoundError", "run_qa_turn"]
