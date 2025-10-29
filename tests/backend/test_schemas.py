"""Schema serialization and API contract tests for milestone 2."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from EviQAsys.backend.app.schemas import EvidenceAnchor

try:
    from fastapi.testclient import TestClient
    from EviQAsys.backend.app import create_app
except ModuleNotFoundError:  # pragma: no cover - environment without FastAPI
    TestClient = None
    create_app = None


def test_evidence_anchor_generates_label() -> None:
    anchor = EvidenceAnchor(
        evidence_no=1,
        element_id=42,
        page_no=3,
        bbox=[0.0, 0.1, 0.5, 0.4],
    )

    assert anchor.label == "[Evidence#1]"
    assert anchor.model_dump()["label"] == "[Evidence#1]"


@pytest.mark.skipif(TestClient is None, reason="FastAPI not installed in test env")
def test_submit_turn_stub_returns_evidence_labels() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/chats/20/turns", json={"question": "What is OBQA?"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["answer"]["evidences"][0]["label"] == "[Evidence#1]"
    assert payload["answer"]["evidences"][0]["bbox"] == [0.1, 0.2, 0.5, 0.4]
