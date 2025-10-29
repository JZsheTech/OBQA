"""Thin synchronous client for executing OceanBase queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class QueryResult(BaseModel):
    """Structured representation of rows returned from OceanBase."""

    rows: List[Dict[str, Any]]


@dataclass
class OceanBaseConfig:
    """Connection configuration for OceanBase."""

    dsn: str
    username: str
    password: str


@dataclass
class OceanBaseClient:
    """Blocking adapter used by repository modules."""

    config: OceanBaseConfig

    def execute(
        self, sql: str, parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute a SQL statement and return rows as dictionaries.

        The Milestone 2 implementation returns static data to keep focus on
        interface validation without requiring a running OceanBase instance.
        """

        sample_row = {
            "id": 1,
            "name": "Sample Collection",
        }
        return QueryResult(rows=[sample_row])
