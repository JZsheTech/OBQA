# -*- coding: utf-8 -*-
"""
Minimal demo: compare dspy / openai / litellm calls to local Llama3 model.
All three functions perform a simple question -> answer inference.
"""

import os
import sys
from pathlib import Path

import dspy
from openai import OpenAI
from litellm import completion


def _ensure_repo_root_on_path() -> None:
    """Add repository root (containing EviQAsys) to sys.path for shared settings."""
    repo_root = None
    for parent in Path(__file__).resolve().parents:
        if (parent / "EviQAsys").exists():
            repo_root = parent
            break
    if repo_root is not None and str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))


_ensure_repo_root_on_path()

try:
    from EviQAsys.backend.app.env_setting import OLLAMA_BASE_URL, OLLAMA_OPENAI_BASE_URL
except (ModuleNotFoundError, ImportError):
    def _default_ollama_base_url() -> str:
        protocol = os.getenv("OLLAMA_PROTOCOL", "http")
        host = os.getenv("OLLAMA_HOST", "localhost")
        port = os.getenv("OLLAMA_PORT", "11434")
        return f"{protocol}://{host}:{port}"

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", _default_ollama_base_url())
    OLLAMA_OPENAI_BASE_URL = os.getenv("OLLAMA_OPENAI_BASE_URL", f"{OLLAMA_BASE_URL}/v1")

# ======================================================
# Configuration
# ======================================================
MODEL_NAME = "llama3:70b"
OPENAI_API_KEY = "EMPTY"  # placeholder if local inference doesn't require auth

# ======================================================
# 1️⃣ dspy demo (no external model call)
# ======================================================
def ask_with_dspy(question: str) -> str:
    """Pure dspy demonstration without external model call."""
    class QA(dspy.Signature):
        question: str = dspy.InputField()
        answer: str = dspy.OutputField()

    # a very simple demo predictor (no backend)
    lm = dspy.LM(f"openai/{MODEL_NAME}", api_key=OPENAI_API_KEY, api_base=OLLAMA_OPENAI_BASE_URL)
    dspy.configure(lm=lm)    
    predictor = dspy.Predict(QA)
    # manually fill in a fake answer (since no model backend here)
    result = predictor(question=question)
    # result.answer = "This is a demo answer produced by dspy.Predict."
    return result.answer

# ======================================================
# 2️⃣  openai client call
# ======================================================
def ask_with_openai(question: str) -> str:
    """Use OpenAI Python client directly."""
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OLLAMA_OPENAI_BASE_URL)
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=256,
    )
    return resp.choices[0].message.content.strip()


# ======================================================
# 3️⃣  litellm call
# ======================================================
def ask_with_litellm(question: str) -> str:
    """Use litellm.completion() unified interface."""
    resp = completion(
        model= "openai/" + MODEL_NAME,
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=256,
        api_base=OLLAMA_OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )
    return resp["choices"][0]["message"]["content"].strip()


# ======================================================
# Test all methods
# ======================================================
if __name__ == "__main__":
    q = "What is the capital of France?"

    print("\n=== dspy ===")
    print(ask_with_dspy(q))

    print("\n=== openai ===")
    print(ask_with_openai(q))

    print("\n=== litellm ===")
    print(ask_with_litellm(q))
