"""Core name-matching algorithms and scoring."""

from __future__ import annotations
from dataclasses import dataclass, field
import statistics

from rapidfuzz import fuzz
import jellyfish

from .normalize import normalize, tokenize

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    WEIGHTS, MATCH_THRESHOLD, POSSIBLE_MATCH_THRESHOLD,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    name1: str                          # original input
    name2: str                          # original input
    name1_latin: str                    # after transliteration (may equal name1)
    name2_latin: str                    # after transliteration (may equal name2)
    score: float                        # composite similarity 0.0–1.0
    decision: str                       # MATCH | POSSIBLE_MATCH | NO_MATCH
    breakdown: dict[str, float] = field(default_factory=dict)
    components1: "NameComponents | None" = None   # parsed name parts for name1
    components2: "NameComponents | None" = None   # parsed name parts for name2
    component_scores: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0         # 0.0–1.0, how certain we are of the decision
    confidence_label: str = ""      # HIGH | MEDIUM | LOW
    reasoning: str = ""             # plain-English explanation


# Forward-declare for type hint (imported lazily to avoid circular imports)
try:
    from .parse import NameComponents
except ImportError:
    NameComponents = None  # type: ignore


# ---------------------------------------------------------------------------
# Individual scorers
# ---------------------------------------------------------------------------

def _phonetic_score(tokens1: list[str], tokens2: list[str]) -> float:
    """Per-token phonetic similarity using Soundex + Metaphone."""
    if not tokens1 or not tokens2:
        return 0.0

    scores: list[float] = []
    for t1 in tokens1:
        best = 0.0
        s1 = jellyfish.soundex(t1)
        m1 = jellyfish.metaphone(t1)
        for t2 in tokens2:
            s2 = jellyfish.soundex(t2)
            m2 = jellyfish.metaphone(t2)

            # Exact code match
            soundex_hit = 1.0 if s1 == s2 else 0.0
            meta_hit = 1.0 if m1 and m2 and m1 == m2 else 0.0

            # Fuzzy similarity on the phonetic codes themselves
            jw_soundex = jellyfish.jaro_winkler_similarity(s1, s2)
            jw_meta = (
                jellyfish.jaro_winkler_similarity(m1, m2) if m1 and m2 else 0.0
            )

            token_score = max(soundex_hit, meta_hit, jw_soundex, jw_meta)
            best = max(best, token_score)
        scores.append(best)

    return sum(scores) / len(scores)


def _compute_breakdown(norm1: str, norm2: str) -> dict[str, float]:
    tokens1 = tokenize(norm1)
    tokens2 = tokenize(norm2)
    return {
        "token_sort":   fuzz.token_sort_ratio(norm1, norm2) / 100.0,
        "token_set":    fuzz.token_set_ratio(norm1, norm2) / 100.0,
        "jaro_winkler": jellyfish.jaro_winkler_similarity(norm1, norm2),
        "phonetic":     _phonetic_score(tokens1, tokens2),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score(latin1: str, latin2: str) -> tuple[float, dict[str, float]]:
    """Return (composite_score, breakdown) for two Latin-script name strings."""
    norm1 = normalize(latin1)
    norm2 = normalize(latin2)

    if norm1 == norm2:
        return 1.0, {"exact": 1.0}

    breakdown = _compute_breakdown(norm1, norm2)
    composite = sum(WEIGHTS[k] * v for k, v in breakdown.items())
    return composite, breakdown


def compute_confidence(
    composite: float,
    decision: str,
    breakdown: dict[str, float],
    component_scores: dict[str, float] | None = None,
    transliterated: bool = False,
) -> tuple[float, str]:
    """Return (confidence 0-1, label) for a match decision.

    Three factors:
    - boundary: how far the score sits from the nearest threshold
    - agreement: how consistently all four algorithms scored
    - components: whether per-component scores back up the decision
    """
    # 1. Boundary distance (0 = right at threshold, 1 = far from it)
    if decision == "MATCH":
        boundary = (composite - MATCH_THRESHOLD) / (1.0 - MATCH_THRESHOLD)
    elif decision == "NO_MATCH":
        boundary = (POSSIBLE_MATCH_THRESHOLD - composite) / POSSIBLE_MATCH_THRESHOLD
    else:  # POSSIBLE_MATCH — inherently straddles the uncertain zone
        half_zone = (MATCH_THRESHOLD - POSSIBLE_MATCH_THRESHOLD) / 2
        boundary = min(composite - POSSIBLE_MATCH_THRESHOLD,
                       MATCH_THRESHOLD - composite) / half_zone

    # 2. Algorithm agreement (low std-dev → high agreement)
    vals = [v for k, v in breakdown.items() if k != "exact"]
    if len(vals) > 1:
        agreement = max(0.0, 1.0 - statistics.stdev(vals) * 2.5)
    else:
        agreement = 1.0   # exact match or single scorer

    # 3. Component corroboration
    if component_scores:
        comp_mean = statistics.mean(component_scores.values())
        comp_decision = decide(comp_mean)
        component = 1.0 if comp_decision == decision else (
            0.5 if comp_decision == "POSSIBLE_MATCH" else 0.0
        )
    else:
        component = 0.5   # neutral — no component data

    # 4. Weighted combination
    raw = (
        CONFIDENCE_WEIGHTS["boundary"]   * boundary  +
        CONFIDENCE_WEIGHTS["agreement"]  * agreement +
        CONFIDENCE_WEIGHTS["components"] * component
    )

    # Slight penalty when AI transliteration introduced uncertainty
    if transliterated:
        raw *= 0.93

    confidence = round(max(0.0, min(1.0, raw)), 4)

    if confidence >= CONFIDENCE_HIGH:
        label = "HIGH"
    elif confidence >= CONFIDENCE_MEDIUM:
        label = "MEDIUM"
    else:
        label = "LOW"

    return confidence, label


def decide(composite: float) -> str:
    if composite >= MATCH_THRESHOLD:
        return "MATCH"
    if composite >= POSSIBLE_MATCH_THRESHOLD:
        return "POSSIBLE_MATCH"
    return "NO_MATCH"


def match(
    latin1: str,
    latin2: str,
    orig1: str | None = None,
    orig2: str | None = None,
    transliterated: bool = False,
) -> MatchResult:
    """Compare two Latin-script names and return a MatchResult."""
    composite, breakdown = score(latin1, latin2)
    decision = decide(composite)
    confidence, label = compute_confidence(
        composite, decision, breakdown, transliterated=transliterated
    )
    return MatchResult(
        name1=orig1 if orig1 is not None else latin1,
        name2=orig2 if orig2 is not None else latin2,
        name1_latin=latin1,
        name2_latin=latin2,
        score=round(composite, 4),
        decision=decision,
        breakdown={k: round(v, 4) for k, v in breakdown.items()},
        confidence=confidence,
        confidence_label=label,
    )
