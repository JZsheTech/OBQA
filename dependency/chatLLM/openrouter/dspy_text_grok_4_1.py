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


LLM_BASE_URL = "https://openrouter.ai/api/v1"

# ======================================================
# Configuration
# ======================================================
MODEL_NAME = "x-ai/grok-4.1-fast"
OPENAI_API_KEY =  "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"  # placeholder if local inference doesn't require auth

# ======================================================
# 1️⃣ dspy demo (no external model call)
# ======================================================
def ask_with_dspy(question: str) -> str:
    """Pure dspy demonstration without external model call."""
    class QA(dspy.Signature):
        question: str = dspy.InputField()
        answer: str = dspy.OutputField()

    # a very simple demo predictor (no backend)
    lm = dspy.LM(f"openai/{MODEL_NAME}", api_key=OPENAI_API_KEY, api_base=LLM_BASE_URL)
    dspy.configure(lm=lm)    
    predictor = dspy.Predict(QA)
    # manually fill in a fake answer (since no model backend here)
    result = predictor(question=question)

    return result.answer


# ======================================================
# Test all methods
# ======================================================
if __name__ == "__main__":
    q = "What is the meaning of life?"

    print("\n=== dspy ===")
    print(ask_with_dspy(q))

