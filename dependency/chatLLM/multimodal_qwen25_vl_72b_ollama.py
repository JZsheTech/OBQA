# -*- coding: utf-8 -*-
"""
Minimal example: Directly call Ollama Qwen2.5-VL using OpenAI-compatible API

Requirements:
    pip install openai pillow

Preconditions:
    1. Ollama server is running:   ollama serve
    2. Model is available locally: ollama pull qwen2.5vl
    3. API endpoint: http://localhost:11434/v1/chat/completions
"""

import base64
from openai import OpenAI
from PIL import Image
import os


# ======== Configuration ========
BASE_URL = "http://localhost:11434/v1"   # Ollama’s OpenAI-compatible endpoint
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
