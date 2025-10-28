"""Shared Pydantic schema utilities."""

from pydantic import BaseModel

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[assignment]


class ORMModel(BaseModel):
    """Base schema enabling ORM mode compatible with v1/v2."""

    if ConfigDict is not None:
        model_config = ConfigDict(from_attributes=True)  # type: ignore[call-arg]

    class Config:
        orm_mode = True
