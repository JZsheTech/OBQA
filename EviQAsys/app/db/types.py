"""Custom SQLAlchemy column types."""

import json
from typing import Any, Iterable, Optional

from sqlalchemy.types import UserDefinedType


class OBVector(UserDefinedType):
    """OceanBase VECTOR column type helper."""

    cache_ok = True

    def __init__(self, dimension: int):
        super().__init__()
        self.dimension = dimension

    def get_col_spec(self, **_: Any) -> str:
        return f"VECTOR({self.dimension})"

    def bind_processor(self, dialect):  # type: ignore[override]
        def process(value: Optional[Iterable[float]]) -> Optional[str]:
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return json.dumps(list(value))

        return process

    def result_processor(self, dialect, coltype):  # type: ignore[override]
        def process(value: Optional[str]) -> Optional[Any]:
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return process
