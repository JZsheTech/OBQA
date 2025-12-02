from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from openai import OpenAI

from ...env_setting import PER_EVIDENCE_ELEM_CHAR_LIMIT, LLMSettings, QAFlowSettings, get_llm_settings, get_qa_flow_settings
from ...repositories import ChatsRepository, DocumentsRepository, ElementsRepository, TurnsRepository
from ..llm import DSPyPredictorFactory, QueryRewriter
from ..mapping import evidence_mapper
from ..retrieval import ChunkRetrievalResult, Retriever
from .models import CandidateElement, QATurnResult

logger = logging.getLogger(__name__)

_ELEM_TAG_RE = re.compile(r"\[Elem#(?P<id>[0-9A-Za-z_-]+)\]")
_TEXT_CHUNK_TYPES = {"text", "table"}


class QAFlowError(RuntimeError):
    """Base class for QA orchestration errors."""


class ChatNotFoundError(QAFlowError):
    """Raised when chat metadata cannot be located."""


@dataclass
class QAFlowConfig:
    use_image: bool = False
    text_retrieve_topk: int = 8
    image_retrieve_topk: int = 2
    text_memory_topk: int = 4
    image_memory_topk: int = 1
    use_page_in_text_retrieve: bool = False
    page_retrieve_topk: int = 4
    text_search_mode: str = "hybrid"
    memory_max_length: int = 4000
    max_summary_memory_length: int = 1000

    @classmethod
    def from_settings(cls, settings: QAFlowSettings | None = None) -> "QAFlowConfig":
        settings = settings or get_qa_flow_settings()
        return cls(
            use_image=bool(settings.default_use_image),
            text_retrieve_topk=max(1, int(settings.default_text_retrieve_topk)),
            image_retrieve_topk=max(1, int(settings.default_image_retrieve_topk)),
            text_memory_topk=max(1, int(settings.default_text_memory_topk)),
            image_memory_topk=max(1, int(settings.default_image_memory_topk)),
            use_page_in_text_retrieve=bool(settings.default_use_page_in_text_retrieve),
            page_retrieve_topk=max(1, int(settings.default_page_retrieve_topk)),
            text_search_mode=_normalize_search_mode(settings.default_text_search_mode) or "hybrid",
            memory_max_length=max(500, int(settings.memory_max_length)),
            max_summary_memory_length=max(200, int(settings.max_summary_memory_length)),
        )

    def with_overrides(
        self,
        *,
        use_image: bool | None = None,
        text_retrieve_topk: int | None = None,
        image_retrieve_topk: int | None = None,
        text_memory_topk: int | None = None,
        image_memory_topk: int | None = None,
        use_page_in_text_retrieve: bool | None = None,
        page_retrieve_topk: int | None = None,
        text_search_mode: str | None = None,
    ) -> "QAFlowConfig":
        return QAFlowConfig(
            use_image=self._bool_or_default(use_image, self.use_image),
            text_retrieve_topk=self._clamp_topk(text_retrieve_topk, self.text_retrieve_topk),
            image_retrieve_topk=self._clamp_topk(image_retrieve_topk, self.image_retrieve_topk),
            text_memory_topk=self._clamp_topk(text_memory_topk, self.text_memory_topk),
            image_memory_topk=self._clamp_topk(image_memory_topk, self.image_memory_topk),
            use_page_in_text_retrieve=self._bool_or_default(use_page_in_text_retrieve, self.use_page_in_text_retrieve),
            page_retrieve_topk=self._clamp_topk(page_retrieve_topk, self.page_retrieve_topk),
            text_search_mode=_normalize_search_mode(text_search_mode) or self.text_search_mode,
            memory_max_length=self.memory_max_length,
            max_summary_memory_length=self.max_summary_memory_length,
        )

    @staticmethod
    def _bool_or_default(value: bool | None, default: bool) -> bool:
        if value is None:
            return default
        return bool(value)

    @staticmethod
    def _clamp_topk(value: int | None, default: int) -> int:
        if value is None:
            return max(1, min(20, int(default)))
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return max(1, min(20, int(default)))
        return max(1, min(20, numeric))


