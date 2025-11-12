# -*- coding: utf-8 -*-
"""
Minimal example: Directly call Ollama Qwen2.5-VL using OpenAI-compatible API

Requirements:
    pip install openai pillow

Preconditions:
    1. Ollama server is running:   ollama serve
    2. Model is available locally: ollama pull qwen2.5vl
    3. API endpoint: http://localhost:${OLLAMA_PORT}/v1/chat/completions
"""

import base64
import os
import sys
from pathlib import Path

from openai import OpenAI
from PIL import Image


def _ensure_repo_root_on_path() -> None:
    """Ensure shared settings are importable when running the script directly."""
    repo_root = None
    for parent in Path(__file__).resolve().parents:
        if (parent / "EviQAsys").exists():
            repo_root = parent
            break
    if repo_root is not None and str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))


_ensure_repo_root_on_path()

try:
    from EviQAsys.backend.app.env_setting import OLLAMA_OPENAI_BASE_URL
except (ModuleNotFoundError, ImportError):
    def _default_ollama_openai_base_url() -> str:
        protocol = os.getenv("OLLAMA_PROTOCOL", "http")
        host = os.getenv("OLLAMA_HOST", "localhost")
        port = os.getenv("OLLAMA_PORT", "11434")
        base_url = os.getenv("OLLAMA_BASE_URL", f"{protocol}://{host}:{port}")
        return os.getenv("OLLAMA_OPENAI_BASE_URL", f"{base_url}/v1")

    OLLAMA_OPENAI_BASE_URL = _default_ollama_openai_base_url()


# ======== Configuration ========
# Ollama’s OpenAI-compatible endpoint
BASE_URL = OLLAMA_OPENAI_BASE_URL
API_KEY = "ollama"                       # placeholder (Ollama ignores key)
MODEL = "qwen2.5vl:72b"                      # your local multimodal model name / ollama/


# ======== Helper: Encode image ========
def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ======== Initialize client ========
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ======== Example 1: Text-only Q&A ========
def test_text_only():
    print("=== Text-only example ===")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": [{"type": "text", "text": "Explain quantum entanglement simply."}]}
        ],
        temperature=0.7,
        max_tokens=200,
    )
    print(response.choices[0].message.content)


# ======== Example 2: Text + Image (Multimodal) ========
def test_text_and_image():
    print("\n=== Multimodal example (image + question) ===")

    image_path = "/mnt/data/sharedData/dataset/jztest/minerU_converted_pdf/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples/auto/images/3c4cf82faaa8797f32723d49fca86e1b9cd1375b7280c624df3d180cf5a95f58.jpg"
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Missing test image: {image_path}")

    image_b64 = encode_image(image_path)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": "What is shown in this image? Describe it in one sentence."},
                ],
            }
        ],
        temperature=0.7,
        max_tokens=200,
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    test_text_only()
    test_text_and_image()
