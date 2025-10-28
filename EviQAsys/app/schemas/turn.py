"""Turn schemas."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import ORMModel


class TurnBase(ORMModel):
    chat_id: int
    user_question: str = Field(..., min_length=1)
    llm_answer_text: Optional[str] = None
    llm_thought_text: Optional[str] = None


class TurnCreate(TurnBase):
    pass


class TurnUpdate(ORMModel):
    llm_answer_text: Optional[str] = None
    llm_thought_text: Optional[str] = None


class TurnRead(TurnBase):
    id: int
    created_at: datetime
