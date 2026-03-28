"""Name normalization utilities for Latin-script names."""

import re
import unicodedata

# Titles and suffixes to strip before comparison
_TITLES_RE = re.compile(
    r"\b(mr|mrs|ms|miss|dr|prof|sir|rev|fr|sr|jr|ii|iii|iv|esq)\b\.?",
    re.IGNORECASE,
)


def remove_diacritics(text: str) -> str:
    """Strip combining diacritical marks (accents, cedillas, etc.)."""
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def normalize(name: str) -> str:
    """Return a canonical lower-case, ASCII-only form of a Latin-script name.

    Steps:
    1. Lower-case
    2. Remove diacritics  (é → e, ü → u)
    3. Strip titles/suffixes  (Dr., Jr., III, …)
    4. Convert hyphens and apostrophes to spaces  (O'Brien → o brien)
    5. Drop all non-letter characters
    6. Collapse whitespace
    """
    name = name.lower()
    name = remove_diacritics(name)
    name = _TITLES_RE.sub("", name)
    name = re.sub(r"['\-]", " ", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def tokenize(normalized_name: str) -> list[str]:
    """Split a normalized name into individual tokens."""
    return normalized_name.split()
