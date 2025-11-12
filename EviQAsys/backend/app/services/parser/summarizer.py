from __future__ import annotations

from pathlib import Path
from typing import Sequence

import nltk
import numpy as np
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

_NLTK_DATA = Path(__file__).resolve().parents[5] / "model" / "nltk_data"
if str(_NLTK_DATA) not in nltk.data.path:
    nltk.data.path.clear()
    nltk.data.path.append(str(_NLTK_DATA))


def tfidf_summary(text: str | None, *, max_sentences: int = 5) -> str:
    """Return a lightweight TF-IDF based summary for a section."""
    if not text:
        return ""
    sentences = [sentence.strip() for sentence in sent_tokenize(text) if sentence.strip()]
    if not sentences:
        return ""
    valid_sentences = [sentence for sentence in sentences if len(sentence) > 10]
    if not valid_sentences:
        valid_sentences = sentences
    limit = min(max_sentences, len(valid_sentences))
    if limit == 0:
        return ""
    vectorizer = TfidfVectorizer(
        stop_words="english",
        lowercase=True,
        max_features=1000,
        token_pattern=r"\b[a-zA-Z]{2,}\b",
    )
    try:
        matrix = vectorizer.fit_transform(valid_sentences)
    except ValueError as exc:
        if "empty vocabulary" in str(exc):
            return " ".join(valid_sentences[:limit])
        raise
    scores = matrix.sum(axis=1).A1
    top_indices = np.argsort(scores)[-limit:]
    top_indices.sort()
    chosen = [valid_sentences[index] for index in top_indices]
    return "\n".join(chosen)


__all__ = ["tfidf_summary"]
