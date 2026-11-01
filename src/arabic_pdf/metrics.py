"""Scoring helpers used by the benchmark: character error rate and word order.

Both metrics compare a reference text (the ground truth, in logical order)
with an extracted text. Before scoring, both sides are NFC normalized,
invisible bidi control characters are removed and all whitespace is
collapsed to single spaces. Nothing else is normalized: presentation forms,
reversed words and wrong digits all count as errors, because a search index
or a language model would see them as errors too.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

try:  # optional, only makes long documents faster
    from rapidfuzz.distance import Levenshtein as _rf_lev
except ImportError:  # pragma: no cover
    _rf_lev = None

_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿­]")
_SPACE = re.compile(r"\s+")


def prepare(text: str) -> str:
    """Normalize a text the same way for reference and hypothesis."""
    text = unicodedata.normalize("NFC", text)
    text = _INVISIBLE.sub("", text)
    return _SPACE.sub(" ", text).strip()


def levenshtein(a, b) -> int:
    """Edit distance between two sequences (strings or lists of words)."""
    if _rf_lev is not None:
        return _rf_lev.distance(a, b)
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        current = [i]
        for j, y in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate: edits needed to turn hypothesis into reference, per reference character."""
    ref, hyp = prepare(reference), prepare(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate over whitespace separated words."""
    ref, hyp = prepare(reference).split(), prepare(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def word_order(reference: str, hypothesis: str) -> float:
    """Share of adjacent word pairs from the reference that appear, in the same order, in the hypothesis.

    A text with every word correct but in reversed order scores close to 0,
    a perfect extraction scores 1.
    """
    ref, hyp = prepare(reference).split(), prepare(hypothesis).split()
    ref_pairs = Counter(zip(ref, ref[1:]))
    if not ref_pairs:
        return 1.0 if ref == hyp else 0.0
    hyp_pairs = Counter(zip(hyp, hyp[1:]))
    matched = sum(min(n, hyp_pairs[p]) for p, n in ref_pairs.items())
    return matched / sum(ref_pairs.values())


def score(reference: str, hypothesis: str) -> dict:
    """All metrics for one document."""
    ref = prepare(reference)
    return {
        "cer": cer(reference, hypothesis),
        "wer": wer(reference, hypothesis),
        "word_order": word_order(reference, hypothesis),
        "ref_chars": len(ref),
        "edits": round(cer(reference, hypothesis) * len(ref)),
    }
