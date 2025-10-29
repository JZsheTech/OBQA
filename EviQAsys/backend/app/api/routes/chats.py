"""Chat creation, turn submission, and evidence lookup routes."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Path

from ...schemas import (
    AnswerPayload,
    ChatCreateRequest,
    ChatListResponse,
    ChatResponse,
    EvidenceAnchor,
    EvidenceListResponse,
    TurnResponse,
    TurnSubmitRequest,
)

router = APIRouter(tags=["chats"])


def _example_chat(collection_id: int, chat_id: int) -> ChatResponse:
    return ChatResponse(
        id=chat_id,
        collection_id=collection_id,
        created_at=datetime(2024, 1, 3, 0, 0, 0),
        title="Example Chat",
        max_evidence_no=3,
    )


def _example_evidences() -> List[EvidenceAnchor]:
    return [
        EvidenceAnchor(
            evidence_no=1,
            element_id=100,
            page_no=2,
            bbox=[0.1, 0.2, 0.5, 0.4],
            section_name="Introduction",
        ),
        EvidenceAnchor(
            evidence_no=2,
            element_id=101,
            page_no=5,
            bbox=[0.2, 0.2, 0.6, 0.5],
            section_name="Method",
        ),
    ]


@router.post(
    "/collections/{collection_id}/chats",
    response_model=ChatResponse,
    status_code=201,
)
async def create_chat(
    payload: ChatCreateRequest, collection_id: int = Path(..., ge=1)
) -> ChatResponse:
    """Create a chat for a given collection."""

    return ChatResponse(
        id=20,
        collection_id=collection_id,
        created_at=datetime.utcnow(),
        title=payload.title,
        max_evidence_no=0,
    )


@router.get(
    "/collections/{collection_id}/chats",
    response_model=ChatListResponse,
)
async def list_chats(collection_id: int = Path(..., ge=1)) -> ChatListResponse:
    """List chats scoped to a collection."""

    items: List[ChatResponse] = [_example_chat(collection_id, 20)]
    return ChatListResponse(items=items)


@router.post(
    "/chats/{chat_id}/turns",
    response_model=TurnResponse,
)
async def submit_turn(
    payload: TurnSubmitRequest, chat_id: int = Path(..., ge=1)
) -> TurnResponse:
    """Submit a user question and return a stubbed answer."""

    if chat_id != 20:
        raise HTTPException(status_code=404, detail="Chat not found")

    evidences = _example_evidences()
    answer = AnswerPayload(
        turn_id=200,
        answer_text=(
            "The paper proposes a sequential QA pipeline. "
            "See references for highlighted sections."
        ),
        evidences=evidences,
    )
    return TurnResponse(
        chat_id=chat_id,
        turn_order=1,
        user_question=payload.question,
        answer=answer,
    )


@router.get(
    "/chats/{chat_id}/turns/{turn_id}/evidence",
    response_model=EvidenceListResponse,
)
async def list_turn_evidence(
    chat_id: int = Path(..., ge=1), turn_id: int = Path(..., ge=1)
) -> EvidenceListResponse:
    """Return evidence anchors for a chat turn."""

    if chat_id != 20 or turn_id != 200:
        raise HTTPException(status_code=404, detail="Turn not found")

    evidences = _example_evidences()
    return EvidenceListResponse(chat_id=chat_id, turn_id=turn_id, items=evidences)
