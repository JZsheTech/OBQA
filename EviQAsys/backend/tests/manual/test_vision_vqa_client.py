# Manual test: python EviQAsys/backend/tests/manual/test_vision_vqa_client.py --question "Describe the photo."
from __future__ import annotations

import argparse
import base64
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.services.integrations.vision_vqa import (  # noqa: E402
    VisionVQAClient,
    VisionVQAError,
)

DEFAULT_IMAGE_PATH = PROJECT_ROOT / "sample_data" / "image_demo" / "demo1.jpg"

DEFAULT_ELEMENT_ID = 2024083001
DEFAULT_QUESTION = "What is in this image?"


class StaticElementsRepository:
    """Minimal in-memory repository that mimics a single elements row."""

    def __init__(self, element: dict[str, Any]) -> None:
        self._element = dict(element)

    def get_by_id(self, element_id: int) -> dict[str, Any] | None:
        if element_id == self._element.get("id"):
            return dict(self._element)
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manual VisionVQAClient check using the sample image bundled in the repo "
            "and encoded as base64 locally."
        ),
    )
    parser.add_argument(
        "--question",
        type=str,
        default=DEFAULT_QUESTION,
        help="Question sent to the VQA model.",
    )
    parser.add_argument(
        "--element-id",
        type=int,
        default=DEFAULT_ELEMENT_ID,
        help="Synthetic element id used when querying the ElementsRepository stub.",
    )
    parser.add_argument(
        "--image-path",
        type=Path,
        default=DEFAULT_IMAGE_PATH,
        help=f"Path to the local image used for VQA (default: {DEFAULT_IMAGE_PATH}).",
    )
    return parser.parse_args()


def load_image_b64(image_path: Path) -> str:
    """Load a local image and return a base64 string."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    data = image_path.read_bytes()
    encoded = base64.b64encode(data).decode("utf-8")
    print(f"Loaded {image_path} ({len(data)} bytes) -> base64 size {len(encoded)}")
    return encoded


def build_static_element(element_id: int, image_b64: str) -> dict[str, Any]:
    return {
        "id": element_id,
        "doc_id": 0,
        "elem_type": "image",
        "text_caption": "image",
        "image_base64": image_b64.strip(),
    }


def main() -> None:
    args = parse_args()
    try:
        image_b64 = load_image_b64(args.image_path.resolve())
    except OSError as exc:  # pragma: no cover - manual script
        raise SystemExit(f"Failed to load image: {exc}") from exc

    repo = StaticElementsRepository(build_static_element(args.element_id, image_b64))
    client = VisionVQAClient(elements_repo=repo)
    settings = client._settings  # Accessing private field for logging purposes only.
    print("=== Vision VQA sanity check ===")
    print(f"Endpoint: {settings.endpoint}")
    print(f"Model: {settings.model}")
    print(f"Element id: {args.element_id}")
    print(f"Question: {args.question}")
    try:
        answer = client.summarize(
            element_id=args.element_id,
            derived_question=args.question,
            local_context=None,
        )
    except VisionVQAError as exc:
        print(f"Vision VQA request failed: {exc}")
        raise
    print("--- Model response ---")
    print(answer)


if __name__ == "__main__":
    main()
