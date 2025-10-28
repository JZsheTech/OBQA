# Create a fully annotated Python demo that follows the DSPy RAG tutorial, adapted for a local programming agent workflow.
# The file will be saved to /mnt/data/dspy_rag_agent_demo.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dspy_rag_agent_demo.py

A fully annotated, end‑to‑end demo that follows (and lightly adapts) the official
DSPy RAG tutorial so you can run it locally as a "programming agent" style pipeline.

Source tutorial (read for background & screenshots):
 - https://dspy.ai/tutorials/rag/

What this demo shows (mirrors the tutorial, with extras for local use):
  1) Configure DSPy with your model provider (OpenAI by default; swap to others).
  2) (Optional) Enable MLflow tracing to visualize prompt traces & evaluations.
  3) Load a small Tech QA dataset (RAG‑QA Arena "Tech") and split into sets.
  4) Define a semantic evaluation metric (SemanticF1) and a baseline CoT module.
  5) Build a *retrieval* backend with Embeddings (OpenAI by default) + local top‑K.
  6) Define a RAG module (retrieve → reason → respond).
  7) Evaluate baseline vs. RAG.
  8) (Optional) Optimize the RAG prompt with MIPROv2 and re‑evaluate.
  9) (Optional) Track cost and save / load the optimized program (JSON or MLflow).

Notes for local usage:
 - By default this uses OpenAI models: `openai/gpt-4o-mini` and
   `openai/text-embedding-3-small`. Set OPENAI_API_KEY in your environment.
 - You can swap models (e.g., to OpenRouter, llama.cpp/Ollama adapters,
   or other providers supported by DSPy) by changing CLI flags.
 - FAISS is optional. If you don't have faiss installed, we set
   `brute_force_threshold=30000` to avoid FAISS automatically.
 - This demo is *cost‑aware* but does make LLM calls. Use `--no-optimize`
   to skip MIPRO (which can add cost/time), and reduce `--dev-size` as needed.

Run examples
------------
# Quick run, evaluate baseline CoT and simple RAG (no optimizer):
python dspy_rag_agent_demo.py --no-mlflow --no-optimize --threads 8

# Also compile with MIPROv2 (prompt optimizer), then save JSON:
python dspy_rag_agent_demo.py --optimize --save-json optimized_rag.json

# Use a single test question after building RAG:
python dspy_rag_agent_demo.py --no-optimize --question "why igp is used in mpls?"

# Switch models (example: smaller OpenAI chat + embeddings):
python dspy_rag_agent_demo.py --lm openai/gpt-4o-mini --embedder openai/text-embedding-3-small

# (Advanced) Enable MLflow tracing (start MLflow UI separately: `mlflow ui --port 5000`):
python dspy_rag_agent_demo.py --mlflow-uri http://localhost:5000

