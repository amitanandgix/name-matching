"""Plain-English reasoning generator for MatchResult."""

from __future__ import annotations
from .match import MatchResult


def generate(result: MatchResult) -> str:
    sentences: list[str] = []

    # ── Transliteration note ──────────────────────────────────────────────────
    if result.name1_latin != result.name1:
        sentences.append(
            f"'{result.name1}' was converted from its original script to "
            f"'{result.name1_latin}' for comparison."
        )
    if result.name2_latin != result.name2:
        sentences.append(
            f"'{result.name2}' was converted from its original script to "
            f"'{result.name2_latin}' for comparison."
        )

    # ── Exact match shortcut ──────────────────────────────────────────────────
    if "exact" in result.breakdown:
        sentences.append(
            "After removing diacritics, titles, and punctuation, both names "
            "are identical."
        )
        sentences.append("This is a near-perfect match with very high confidence.")
        return " ".join(sentences)

    # ── Component-level analysis ──────────────────────────────────────────────
    gn = result.component_scores.get("given_name")
    fn = result.component_scores.get("family_name")

    if gn is not None and fn is not None:
        if gn >= 0.95 and fn >= 0.95:
            sentences.append(
                "Both the given name and family name are near-identical matches."
            )
        elif gn >= 0.85 and fn >= 0.85:
            sentences.append(
                "Both the given name and family name match strongly."
            )
        elif gn >= 0.85 and fn < 0.65:
            sentences.append(
                f"The given name is a strong match (score {gn:.2f}), "
                f"but the family name differs significantly (score {fn:.2f})."
            )
        elif fn >= 0.85 and gn < 0.65:
            sentences.append(
                f"The family name is a strong match (score {fn:.2f}), "
                f"but the given name differs significantly (score {gn:.2f})."
            )
        elif gn >= 0.65 and fn >= 0.65:
            sentences.append(
                f"Both components show partial similarity — "
                f"given name: {gn:.2f}, family name: {fn:.2f}."
            )
        elif gn >= 0.85:
            sentences.append(
                f"The given names match well ({gn:.2f}) but the family names "
                f"are quite different ({fn:.2f})."
            )
        elif fn >= 0.85:
            sentences.append(
                f"The family names match well ({fn:.2f}) but the given names "
                f"are quite different ({gn:.2f})."
            )
        else:
            sentences.append(
                f"Neither component matches well — "
                f"given name: {gn:.2f}, family name: {fn:.2f}."
            )

    # ── Algorithm insights ────────────────────────────────────────────────────
    bd = result.breakdown
    ts  = bd.get("token_sort",   0.0)
    tse = bd.get("token_set",    0.0)
    jw  = bd.get("jaro_winkler", 0.0)
    ph  = bd.get("phonetic",     0.0)

    if ts >= 0.95 and jw < 0.80:
        sentences.append(
            "The names appear to be in different order "
            "(e.g. 'Last, First' vs 'First Last')."
        )

    if tse >= 0.92 and ts < 0.82:
        sentences.append(
            "One name contains an extra token (such as a middle name or "
            "initial) that the other does not."
        )

    if 0.80 <= jw < 0.93:
        sentences.append(
            "There is a minor spelling variation between the names "
            "(e.g. 'Amit' vs 'Ameet', or 'Mohammed' vs 'Muhammad')."
        )
    elif jw < 0.70:
        sentences.append(
            "The names differ significantly at the character level."
        )

    if ph >= 0.90 and jw < 0.90:
        sentences.append(
            "Despite the spelling difference, the names sound very similar "
            "when spoken aloud."
        )
    elif ph < 0.50:
        sentences.append(
            "The names also differ phonetically and do not sound alike."
        )

    spread = max(ts, tse, jw, ph) - min(ts, tse, jw, ph)
    if spread > 0.35:
        sentences.append(
            "The four matching algorithms give notably different scores, "
            "suggesting this comparison is ambiguous."
        )

    # ── Final verdict sentence ────────────────────────────────────────────────
    s = result.score
    if result.decision == "MATCH":
        if s >= 0.97:
            sentences.append(
                f"Overall score of {s:.3f} indicates a near-perfect match."
            )
        elif s >= 0.90:
            sentences.append(
                f"Overall score of {s:.3f} comfortably exceeds the match "
                f"threshold of 0.85."
            )
        else:
            sentences.append(
                f"Overall score of {s:.3f} just clears the match threshold "
                f"of 0.85 — a manual review is recommended."
            )
    elif result.decision == "POSSIBLE_MATCH":
        sentences.append(
            f"Overall score of {s:.3f} falls in the uncertain range "
            f"(0.65 - 0.85). This could be the same person with a name "
            f"variation, or a different person. Manual review is recommended."
        )
    else:
        if s < 0.35:
            sentences.append(
                f"Overall score of {s:.3f} is well below the threshold. "
                f"These names almost certainly refer to different people."
            )
        else:
            sentences.append(
                f"Overall score of {s:.3f} falls below the match threshold "
                f"of 0.65. Despite some surface similarity, these names "
                f"likely refer to different people."
            )

    return " ".join(sentences)
