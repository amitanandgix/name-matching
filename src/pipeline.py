"""High-level NameMatcher: transliterate → parse → normalize → score → decide."""

from .transliterate import transliterate, has_non_latin
from .parse import parse
from .match import match, score as name_score, decide, compute_confidence, MatchResult
from .reason import generate as generate_reasoning


def _component_scores(c1, c2) -> dict[str, float]:
    """Score given_name vs given_name and family_name vs family_name."""
    result = {}
    if c1.given_name and c2.given_name:
        s, _ = name_score(c1.given_name, c2.given_name)
        result["given_name"] = round(s, 4)
    if c1.family_name and c2.family_name:
        s, _ = name_score(c1.family_name, c2.family_name)
        result["family_name"] = round(s, 4)
    return result


class NameMatcher:
    """End-to-end name matcher with AI-led transliteration and name parsing.

    Usage::

        matcher = NameMatcher()
        result = matcher.match("अमित आनंद", "Amit Anand")
        print(result.decision, result.score)
        print(result.components1)   # given: अमित  family: आनंद
    """

    def match(self, name1: str, name2: str) -> MatchResult:
        """Compare two names (any script) and return a MatchResult."""
        # Step 1 — transliterate to Latin
        latin1 = transliterate(name1)
        latin2 = transliterate(name2)

        # Step 2 — parse components (uses original script for cultural accuracy)
        comp1 = parse(name1)
        comp2 = parse(name2)

        # Step 3 — score full names
        transliterated = has_non_latin(name1) or has_non_latin(name2)
        result = match(latin1, latin2, orig1=name1, orig2=name2,
                       transliterated=transliterated)

        # Step 4 — component-level scores
        result.components1 = comp1
        result.components2 = comp2
        comp_scores = _component_scores(
            _LatinComponents(comp1, latin1),
            _LatinComponents(comp2, latin2),
        )
        result.component_scores = comp_scores

        # Step 5 — recompute confidence now that component scores are available
        result.confidence, result.confidence_label = compute_confidence(
            result.score, result.decision, result.breakdown,
            component_scores=comp_scores or None,
            transliterated=transliterated,
        )

        # Step 6 — plain-English reasoning
        result.reasoning = generate_reasoning(result)
        return result

    def batch_match(self, pairs: list[tuple[str, str]]) -> list[MatchResult]:
        """Compare a list of (name1, name2) pairs."""
        return [self.match(n1, n2) for n1, n2 in pairs]


class _LatinComponents:
    """Transliterate component fields on demand for scoring."""
    def __init__(self, comp, latin_full: str):
        self._comp = comp
        self._latin_full = latin_full

    @property
    def given_name(self) -> str:
        raw = self._comp.given_name
        return transliterate(raw) if raw else ""

    @property
    def family_name(self) -> str:
        raw = self._comp.family_name
        return transliterate(raw) if raw else ""
