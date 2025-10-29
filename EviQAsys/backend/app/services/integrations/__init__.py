"""External service adapters used by the backend."""

from .mineru_client import MinerUClient, MinerUParseRequest, MinerUParseResponse
from .oceanbase_client import (
    OceanBaseClient,
    OceanBaseConfig,
    QueryResult,
)

__all__ = [
    "MinerUClient",
    "MinerUParseRequest",
    "MinerUParseResponse",
    "OceanBaseClient",
    "OceanBaseConfig",
    "QueryResult",
]