class TextRetrieveAgent:
    """Query rewrite + text chunk retrieval pipeline (DSPy-enabled)."""

    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self._retriever = retriever or Retriever()
        self._query_rewriter = query_rewriter or QueryRewriter()

    def run(
        self,
        *,
        question: str,
        last_memory: str,
        collection_id: int,
        document_id: int | None,
        top_k: int,
        search_mode: str,
        use_page_filter: bool,
        page_top_k: int,
    ) -> list[ChunkRetrievalResult]:
        search_query = self._query_rewriter.rewrite(question, last_memory) or question
        logger.info(
            "TextRetrieveAgent: query='%s' mode=%s top_k=%s use_page=%s page_top_k=%s",
            search_query,
            search_mode,
            top_k,
            use_page_filter,
            page_top_k,
        )
        return self._retriever.retrieve_topk(
            collection_id=collection_id,
            doc_id=document_id,
            query_text=search_query,
            top_k=top_k,
            chunk_types=_TEXT_CHUNK_TYPES,
            search_mode=search_mode,
            enable_page_filter=use_page_filter,
            page_top_k=page_top_k,
        )

    def expand(self, chunk_results: Sequence[ChunkRetrievalResult]) -> list[CandidateElement]:
        expanded = self._retriever.expand_chunks_to_elements(chunk_results)
        return [_row_to_candidate(row) for row in expanded]


class ImageRetrieveAgent:
    """Optional image retrieval path (no DSPy)."""

    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self._retriever = retriever or Retriever()
        self._query_rewriter = query_rewriter or QueryRewriter()

    def run(
        self,
        *,
        question: str,
        last_memory: str,
        collection_id: int,
        document_id: int | None,
        top_k: int,
    ) -> list[ChunkRetrievalResult]:
        search_query = self._query_rewriter.rewrite(question, last_memory) or question
        logger.info("ImageRetrieveAgent: query='%s' top_k=%s", search_query, top_k)
        return self._retriever.retrieve_topk(
            collection_id=collection_id,
            doc_id=document_id,
            query_text=search_query,
            top_k=top_k,
            chunk_types={"image"},
            search_mode="vector",
        )

    def expand(self, chunk_results: Sequence[ChunkRetrievalResult]) -> list[CandidateElement]:
        expanded = self._retriever.expand_chunks_to_elements(chunk_results)
        return [_row_to_candidate(row) for row in expanded]


