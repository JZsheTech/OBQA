from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Mapping

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
from ..retrieval import Retriever
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
    ) -> None:
        self._chats_repo = chats_repo or ChatsRepository()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._turns_repo = turns_repo or TurnsRepository()
        self._turn2element_repo = turn2element_repo or Turn2ElementRepository()
        self._elements_repo = elements_repo or ElementsRepository()
        self._retriever = retriever or Retriever()
        self._memory_service = memory_service or MemoryService()
        self._retrieval_decider = retrieval_decider or RetrievalDecider()
        self._query_rewriter = query_rewriter or QueryRewriter()
        self._answer_composer = answer_composer or AnswerComposer()
        self._image_question_generator = image_question_generator or ImageQuestionGenerator()
        self._vision_client = vision_client
        self._config = config or QAFlowConfig()

    def run(
        self,
        *,
        chat_id: int,
        question: str,
        top_k: int = 8,
        enable_image_vqa: bool = False,
    ) -> QATurnResult:
        question_text = (question or "").strip()
        if not question_text:
            raise QAFlowError("question must be provided.")
        chat = self._chats_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found.")
        collection_id, document_id = self._resolve_chat_scope(chat)
        history_turns = self._turns_repo.list_by_chat(chat_id)
        history_text = format_history_text(history_turns, max_turns=self._config.max_history_turns)
        memory_summary = history_text
        if self._config.enable_memory_summarizer and history_text:
            memory_summary = self._memory_service.summarize_history(history_text)

        decision = self._retrieval_decider.decide(question_text, memory_summary)
        logger.info(
            "QAFlow: chat=%s need_retrieve=%s elem_types=%s",
            chat_id,
            decision.need_retrieve,
            decision.element_types,
        )
        text_evidences: list[EvidenceText] = []
        image_candidates: list[dict[str, object]] = []
        if decision.need_retrieve:
            search_query = self._query_rewriter.rewrite(question_text, memory_summary) or question_text
            try:
                results = self._retriever.retrieve_topk(
                    collection_id=collection_id,
                    doc_id=document_id,
                    query_text=search_query,
                    top_k=max(1, min(top_k, 20)),
                    elem_types=decision.element_types,
                )
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning("Retriever failed for chat %s: %s", chat_id, exc)
                results = []
            for row in results:
                elem_id = int(row["element_id"])
                elem_type = (row.get("elem_type") or "").lower()
                text_content = (row.get("text_content") or "").strip()
                if elem_type == "image":
                    image_candidates.append(row)
                    continue
                if not text_content:
                    continue
                if len(text_evidences) >= self._config.text_evidence_limit:
                    continue
                text_evidences.append(
                    EvidenceText(
                        element_id=elem_id,
                        elem_type=elem_type or "text",
                        text_content=text_content,
                        score=float(row.get("score") or 0.0),
                    ),
                )

        image_evidences = self._build_image_evidences(
            candidates=image_candidates,
            question=question_text,
            memory_summary=memory_summary,
            enable_image_vqa=enable_image_vqa,
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

    def _build_image_evidences(
        self,
        *,
        candidates: Iterable[dict[str, object]],
        question: str,
        memory_summary: str,
        enable_image_vqa: bool,
    ) -> list[EvidenceText]:
        evidences: list[EvidenceText] = []
        if not candidates:
            return evidences
        for row in candidates:
            if len(evidences) >= self._config.image_evidence_limit:
                break
            elem_id = int(row["element_id"])
            base_text = (row.get("text_content") or "").strip()
            merged_text = base_text
            if enable_image_vqa and self._vision_client is not None:
                local_context = base_text
                derived_question = self._image_question_generator.generate(
                    question=question,
                    memory_summary=memory_summary,
                    local_context=local_context,
                )
                try:
                    vqa_summary = self._vision_client.summarize(
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
                "text_content": row.get("text_content"),
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
    enable_image_vqa: bool = False,
    enable_memory_summarizer: bool = False,
) -> QATurnResult:
    orchestrator = QAOrchestrator(
        vision_client=VisionVQAClient() if enable_image_vqa else None,
        config=QAFlowConfig(enable_memory_summarizer=enable_memory_summarizer),
    )
    return orchestrator.run(
        chat_id=chat_id,
        question=question,
        top_k=top_k,
        enable_image_vqa=enable_image_vqa,
    )


__all__ = ["QAOrchestrator", "QAFlowError", "ChatNotFoundError", "run_qa_turn"]
