# Manual validation script for AnswerAgent text/vision model selection.
# Usage example:
#   python EviQAsys/backend/tests/manual/test_answer_agent_llm_switch.py \
#       --document-id 1 --question "Summarize the method." --text-limit 4 --image-limit 2

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
import sys
import textwrap
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_llm_settings, get_vision_llm_settings  # noqa: E402
from EviQAsys.backend.app.repositories import ElementsRepository, initialize_database  # noqa: E402
from EviQAsys.backend.app.services.qa_flow.qa_orchestrator import AnswerAgent  # noqa: E402
from EviQAsys.backend.app.services.qa_flow.models import CandidateElement  # noqa: E402

PROMPT_PREVIEW_LEN = 800
ANSWER_PREVIEW_LEN = 600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual check: AnswerAgent switches between text and vision models based on use_image/images.",
    )
    parser.add_argument("--document-id", type=int, required=True, help="Document id to pull real parsed elements from.")
    parser.add_argument("--question", type=str, required=True, help="User question for the AnswerAgent.")
    parser.add_argument(
        "--memory-summary",
        type=str,
        default="",
        help="Optional memory summary string that may contain [Elem#id].",
    )
    parser.add_argument("--text-limit", type=int, default=4, help="Number of text elements to include.")
    parser.add_argument("--image-limit", type=int, default=2, help="Number of image elements to include.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_database()
    elements_repo = ElementsRepository()
    rows = elements_repo.list_by_document(args.document_id)
    if not rows:
        raise RuntimeError(f"No elements found for document_id={args.document_id}. Ingest the PDF before running.")

    text_candidates, image_candidates = _split_candidates(rows)
    if not text_candidates:
        raise RuntimeError("No text elements available for this document; cannot run text-only scenario.")

    print(f"Loaded {len(text_candidates)} text elements and {len(image_candidates)} image elements from doc {args.document_id}.")
    agent = AnswerAgent(
        text_llm_settings=get_llm_settings(),
        vision_llm_settings=get_vision_llm_settings(),
    )
    text_slice = text_candidates[: max(1, args.text_limit)]
    image_slice = image_candidates[: max(0, args.image_limit)]

    run_scenario(
        label="A) Text-only (use_image=false)",
        agent=agent,
        question=args.question,
        memory_summary=args.memory_summary,
        text_elements=text_slice,
        image_elements=[],
        use_image=False,
    )

    usable_vision = [img for img in image_slice if img.image_base64]
    if usable_vision:
        run_scenario(
            label="B) Vision (use_image=true, with base64)",
            agent=agent,
            question=args.question,
            memory_summary=args.memory_summary,
            text_elements=text_slice,
            image_elements=usable_vision,
            use_image=True,
        )
    else:
        print("Skipped scenario B: no image elements with base64 available.")

    if image_slice:
        stripped_images = [replace(img, image_base64=None) for img in image_slice]
        run_scenario(
            label="C) use_image=true but missing image_base64 (fallback expected)",
            agent=agent,
            question=args.question,
            memory_summary=args.memory_summary,
            text_elements=text_slice,
            image_elements=stripped_images,
            use_image=True,
        )
    else:
        print("Skipped scenario C: document has no image elements.")


def run_scenario(
    *,
    label: str,
    agent: AnswerAgent,
    question: str,
    memory_summary: str,
    text_elements: Sequence[CandidateElement],
    image_elements: Sequence[CandidateElement],
    use_image: bool,
) -> None:
    print("\n" + "=" * 80)
    print(label)
    print(f"use_image={use_image} text_elems={len(text_elements)} image_elems={len(image_elements)}")
    usable_images = [img for img in image_elements if img.image_base64] if use_image else []
    if use_image and image_elements and not usable_images:
        print("Note: image_base64 is missing; AnswerAgent should fallback to text prompt/model.")

    prompt = (
        agent._build_vision_prompt(question, memory_summary, text_elements, usable_images)  # type: ignore[attr-defined]
        if use_image and usable_images
        else agent._build_text_prompt(question, memory_summary, text_elements)  # type: ignore[attr-defined]
    )
    print("\nPrompt preview:")
    print(textwrap.shorten(prompt.replace("\n", " "), width=PROMPT_PREVIEW_LEN, placeholder=" ..."))

    answer_text, used_element_ids, used_model = agent.answer(
        question=question,
        memory_summary=memory_summary,
        text_elements=text_elements,
        image_elements=image_elements,
        use_image=use_image,
    )
    print(f"\nUsed model: {used_model}")
    print(f"Cited element ids: {used_element_ids}")
    print("\nAnswer preview:")
    print(textwrap.shorten(answer_text.replace("\n", " "), width=ANSWER_PREVIEW_LEN, placeholder=" ..."))
    print("=" * 80)


def _split_candidates(rows: Sequence[dict[str, object]]) -> tuple[list[CandidateElement], list[CandidateElement]]:
    text_elements: list[CandidateElement] = []
    image_elements: list[CandidateElement] = []
    for row in rows:
        candidate = _row_to_candidate(row)
        if candidate.elem_type == "image":
            image_elements.append(candidate)
        else:
            text_elements.append(candidate)
    return text_elements, image_elements


def _row_to_candidate(row: dict[str, object]) -> CandidateElement:
    bbox = _safe_load_bbox(row.get("bbox_json"))
    text_content = (row.get("text_content") or row.get("raw_text_content") or "").strip() or None  # type: ignore[attr-defined]
    text_caption = (row.get("text_caption") or "").strip() or None  # type: ignore[attr-defined]
    return CandidateElement(
        element_id=int(row.get("element_id") or row.get("id")),  # type: ignore[arg-type]
        elem_type=str(row.get("elem_type") or row.get("chunk_type") or "text").lower(),
        doc_id=row.get("doc_id"),  # type: ignore[arg-type]
        page_no=row.get("page_no") or row.get("page_id") or row.get("page_index"),  # type: ignore[arg-type]
        bbox=bbox,
        text_content=text_content,
        image_base64=row.get("image_base64"),  # type: ignore[arg-type]
        text_caption=text_caption,
        level_nav=row.get("level_nav"),  # type: ignore[arg-type]
    )


def _safe_load_bbox(raw_bbox: object) -> list[float] | None:
    if raw_bbox is None or raw_bbox == "":
        return None
    if isinstance(raw_bbox, list):
        return raw_bbox  # type: ignore[return-value]
    try:
        parsed = json.loads(raw_bbox) if isinstance(raw_bbox, str) else raw_bbox
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None  # type: ignore[return-value]


if __name__ == "__main__":
    main()
