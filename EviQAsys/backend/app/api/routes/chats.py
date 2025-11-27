from __future__ import annotations

from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from ...repositories import ChatsRepository, CollectionsRepository, DocumentsRepository, ElementsRepository, TurnsRepository
from ...schemas import (
    ChatDetail,
    ChatDetailEnvelope,
    ChatRead,
    TurnCreateRequest,
    TurnEvidencesEnvelope,
    TurnEvidencesResponse,
    TurnResponse,
    TurnResponseEnvelope,
    TurnWithEvidence,
)
from ...services.mapping import evidence_mapper
from ...services.qa_flow import ChatNotFoundError, QAFlowError, run_qa_turn

router = APIRouter(tags=["chats"])


class ChatCreateRequest(BaseModel):
    title: str | None = None
    doc_id: int | None = None


class ChatUpdateRequest(BaseModel):
    title: str | None = None


class ChatEnvelope(BaseModel):
    code: str = "OK"
    data: ChatRead


def get_chats_repo() -> ChatsRepository:
    return ChatsRepository()


def get_collections_repo() -> CollectionsRepository:
    return CollectionsRepository()


def get_documents_repo() -> DocumentsRepository:
    return DocumentsRepository()


def get_turns_repo() -> TurnsRepository:
    return TurnsRepository()


def get_elements_repo() -> ElementsRepository:
    return ElementsRepository()