"""

from __future__ import annotations

import argparse
import os
import random
import sys
from typing import List, Tuple

import ujson

import dspy
from dspy.utils import download
from dspy.evaluate import SemanticF1

# Optional imports (only used if --mlflow-uri is provided)
try:
    import mlflow  # noqa: F401
except Exception:
    mlflow = None


# ---------- Configuration helpers ----------

def configure_lm(model_id: str) -> dspy.LM:
    """
    Configure the LM backend used by DSPy modules.
    - For OpenAI, set OPENAI_API_KEY in the environment.
    - You can swap to other providers supported by DSPy via 'model_id' string.
      (See: https://github.com/stanfordnlp/dspy#supported-providers )
    """
    lm = dspy.LM(model_id)
    dspy.configure(lm=lm)
    return lm


def maybe_enable_mlflow(mlflow_uri: str | None) -> None:
    """
    Optionally wire up MLflow → DSPy autologging (if URI & package present).
    This mirrors the tutorial's "MLflow DSPy Integration" section.
    """
    if not mlflow_uri:
        return
    if mlflow is None:
        print("[WARN] --mlflow-uri is set but 'mlflow' is not installed. "
              "Run `pip install mlflow>=2.20` and retry.", file=sys.stderr)
        return
    import mlflow as _mlf
    _mlf.set_tracking_uri(mlflow_uri)
    _mlf.set_experiment("DSPy")
    # Enable DSPy traces in MLflow
    try:
        _mlf.dspy.autolog()
        print(f"[INFO] MLflow autolog enabled. UI at: {mlflow_uri}")
    except Exception as e:
        print(f"[WARN] Failed to enable MLflow autolog: {e}", file=sys.stderr)


# ---------- Data loading & splitting ----------

def download_tech_examples() -> List[dict]:
    """
    Fetch the small Tech QA example set used in the tutorial.
    File: ragqa_arena_tech_examples.jsonl
    Each line is a JSON object with keys: 'question', 'response', 'gold_doc_ids'.
    """
    url = "https://huggingface.co/dspy/cache/resolve/main/ragqa_arena_tech_examples.jsonl"
    download(url)
    with open("ragqa_arena_tech_examples.jsonl", "r", encoding="utf-8") as f:
        return [ujson.loads(line) for line in f]


def examples_to_dspy(data: List[dict]) -> List[dspy.Example]:
    """
    Convert raw dicts to DSPy Examples. We mark 'question' as input; the rest
    act as labels/metadata. (Exactly as in the tutorial.)
    """
    return [dspy.Example(**d).with_inputs("question") for d in data]


def split_dataset(examples: List[dspy.Example],
                  seed: int = 0,
                  train_size: int = 200,
                  dev_size: int = 300,
                  test_size: int = 500) -> Tuple[List[dspy.Example], List[dspy.Example], List[dspy.Example]]:
    """
    Shuffle deterministically and create (train, dev, test) splits.
    The tutorial uses (200, 300, 500) as an example; you can scale down via CLI.
    """
    ex = list(examples)
    random.Random(seed).shuffle(ex)
    return ex[:train_size], ex[train_size:train_size+dev_size], ex[train_size+dev_size:train_size+dev_size+test_size]


# ---------- Baseline modules & evaluation ----------

def build_semantic_f1() -> SemanticF1:
    """
    SemanticF1 is a decompositional coverage/precision metric implemented
    as a small DSPy program, matching the tutorial.
    """
    return SemanticF1(decompositional=True)


def evaluate_program(program: dspy.Module,
                     devset: List[dspy.Example],
                     metric: SemanticF1,
                     threads: int = 8,
                     show_table_rows: int = 2) -> float:
    """
    Parallel evaluation helper using dspy.Evaluate (exactly like the tutorial).
    Returns the aggregated score for convenience.
    """
    evaluate = dspy.Evaluate(
        devset=devset,
        metric=metric,
        num_threads=threads,
        display_progress=True,
        display_table=show_table_rows
    )
    score = evaluate(program)
    # For MLflow users, DSPy autolog would capture details automatically.
    return float(score)


# ---------- Retrieval backend ----------

def ensure_corpus_and_search(embedder_model: str,
                             embedder_dim: int,
                             topk: int = 5,
                             max_chars: int = 6000,
                             brute_force_threshold: int = 30000):
    """
    Build a local top‑K retrieval function `search(query)` using DSPy's
    Embeddings retriever (OpenAI by default). This follows the tutorial's
    exact approach, including truncating long docs and avoiding FAISS unless
    you have it installed.

    Returns
    -------
    search : callable
        A function: `search(query).passages -> List[str]`
    doc_count : int
        Number of documents loaded into the retriever.
    """
    # 1) Download the small (≈28k) Tech corpus used by the tutorial
    #    (the full dataset is ~650k docs; the tutorial downsamples to be fast).
    corpus_url = "https://huggingface.co/dspy/cache/resolve/main/ragqa_arena_tech_corpus.jsonl"
    download(corpus_url)

    # 2) Load & lightly truncate to clip >99th percentile outliers (per tutorial)
    with open("ragqa_arena_tech_corpus.jsonl", "r", encoding="utf-8") as f:
        corpus = [ujson.loads(line)["text"][:max_chars] for line in f]

    print(f"[INFO] Loaded {len(corpus)} documents for retrieval. Encoding...")

    # 3) Create an embedder + embeddings retriever
    #    If you don't have FAISS installed, pass brute_force_threshold to force a pure‑Python search.
    embedder = dspy.Embedder(embedder_model, dimensions=embedder_dim)
    retriever = dspy.retrievers.Embeddings(
        embedder=embedder,
        corpus=corpus,
        k=topk,
        brute_force_threshold=brute_force_threshold  # avoids FAISS unless corpus > threshold
    )

    # 4) Wrap as a simple callable for the RAG module to use
    def search(query: str):
        """
        Return an object with `passages` as a list of retrieved text strings.
        This mirrors the tutorial's usage pattern: `search(question).passages`.
        """
        return retriever(query)

    return search, len(corpus)


# ---------- RAG module (matches tutorial structure) ----------

class RAG(dspy.Module):
    """
    A minimal RAG module: retrieve relevant passages, then call a CoT‑style
    responder over (context, question). The 'respond' submodule is a
    dspy.ChainOfThought signature like in the tutorial.
    """
    def __init__(self, search_callable):
        super().__init__()
        self.search = search_callable
        self.respond = dspy.ChainOfThought('context, question -> response')

    def forward(self, question: str):
        context_passages = self.search(question).passages
        # Join passages for simplicity; you could also pass a list and let your prompt format enumerate them.
        context = "\n".join(f"[{i+1}] {p}" for i, p in enumerate(context_passages))
        return self.respond(context=context, question=question)


# ---------- Optional: prompt optimization (MIPROv2) ----------

def maybe_optimize_rag(rag: RAG,
                       trainset: List[dspy.Example],
                       metric: SemanticF1,
                       threads: int = 8,
                       auto_level: str = "medium",
                       max_bootstrapped_demos: int = 2,
                       max_labeled_demos: int = 2,
                       do_optimize: bool = False) -> dspy.Module:
    """
    If `do_optimize` is True, run MIPROv2 to compile a stronger prompt for the
    RAG program, as shown in the tutorial. Returns the (possibly) optimized module.

    Cost note: the tutorial mentions ~USD $1.5 for 'auto=medium' depending on provider/limits.
    """
    if not do_optimize:
        return rag
    tp = dspy.MIPROv2(metric=metric, auto=auto_level, num_threads=threads)
    optimized = tp.compile(
        rag,
        trainset=trainset,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos
    )
    return optimized


# ---------- Utility: cost tracking & program IO ----------

def total_cost_from_history(lm: dspy.LM) -> float:
    """
    If the provider exposes costs via LiteLLM, DSPy keeps them in lm.history.
    This matches the tutorial snippet.
    """
    costs = [x.get("cost") for x in getattr(lm, "history", []) if x.get("cost") is not None]
    return float(sum(costs)) if costs else 0.0


def save_program_json(program: dspy.Module, path: str) -> None:
    program.save(path)
    print(f"[INFO] Saved program to: {path}")


def load_program_json(program_cls, path: str, *args, **kwargs) -> dspy.Module:
    prog = program_cls(*args, **kwargs)
    prog.load(path)
    print(f"[INFO] Loaded program from: {path}")
    return prog


# ---------- CLI ----------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DSPy RAG tutorial — local programming agent demo")
    # Models
    p.add_argument("--lm", default="openai/gpt-4o-mini",
                   help="DSPy LM id, e.g., openai/gpt-4o-mini, openai/gpt-4o, openrouter/xxx, ollama/llama3, etc.")
    p.add_argument("--embedder", default="openai/text-embedding-3-small",
                   help="Embedding model id (DSPy Embedder).")
    p.add_argument("--embedder-dim", type=int, default=512,
                   help="Embedding dimension for the chosen embedder (512 for openai/text-embedding-3-small).")
    # Data sizes
    p.add_argument("--train-size", type=int, default=200)
    p.add_argument("--dev-size", type=int, default=300)
    p.add_argument("--test-size", type=int, default=500)
    p.add_argument("--seed", type=int, default=0)
    # Retrieval
    p.add_argument("--topk", type=int, default=5, help="Top‑K passages per query.")
    p.add_argument("--max-chars", type=int, default=6000, help="Truncate docs to this length (tutorial uses 6000).")
    p.add_argument("--brute-force-threshold", type=int, default=30000,
                   help="If corpus <= threshold, use pure‑Python search (avoid FAISS).")
    # Optimization
    opt = p.add_argument_group("optimization")
    opt.add_argument("--optimize", dest="optimize", action="store_true", help="Enable MIPROv2 prompt optimization.")
    opt.add_argument("--no-optimize", dest="optimize", action="store_false")
    opt.set_defaults(optimize=False)
    opt.add_argument("--auto", default="medium", help="MIPROv2 auto level (e.g., 'light', 'medium', 'aggressive').")
    opt.add_argument("--threads", type=int, default=max(4, (os.cpu_count() or 8) // 2))
    opt.add_argument("--max-bootstrapped-demos", type=int, default=2)
    opt.add_argument("--max-labeled-demos", type=int, default=2)
    # MLflow
    p.add_argument("--mlflow-uri", default=None,
                   help="If set, enable MLflow autolog with this tracking URI (e.g. http://localhost:5000).")
    # Save/Load
    p.add_argument("--save-json", default=None, help="If set, save the (optimized) program to this JSON path.")
    p.add_argument("--load-json", default=None, help="If set, load a previously saved program JSON path.")
    # Quick question test
    p.add_argument("--question", default=None, help="If set, run a single question through the (R)AG pipeline.")
    return p


def main():
    args = build_argparser().parse_args()

    # 1) Configure model (and optional MLflow)
    lm = configure_lm(args.lm)
    maybe_enable_mlflow(args.mlflow_uri)

    # 2) Load the Tech QA examples and build splits for development
    raw = download_tech_examples()
    examples = examples_to_dspy(raw)

    trainset, devset, testset = split_dataset(
        examples, seed=args.seed,
        train_size=args.train_size, dev_size=args.dev_size, test_size=args.test_size
    )
    print(f"[INFO] Split sizes => train: {len(trainset)}, dev: {len(devset)}, test: {len(testset)}")

    # 3) Metric (SemanticF1) and a cheap baseline (Chain of Thought) for comparison
    metric = build_semantic_f1()

    cot = dspy.ChainOfThought("question -> response")
    print("[INFO] Evaluating baseline ChainOfThought on devset ...")
    cot_score = evaluate_program(cot, devset, metric, threads=args.threads, show_table_rows=2)
    print(f"[RESULT] CoT baseline SemanticF1: {cot_score:.2f}")

    # 4) Build the retrieval backend
    search, doc_count = ensure_corpus_and_search(
        embedder_model=args.embedder,
        embedder_dim=args.embedder_dim,
        topk=args.topk,
        max_chars=args.max_chars,
        brute_force_threshold=args.brute_force_threshold
    )
    print(f"[INFO] Retrieval ready over {doc_count} docs. topk={args.topk}")

    # Either load a previously saved RAG, or create a fresh one.
    if args.load_json:
        rag = load_program_json(RAG, args.load_json, search_callable=search)
    else:
        rag = RAG(search_callable=search)

    # 5) Evaluate basic RAG
    print("[INFO] Evaluating basic RAG on devset ...")
    rag_score = evaluate_program(rag, devset, metric, threads=args.threads, show_table_rows=2)
    print(f"[RESULT] Basic RAG SemanticF1: {rag_score:.2f}")

    # 6) (Optional) Optimize with MIPROv2, then re‑evaluate
    final_prog = maybe_optimize_rag(
        rag, trainset=trainset, metric=metric, threads=args.threads,
        auto_level=args.auto, max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=args.max_labeled_demos, do_optimize=args.optimize
    )

    if args.optimize:
        print("[INFO] Evaluating *optimized* RAG on devset ...")
        opt_score = evaluate_program(final_prog, devset, metric, threads=args.threads, show_table_rows=2)
        print(f"[RESULT] Optimized RAG SemanticF1: {opt_score:.2f}")

    # 7) Quick interactive check if a question was provided
    if args.question:
        pred = final_prog(question=args.question)
        print("\n=== One‑shot Question ===")
        print(args.question)
        print("\n--- Response ---")
        print(pred.response)

    # 8) Save program JSON if requested (useful to reload without re‑optimizing)
    if args.save_json:
        save_program_json(final_prog, args.save_json)

    # 9) Report rough cost if available
    try:
        cost = total_cost_from_history(lm)
        if cost > 0:
            print(f"[INFO] Approximate provider cost recorded by LiteLLM: ${cost:.4f} USD")
    except Exception:
        pass


if __name__ == "__main__":
    main()