class MemoryAgent:
    """Handles memory generation and selection via DSPy with robust fallbacks."""

    def __init__(
        self,
        *,
        predictor_factory: DSPyPredictorFactory | None = None,
        elements_repo: ElementsRepository | None = None,
        max_memory_length: int = 4000,
        max_summary_memory_length: int = 1000,
    ) -> None:
        self._predictor_factory = predictor_factory or DSPyPredictorFactory()
        self._elements_repo = elements_repo or ElementsRepository()
        self._max_memory_length = max_memory_length
        self._max_summary_memory_length = max_summary_memory_length

    def generate_memory(self, last_memory: str, question: str, answer: str) -> str:
        candidate = "\n".join(
            entry for entry in [last_memory.strip(), f"User: {question}".strip(), f"Assistant: {answer}".strip()] if entry
        )
        if len(candidate) <= self._max_memory_length:
            raw_memory = candidate
        else:
            raw_memory = self._summarize(last_memory, question, answer)
        cleaned = self._clean_invalid_elem_ids(raw_memory)
        return cleaned.strip()

    def select_elements(
        self,
        *,
        question: str,
        last_memory: str,
        use_image: bool,
        text_topk: int,
        image_topk: int,
    ) -> tuple[list[CandidateElement], list[CandidateElement]]:
        if not last_memory.strip():
            return [], []
        predicted_ids = self._predict_elem_ids(question, last_memory)
        if not predicted_ids:
            predicted_ids = _extract_elem_ids(last_memory)
        elements = self._elements_repo.list_by_ids(predicted_ids)
        mapping = {int(row["id"]): row for row in elements}
        text_elements: list[CandidateElement] = []
        image_elements: list[CandidateElement] = []
        for elem_id in predicted_ids:
            row = mapping.get(int(elem_id))
            if not row:
                continue
            candidate = _row_to_candidate(row)
            if candidate.elem_type == "image":
                if use_image and len(image_elements) < image_topk:
                    image_elements.append(candidate)
            else:
                if len(text_elements) < text_topk:
                    text_elements.append(candidate)
        return text_elements, image_elements

    def _summarize(self, last_memory: str, question: str, answer: str) -> str:
        predictor = self._predictor_factory.create_predictor(_MemorySummarySignature)
        if predictor is None:
            return self._fallback_summary(last_memory, question, answer)
        prompt = (
            "Based on the current turn’s question, answer, and the previous turn’s memory,\n"
            "generate an updated memory summary.\n\n"
            "Requirements:\n"
            "1. While compressing the content, you must retain all necessary `[Elem#id]` references from the previous memory. "
            "Do NOT remove, rename, or alter them.\n"
            "2. The new summary should be concise and highlight key information, dialog state, and essential evidence references across turns.\n"
            f"3. The total length should not exceed {self._max_summary_memory_length} characters. "
            "This is a soft limit; do your best to stay under it.\n"
            "4. Output only the updated memory text with no extra commentary.\n"
        )
        try:
            result = predictor(
                question=question,
                answer=answer,
                last_turn_memory=last_memory,
                guidance=prompt,
            )
            summary = (getattr(result, "memory_summary", "") or "").strip()
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("Memory summarization failed, falling back: %s", exc)
            summary = ""
        return summary or self._fallback_summary(last_memory, question, answer)

    def _fallback_summary(self, last_memory: str, question: str, answer: str) -> str:
        combined = "\n".join(
            entry for entry in [last_memory.strip(), f"User: {question}".strip(), f"Assistant: {answer}".strip()] if entry
        )
        if len(combined) <= self._max_summary_memory_length:
            return combined
        lines = [line for line in combined.splitlines() if line.strip()]
        return "\n".join(lines[-12:])[-self._max_summary_memory_length :]

    def _predict_elem_ids(self, question: str, memory_text: str) -> list[int]:
        predictor = self._predictor_factory.create_predictor(_MemorySelectionSignature)
        if predictor is None:
            return []
        try:
            result = predictor(question=question, last_turn_memory=memory_text)
            json_text = (getattr(result, "elem_ids_json", "") or "").strip()
            parsed_ids = _parse_elem_id_list(json_text)
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("Memory selection failed to parse JSON, fallback to regex: %s", exc)
            parsed_ids = []
        return parsed_ids

    def _clean_invalid_elem_ids(self, memory_text: str) -> str:
        elem_tags = list(dict.fromkeys(_ELEM_TAG_RE.findall(memory_text or "")))
        if not elem_tags:
            return memory_text
        numeric_ids: list[int] = []
        invalid_tokens: list[str] = []
        for tag in elem_tags:
            try:
                numeric_ids.append(int(tag))
            except ValueError:
                invalid_tokens.append(tag)
        existing = {int(row["id"]) for row in self._elements_repo.list_by_ids(numeric_ids)}
        invalid_numeric = [elem_id for elem_id in numeric_ids if elem_id not in existing]
        cleaned = memory_text
        for token in invalid_tokens:
            cleaned = cleaned.replace(f"[Elem#{token}]", "")
        for elem_id in invalid_numeric:
            cleaned = cleaned.replace(f"[Elem#{elem_id}]", "")
        if invalid_tokens or invalid_numeric:
            logger.warning("Removed invalid Elem IDs from memory: %s %s", invalid_tokens, invalid_numeric)
        return cleaned


