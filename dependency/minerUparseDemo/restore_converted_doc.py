"""Restore converted document artifacts from a unified JSON dump.
把通过minerU-api(dependency/minerUparseDemo/parse_pdf_minerU.py)解析出来的json结果还原为
`md_content`(全文), `content_list`(Element-包括各个模态), and `images`(图片集合)

This script reads a JSON file that contains three top-level keys:
`md_content`, `content_list`, and `images`. It recreates the markdown text,
the parsed `content_list.json`, and an `img/` folder populated with the
embedded base64 images.

Example:
    python dependency/minerUparseDemo/restore_converted_doc.py sample_data/converted_doc/demo1.json --output-dir sample_data/converted_doc/demo1

Use `--output-dir` to control where the reconstructed assets are written.
Without it, the assets are created in a sibling folder named after the JSON
file stem (e.g., `demo1/` for `demo1.json`).
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
from pathlib import Path
from typing import Any, Dict


def convert_file(input_path: Path, output_dir: Path | None = None) -> None:
    """Convert the unified JSON dump back into discrete artifacts."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    target_dir = output_dir or (input_path.parent / input_path.stem)
    target_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as fp:
        payload: Dict[str, Any] = json.load(fp)

    md_content = payload.get("md_content", "")
    content_list_raw = payload.get("content_list", "")
    images: Dict[str, str] = payload.get("images", {}) or {}

    md_path = target_dir / f"{input_path.stem}.md"
    md_path.write_text(md_content, encoding="utf-8")

    content_list_path = target_dir / "content_list.json"
    try:
        content_list = json.loads(content_list_raw)
    except json.JSONDecodeError:
        # Persist the raw string so users can inspect malformed JSON.
        content_list_path.write_text(content_list_raw, encoding="utf-8")
    else:
        content_list_path.write_text(
            json.dumps(content_list, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if images:
        img_dir = target_dir / "img"
        img_dir.mkdir(exist_ok=True)
        mime_ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        for name, b64_payload in images.items():
            if not isinstance(name, str) or not isinstance(b64_payload, str):
                continue
            payload = b64_payload.strip()
            mime_type = None
            if payload.startswith("data:"):
                try:
                    header, payload = payload.split(",", 1)
                except ValueError:
                    continue
                header_parts = header.split(";")
                if header_parts and header_parts[0].startswith("data:"):
                    mime_type = header_parts[0][5:].lower()
            suffix = Path(name).suffix.lower()
            if not suffix and mime_type in mime_ext_map:
                name = f"{name}{mime_ext_map[mime_type]}"
                suffix = Path(name).suffix.lower()
            if not suffix:
                name = f"{name}.jpg"
            img_path = img_dir / name
            try:
                img_bytes = base64.b64decode(payload)
            except (binascii.Error, ValueError):
                # Skip invalid base64 payloads.
                continue
            img_path.write_bytes(img_bytes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore markdown, content list, and images from JSON dump."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the JSON file produced by the converted_doc pipeline.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory where the reconstructed assets will be saved.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    convert_file(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
