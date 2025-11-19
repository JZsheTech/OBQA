from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...schemas import TurnCreateRequest, TurnResponse, TurnResponseEnvelope
from ...services.qa_flow import ChatNotFoundError, QAFlowError, run_qa_turn

router = APIRouter(tags=["chats"])


@router.post(
    "/chats/{chat_id}/turns",
    response_model=TurnResponseEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_turn(chat_id: int, payload: TurnCreateRequest) -> TurnResponseEnvelope:
    top_k = payload.top_k or 8
    try:
        result = run_qa_turn(
            chat_id=chat_id,
            question=payload.question,
            top_k=top_k,
            enable_image_vqa=bool(payload.enable_image_vqa),
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
    response = TurnResponse(
        turn_id=result.turn_id,
        chat_id=result.chat_id,
        answer_text=result.answer_text,
        evidences=result.evidences,
    )
    return TurnResponseEnvelope(code="OK", data=response)


__all__ = ["router"]
