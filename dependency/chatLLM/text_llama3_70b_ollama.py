# -*- coding: utf-8 -*-
"""
Minimal demo: compare dspy / openai / litellm calls to local Llama3 model.
All three functions perform a simple question -> answer inference.
"""

import dspy
from openai import OpenAI
from litellm import completion

# ======================================================
# Configuration
# ======================================================
OLLAMA_BASE_URL = "http://localhost:11434"
OPENAI_BASE_URL = "http://localhost:11434/v1"
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
    lm = dspy.LM(f"ollama/{MODEL_NAME}", api_key="", api_base=OLLAMA_BASE_URL)
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
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
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
        model= "ollama/" + MODEL_NAME,
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=256,
        api_base=OLLAMA_BASE_URL,
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
