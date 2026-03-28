"""Offline name component parsing using the nameparser library."""

from __future__ import annotations
from dataclasses import dataclass
from nameparser import HumanName
from .transliterate import transliterate

_cache: dict[str, "NameComponents"] = {}


@dataclass
class NameComponents:
    given_name: str
    family_name: str
    middle_name: str = ""
    raw: str = ""

    def __str__(self) -> str:
        parts = [self.given_name, self.middle_name, self.family_name]
        return "  ".join(p for p in parts if p)


def parse(name: str) -> NameComponents:
    """Split *name* into given / family / middle components.

    Non-Latin names are transliterated first so nameparser can process them.
    Results are cached so the same name is never processed twice.
    """
    if name in _cache:
        return _cache[name]

    # nameparser works on Latin script only — transliterate first
    latin = transliterate(name)
    h = HumanName(latin)

    result = NameComponents(
        given_name=h.first,
        family_name=h.last,
        middle_name=h.middle,
        raw=name,
    )
    _cache[name] = result
    return result