@router.post(
    "/collections/{collection_id}/chats",
    response_model=ChatEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_collection_chat(
    collection_id: int,
    payload: ChatCreateRequest,
    collections_repo: CollectionsRepository = Depends(get_collections_repo),
    documents_repo: DocumentsRepository = Depends(get_documents_repo),
    chats_repo: ChatsRepository = Depends(get_chats_repo),
) -> ChatEnvelope:
    collection = collections_repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    title = (payload.title or "").strip() or None
    target_doc_id = payload.doc_id
    chat_type = "document" if target_doc_id is not None else "collection"
    if chat_type == "document":
        try:
            normalized_doc_id = int(target_doc_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doc_id.")
        document = documents_repo.get_by_id(normalized_doc_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        if int(document.get("collection_id")) != collection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document does not belong to the collection.",
            )
        chat = chats_repo.create_chat(
            document_id=normalized_doc_id,
            chat_type="document",
            title=title,
        )
    else:
        chat = chats_repo.create_chat(collection_id=collection_id, chat_type="collection", title=title)
    return ChatEnvelope(code="OK", data=_to_chat_read(chat))


@router.get(
    "/chats/{chat_id}",
    response_model=ChatDetailEnvelope,
)
def get_chat_detail(
    chat_id: int,
    chats_repo: ChatsRepository = Depends(get_chats_repo),
    turns_repo: TurnsRepository = Depends(get_turns_repo),
    elements_repo: ElementsRepository = Depends(get_elements_repo),
) -> ChatDetailEnvelope:
    chat = chats_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    turns = turns_repo.list_by_chat(chat_id)
    mapping = evidence_mapper.build_evidence_no_mapping(
        evidence_mapper.collect_element_ids_from_turns(turns),
    )
    elements = _load_elements_map(elements_repo, mapping.keys())
    formatted_turns = [_format_turn(turn, mapping, elements) for turn in turns]
    detail = ChatDetail(
        id=int(chat["id"]),
        collection_id=chat.get("collection_id"),
        document_id=chat.get("document_id"),
        type=str(chat.get("type") or "collection"),
        title=chat.get("title"),
        max_turn_order=int(chat.get("max_turn_order") or 0),
        created_at=chat["created_at"],
        turns=formatted_turns,
        evidence_no_mapping=mapping,
    )
    return ChatDetailEnvelope(code="OK", data=detail)


@router.patch(
    "/chats/{chat_id}",
    response_model=ChatEnvelope,
)
def update_chat(
    chat_id: int,
    payload: ChatUpdateRequest,
    chats_repo: ChatsRepository = Depends(get_chats_repo),
) -> ChatEnvelope:
    chat = chats_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    title = (payload.title or "").strip() or None
    chats_repo.update_chat(chat_id, title=title)
    refreshed = chats_repo.get_by_id(chat_id)
    if not refreshed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found after update.")
    return ChatEnvelope(code="OK", data=_to_chat_read(refreshed))


@router.delete(
    "/chats/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_chat(
    chat_id: int,
    chats_repo: ChatsRepository = Depends(get_chats_repo),
) -> Response:
    chat = chats_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    chats_repo.delete_chat(chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/turns/{turn_id}/evidences",
    response_model=TurnEvidencesEnvelope,
)
def get_turn_evidences(
    turn_id: int,
    turns_repo: TurnsRepository = Depends(get_turns_repo),
    chats_repo: ChatsRepository = Depends(get_chats_repo),
    elements_repo: ElementsRepository = Depends(get_elements_repo),
) -> TurnEvidencesEnvelope:
    turn = turns_repo.get_by_id(turn_id)
    if not turn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found.")
    chat_id = int(turn["chat_id"])
    chat = chats_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    turns = turns_repo.list_by_chat(chat_id)
    mapping = evidence_mapper.build_evidence_no_mapping(
        evidence_mapper.collect_element_ids_from_turns(turns),
    )
    elements = _load_elements_map(elements_repo, mapping.keys())
    used_element_ids = evidence_mapper.extract_element_ids_from_answer(turn.get("llm_answer_text") or "")
    evidences = evidence_mapper.build_evidences_payload(
        mapping=mapping,
        elements=elements,
        used_element_ids=used_element_ids,
    )
    payload = TurnEvidencesResponse(
        chat_id=chat_id,
        turn_id=turn_id,
        evidence_no_mapping=mapping,
        evidences=evidences,
    )
    return TurnEvidencesEnvelope(code="OK", data=payload)


@router.post(
    "/chats/{chat_id}/turns",
    response_model=TurnResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_turn(
    chat_id: int,
    payload: TurnCreateRequest,
) -> TurnResponseEnvelope:
    top_k = payload.top_k or 8
    try:
        result = run_qa_turn(
            chat_id=chat_id,
            question=payload.question,
            top_k=top_k,
            retrieval_mode=payload.retrieval_mode,
            elem_types=payload.elem_types,
            search_mode=payload.search_mode,
            max_history_turns=payload.max_history_turns,
            enable_image_vqa=payload.enable_image_vqa,
            enable_memory_summarizer=payload.enable_memory_summarizer,
        )
    except ChatNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except QAFlowError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    mapping = {
        int(item["element_id"]): int(item["evidence_no"])
        for item in result.evidences
        if item.get("evidence_no") is not None
    }
    response = TurnResponse(
        turn_id=result.turn_id,
        chat_id=result.chat_id,
        answer_text=result.answer_text,
        evidences=result.evidences,
        answer_with_evidence=evidence_mapper.replace_elem_tags_with_evidence(result.answer_text, mapping) if mapping else result.answer_text,
    )
    return TurnResponseEnvelope(code="OK", data=response)


def _load_elements_map(
    elements_repo: ElementsRepository,
    element_ids: Iterable[int],
) -> dict[int, dict[str, object]]:
    normalized_ids = [int(elem_id) for elem_id in dict.fromkeys(element_ids)]
    if not normalized_ids:
        return {}
    rows = elements_repo.list_by_ids(normalized_ids)
    mapping: dict[int, dict[str, object]] = {}
    for row in rows:
        mapping[int(row["id"])] = {
            "id": row["id"],
            "doc_id": row.get("doc_id"),
            "page_no": row.get("page_no"),
            "bbox": row.get("bbox"),
            "elem_type": row.get("elem_type"),
            "text_content": row.get("text_content"),
            "text_caption": row.get("text_caption"),
            "level_nav": row.get("level_nav"),
        }
    return mapping


def _format_turn(
    turn: dict[str, object],
    mapping: dict[int, int],
    elements: dict[int, dict[str, object]],
) -> TurnWithEvidence:
    answer_text = (turn.get("llm_answer_text") or "") if isinstance(turn, dict) else ""
    used_element_ids = evidence_mapper.extract_element_ids_from_answer(answer_text)
    evidences = evidence_mapper.build_evidences_payload(
        mapping=mapping,
        elements=elements,
        used_element_ids=used_element_ids,
    )
    return TurnWithEvidence(
        id=int(turn["id"]),
        chat_id=int(turn.get("chat_id") or 0),
        order=int(turn.get("order") or 0),
        user_question=turn.get("user_question"),
        answer_text=answer_text,
        answer_with_evidence=evidence_mapper.replace_elem_tags_with_evidence(answer_text, mapping) if mapping else answer_text,
        created_at=turn["created_at"],
        evidences=evidences,
    )


def _to_chat_read(row: dict[str, object]) -> ChatRead:
    return ChatRead(
        id=int(row["id"]),
        collection_id=row.get("collection_id"),
        document_id=row.get("document_id"),
        type=str(row.get("type") or "collection"),
        title=row.get("title"),
        max_turn_order=int(row.get("max_turn_order") or 0),
        created_at=row["created_at"],
    )


__all__ = ["router"]