class AnswerAgent:
    """OpenAI VLM wrapper following the M10 AnswerAgent prompt."""

    SYSTEM_PROMPT = (
        "You are AnswerAgent in a multimodal evidence-based QA system.\n\n"
        "RULES:\n"
        "1. Only answer using the provided evidence elements.\n"
        "2. Every evidence citation MUST use the exact format: [Elem#<id>]\n"
        "3. Do NOT fabricate element_ids or content not provided.\n"
        "4. Text and image elements are provided separately.\n"
        "5. The order of images EXACTLY matches the order of the image list the system sends to the model.\n"
        "6. When an element is relevant, cite it explicitly using [Elem#id]. Irrelevant elements should be ignored.\n"
        "7. If the question cannot be answered from provided elements, say so clearly."
    )

    def __init__(self, *, llm_settings: LLMSettings | None = None) -> None:
        self._llm_settings = llm_settings or get_llm_settings()
        self._client = self._init_client(self._llm_settings)

    def answer(
        self,
        *,
        question: str,
        memory_summary: str,
        text_elements: Sequence[CandidateElement],
        image_elements: Sequence[CandidateElement],
        use_image: bool,
    ) -> tuple[str, list[int]]:
        prompt = self._build_user_prompt(question, memory_summary, text_elements, image_elements if use_image else [])
        messages = [
            {"role": "system", "content": [{"type": "text", "text": self.SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
                + self._build_image_blocks(image_elements if use_image else []),
            },
        ]
        answer_text = self._generate(messages)
        element_ids = evidence_mapper.extract_element_ids_from_answer(answer_text)
        return answer_text, element_ids

    def _generate(self, messages: list[dict[str, object]]) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._llm_settings.model,
                messages=messages,
                max_tokens=self._llm_settings.max_output_tokens,
                temperature=self._llm_settings.temperature,
            )
            content = completion.choices[0].message.content if completion and completion.choices else None
            if isinstance(content, list):
                joined = "\n".join(
                    part.get("text") or "" for part in content if isinstance(part, dict)
                ).strip()
                if joined:
                    return joined
            if isinstance(content, str) and content.strip():
                return content.strip()
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("AnswerAgent failed, using fallback: %s", exc)
        return "I could not generate an answer with the provided evidences. Please try again with more context."

    def _build_user_prompt(
        self,
        question: str,
        memory_summary: str,
        text_elements: Sequence[CandidateElement],
        image_elements: Sequence[CandidateElement],
    ) -> str:
        text_serialized = "\n".join(
            f"- ElemID: [Elem#{elem.element_id}]\n  Content: {self._truncate(elem.text_content)}"
            for elem in text_elements
        ) or "- none"
        image_serialized = "\n".join(
            f"- ElemID: [Elem#{elem.element_id}]\n  ImageIndex: {idx + 1}\n  Caption: {self._truncate(elem.text_caption)}"
            for idx, elem in enumerate(image_elements)
        ) or "- none"
        return (
            f"# USER QUESTION\n{question}\n\n"
            f"# MEMORY SUMMARY (may contain [Elem#id])\n{memory_summary or 'None'}\n\n"
            "# TEXT ELEMENTS\n"
            "Each text element has:\n- ElemID: [Elem#<id>]\n- Content: <text>\n\n"
            f"{text_serialized}\n\n"
            "# IMAGE ELEMENTS\n"
            "The following list defines the EXACT order of image inputs passed to the model.\n"
            "For each image element:\n- ElemID: [Elem#<id>]\n- ImageIndex: <1-based index>\n- Caption: <caption if exists>\n\n"
            f"{image_serialized}\n\n"
            "Please answer the question following all rules in the system message."
        )

    def _build_image_blocks(self, image_elements: Sequence[CandidateElement]) -> list[dict[str, object]]:
        blocks: list[dict[str, object]] = []
        for elem in image_elements:
            if not elem.image_base64:
                continue
            blocks.append(
                {"type": "image_url", "image_url": {"url": self._ensure_data_uri(elem.image_base64)}},
            )
        return blocks

    @staticmethod
    def _ensure_data_uri(image_b64: str) -> str:
        data = image_b64.strip()
        if data.startswith("data:"):
            return data
        return f"data:image/png;base64,{data}"

    @staticmethod
    def _truncate(text: str | None) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        if len(cleaned) > PER_EVIDENCE_ELEM_CHAR_LIMIT:
            return f"{cleaned[:PER_EVIDENCE_ELEM_CHAR_LIMIT]}..."
        return cleaned

    @staticmethod
    def _init_client(settings: LLMSettings) -> OpenAI:
        client_kwargs: dict[str, object] = {"base_url": settings.api_base, "api_key": settings.api_key}
        extra_headers: dict[str, str] = {}
        if settings.api_key and settings.api_key_header.lower() != "authorization":
            extra_headers[settings.api_key_header] = settings.api_key
        if extra_headers:
            client_kwargs["default_headers"] = extra_headers
        return OpenAI(**client_kwargs)


class QAOrchestrator:
    """Coordinates memory, retrieval, AnswerAgent, and persistence."""

    def __init__(
        self,
        *,
        chats_repo: ChatsRepository | None = None,
        documents_repo: DocumentsRepository | None = None,
        turns_repo: TurnsRepository | None = None,
        elements_repo: ElementsRepository | None = None,
        retriever: Retriever | None = None,
        query_rewriter: QueryRewriter | None = None,
        config: QAFlowConfig | None = None,
        qa_settings: QAFlowSettings | None = None,
        llm_settings: LLMSettings | None = None,
    ) -> None:
        self._qa_settings = qa_settings or get_qa_flow_settings()
        self._llm_settings = llm_settings or get_llm_settings()
        self._chats_repo = chats_repo or ChatsRepository()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._turns_repo = turns_repo or TurnsRepository()
        self._elements_repo = elements_repo or ElementsRepository()
        self._retriever = retriever or Retriever()
        self._query_rewriter = query_rewriter or QueryRewriter()
        self._text_agent = TextRetrieveAgent(retriever=self._retriever, query_rewriter=self._query_rewriter)
        self._image_agent = ImageRetrieveAgent(retriever=self._retriever, query_rewriter=self._query_rewriter)
        predictor_factory = DSPyPredictorFactory(settings=self._llm_settings)
        self._memory_agent = MemoryAgent(
            predictor_factory=predictor_factory,
            elements_repo=self._elements_repo,
            max_memory_length=self._qa_settings.memory_max_length,
            max_summary_memory_length=self._qa_settings.max_summary_memory_length,
        )
        self._answer_agent = AnswerAgent(llm_settings=self._llm_settings)
        self._config = config or QAFlowConfig.from_settings(self._qa_settings)

    def run(
        self,
        *,
        chat_id: int,
        question: str,
        use_image: bool | None = None,
        text_retrieve_topk: int | None = None,
        image_retrieve_topk: int | None = None,
        text_memory_topk: int | None = None,
        image_memory_topk: int | None = None,
        use_page_in_text_retrieve: bool | None = None,
        page_retrieve_topk: int | None = None,
        text_search_mode: str | None = None,
    ) -> QATurnResult:
        question_text = (question or "").strip()
        if not question_text:
            raise QAFlowError("question must be provided.")
        chat = self._chats_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found.")
        collection_id, document_id = self._resolve_chat_scope(chat)
        history_turns = self._turns_repo.list_by_chat(chat_id)
        last_memory = (history_turns[-1].get("memory") or "").strip() if history_turns else ""
        config = self._config.with_overrides(
            use_image=use_image,
            text_retrieve_topk=text_retrieve_topk,
            image_retrieve_topk=image_retrieve_topk,
            text_memory_topk=text_memory_topk,
            image_memory_topk=image_memory_topk,
            use_page_in_text_retrieve=use_page_in_text_retrieve,
            page_retrieve_topk=page_retrieve_topk,
            text_search_mode=text_search_mode,
        )

        text_chunks: list[ChunkRetrievalResult] = []
        image_chunks: list[ChunkRetrievalResult] = []
        try:
            text_chunks = self._text_agent.run(
                question=question_text,
                last_memory=last_memory,
                collection_id=collection_id,
                document_id=document_id,
                top_k=config.text_retrieve_topk,
                search_mode=config.text_search_mode,
                use_page_filter=config.use_page_in_text_retrieve,
                page_top_k=config.page_retrieve_topk,
            )
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("Text retrieval failed: %s", exc)
        if config.use_image:
            try:
                image_chunks = self._image_agent.run(
                    question=question_text,
                    last_memory=last_memory,
                    collection_id=collection_id,
                    document_id=document_id,
                    top_k=config.image_retrieve_topk,
                )
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning("Image retrieval failed: %s", exc)

        text_chunk_elements = self._text_agent.expand(text_chunks)
        image_chunk_elements = self._image_agent.expand(image_chunks) if config.use_image else []

        memory_text_elements, memory_image_elements = self._memory_agent.select_elements(
            question=question_text,
            last_memory=last_memory,
            use_image=config.use_image,
            text_topk=config.text_memory_topk,
            image_topk=config.image_memory_topk,
        )

        merged_text, merged_image = self._merge_candidates(
            text_chunk_elements=text_chunk_elements,
            image_chunk_elements=image_chunk_elements,
            memory_text_elements=memory_text_elements,
            memory_image_elements=memory_image_elements,
            use_image=config.use_image,
        )

        answer_text, used_element_ids = self._answer_agent.answer(
            question=question_text,
            memory_summary=last_memory,
            text_elements=merged_text,
            image_elements=merged_image,
            use_image=config.use_image,
        )

        new_memory = self._memory_agent.generate_memory(last_memory, question_text, answer_text)
        next_order = self._compute_next_order(history_turns, chat)
        turn = self._turns_repo.create_turn(
            chat_id=chat_id,
            order=next_order,
            user_question=question_text,
            llm_answer_text=answer_text,
            memory=new_memory,
            used_llm_model=self._llm_settings.model,
        )
        self._chats_repo.update_chat(chat_id, max_turn_order=next_order)
        history_turns.append(turn)
        mapping = evidence_mapper.build_evidence_no_mapping(
            evidence_mapper.collect_element_ids_from_turns(history_turns),
        )
        element_map = self._build_element_map(merged_text, merged_image)
        missing_ids = [elem_id for elem_id in used_element_ids if elem_id not in element_map]
        if missing_ids:
            for row in self._elements_repo.list_by_ids(missing_ids):
                candidate = _row_to_candidate(row)
                element_map[candidate.element_id] = candidate.as_answer_dict()
        evidences = evidence_mapper.build_evidences_payload(
            mapping=mapping,
            elements=element_map,
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

    def _merge_candidates(
        self,
        *,
        text_chunk_elements: Sequence[CandidateElement],
        image_chunk_elements: Sequence[CandidateElement],
        memory_text_elements: Sequence[CandidateElement],
        memory_image_elements: Sequence[CandidateElement],
        use_image: bool,
    ) -> tuple[list[CandidateElement], list[CandidateElement]]:
        seen: set[int] = set()
        merged_text: list[CandidateElement] = []
        merged_image: list[CandidateElement] = []

        for candidate in text_chunk_elements:
            if candidate.element_id in seen:
                continue
            merged_text.append(candidate)
            seen.add(candidate.element_id)
        for candidate in memory_text_elements:
            if candidate.element_id in seen:
                continue
            merged_text.append(candidate)
            seen.add(candidate.element_id)
        if use_image:
            for candidate in image_chunk_elements:
                if candidate.element_id in seen:
                    continue
                merged_image.append(candidate)
                seen.add(candidate.element_id)
            for candidate in memory_image_elements:
                if candidate.element_id in seen:
                    continue
                merged_image.append(candidate)
                seen.add(candidate.element_id)
        return merged_text, merged_image

    def _build_element_map(
        self,
        text_elements: Sequence[CandidateElement],
        image_elements: Sequence[CandidateElement],
    ) -> dict[int, Mapping[str, object]]:
        mapping: dict[int, Mapping[str, object]] = {}
        for elem in list(text_elements) + list(image_elements):
            mapping[elem.element_id] = elem.as_answer_dict()
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


def _normalize_search_mode(value: str | None) -> str | None:
    if not value:
        return None
    lowered = str(value).lower()
    if lowered in {"vector", "fulltext", "hybrid"}:
        return lowered
    return None


def _row_to_candidate(row: Mapping[str, object]) -> CandidateElement:
    text_content = (row.get("text_content") or row.get("raw_text_content") or "").strip() or None
    text_caption = (row.get("text_caption") or "").strip() or None
    bbox = row.get("bbox")
    if bbox is not None and not isinstance(bbox, list):
        bbox = None
    return CandidateElement(
        element_id=int(row.get("element_id") or row.get("id")),
        elem_type=str(row.get("elem_type") or row.get("chunk_type") or "text").lower(),
        doc_id=row.get("doc_id"),
        page_no=row.get("page_no") or row.get("page_id") or row.get("page_index"),
        bbox=bbox,
        text_content=text_content,
        image_base64=row.get("image_base64"),
        text_caption=text_caption,
        level_nav=row.get("level_nav"),
    )


def _extract_elem_ids(text: str) -> list[int]:
    ids: list[int] = []
    for match in _ELEM_TAG_RE.finditer(text or ""):
        try:
            value = int(match.group("id"))
        except ValueError:
            continue
        if value not in ids:
            ids.append(value)
    return ids


def _parse_elem_id_list(json_text: str) -> list[int]:
    import json

    if not json_text:
        return []
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        candidate = payload.get("element_ids") or payload.get("elem_ids")
    else:
        candidate = payload
    if not isinstance(candidate, (list, tuple)):
        return []
    elem_ids: list[int] = []
    for entry in candidate:
        try:
            elem_id = int(entry)
        except (TypeError, ValueError):
            continue
        if elem_id not in elem_ids:
            elem_ids.append(elem_id)
    return elem_ids


try:
    import dspy  # type: ignore
except ImportError:  # pragma: no cover
    dspy = None

if dspy is not None:

    class _MemorySummarySignature(dspy.Signature):  # type: ignore[misc]
        guidance = dspy.InputField(desc="Summarization rules and constraints.")
        question = dspy.InputField(desc="Current turn question.")
        answer = dspy.InputField(desc="Current turn answer.")
        last_turn_memory = dspy.InputField(desc="Last turn memory text.")
        memory_summary = dspy.OutputField(desc="Updated memory summary containing [Elem#id].")

    class _MemorySelectionSignature(dspy.Signature):  # type: ignore[misc]
        question = dspy.InputField(desc="Current turn question.")
        last_turn_memory = dspy.InputField(desc="Last turn memory text containing [Elem#id].")
        elem_ids_json = dspy.OutputField(
            desc="JSON array of element ids that are helpful for answering the question, e.g. {\"element_ids\": [1,2]}",
        )

else:  # pragma: no cover - fallback for static analyzers

    class _MemorySummarySignature:  # type: ignore[too-many-ancestors]
        pass

    class _MemorySelectionSignature:  # type: ignore[too-many-ancestors]
        pass


def run_qa_turn(
    *,
    chat_id: int,
    question: str,
    use_image: bool | None = None,
    text_retrieve_topk: int | None = None,
    image_retrieve_topk: int | None = None,
    text_memory_topk: int | None = None,
    image_memory_topk: int | None = None,
    use_page_in_text_retrieve: bool | None = None,
    page_retrieve_topk: int | None = None,
    text_search_mode: str | None = None,
    **_: object,
) -> QATurnResult:
    settings = get_qa_flow_settings()
    orchestrator = QAOrchestrator(
        config=QAFlowConfig.from_settings(settings),
        qa_settings=settings,
    )
    return orchestrator.run(
        chat_id=chat_id,
        question=question,
        use_image=use_image,
        text_retrieve_topk=text_retrieve_topk,
        image_retrieve_topk=image_retrieve_topk,
        text_memory_topk=text_memory_topk,
        image_memory_topk=image_memory_topk,
        use_page_in_text_retrieve=use_page_in_text_retrieve,
        page_retrieve_topk=page_retrieve_topk,
        text_search_mode=text_search_mode,
    )


__all__ = ["QAOrchestrator", "QAFlowError", "ChatNotFoundError", "run_qa_turn"]
