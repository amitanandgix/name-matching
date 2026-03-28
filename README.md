# Name Matching

Offline name matching across scripts and languages. Compare a name against a list of candidates and get a decision (MATCH / POSSIBLE_MATCH / NO_MATCH), a similarity score, confidence label, and plain-English reasoning — with no API key required.

## Features

- **Multi-script transliteration** — converts non-Latin names to Latin before comparison:
  - Hindi / Devanagari → IAST romanization with schwa deletion (`अमित आनंद` → `amit anand`)
  - Chinese / CJK → Pinyin (`张伟` → `zhang wei`)
  - Arabic → letter-map romanization (`محمد علي` → `mhmd aly`)
  - Everything else → unidecode fallback
- **Four similarity algorithms** combined into one weighted score:
  - Token sort ratio (handles word-order swaps)
  - Token set ratio (handles extra middle names / initials)
  - Jaro-Winkler (character-level, prefix-sensitive)
  - Phonetic similarity (Soundex + Metaphone per token)
- **Component-level scoring** — given name and family name scored separately via nameparser
- **Confidence labels** — HIGH / MEDIUM / LOW based on score margin, algorithm agreement, and component corroboration
- **Plain-English reasoning** — explains why two names matched or didn't
- **Fully offline** — no API key, no internet connection needed at match time

## Installation

```bash
pip install -r requirements.txt
```

Optional (for better Hindi and Chinese support):

```bash
pip install indic-transliteration pypinyin
```

## Usage

### Command line

```bash
# Compare one name against a comma-separated list
python compare.py "Amit Anand" "Ameet Anand, Amit Kumar, John Smith"

# Compare against a text file (one candidate per line)
python compare.py "Amit Anand" candidates.txt

# Analyse a single name (no candidates)
python compare.py "अमित आनंद"

# Interactive mode
python compare.py
```

### Example output

```
  ==============================================================
    COMPARING
  ==============================================================
    Input Name  :  Amit Anand
  --------------------------------------------------------------
    Against     :  3 candidates
               -  Ameet Anand
               -  Amit Kumar
               -  John Smith
  ==============================================================

  +-----+--------------+----------------+----------------+-----------------+---------+------------+
  | #   | Input Name   | Candidate      | Transliterated | Decision        | Score   | Confidence |
  +-----+--------------+----------------+----------------+-----------------+---------+------------+
  | 1   | Amit Anand   | Ameet Anand    | -              | MATCH           | 0.924   | HIGH       |
  +-----+--------------+----------------+----------------+-----------------+---------+------------+
  | 2   | Amit Anand   | Amit Kumar     | -              | POSSIBLE_MATCH  | 0.712   | MEDIUM     |
  +-----+--------------+----------------+----------------+-----------------+---------+------------+
  | 3   | Amit Anand   | John Smith     | -              | NO_MATCH        | 0.091   | HIGH       |
  +-----+--------------+----------------+----------------+-----------------+---------+------------+
```

### Python API

```python
from src.pipeline import NameMatcher

matcher = NameMatcher()
result = matcher.match("Amit Anand", "अमित आनंद")

print(result.score)           # 1.0
print(result.decision)        # MATCH
print(result.confidence_label)# HIGH
print(result.reasoning)       # plain-English explanation
print(result.name2_latin)     # amit anand
```

## How scoring works

| Algorithm    | Weight | Purpose |
|--------------|--------|---------|
| token_sort   | 30%    | Same tokens, different order (e.g. "Last, First" vs "First Last") |
| token_set    | 25%    | Subset matching (handles extra middle names or initials) |
| jaro_winkler | 25%    | Character-level similarity, prefix-sensitive |
| phonetic     | 20%    | Sounds-alike matching (Soundex + Metaphone) |

Thresholds:

| Score range | Decision |
|-------------|----------|
| ≥ 0.85      | MATCH |
| 0.65 – 0.85 | POSSIBLE_MATCH |
| < 0.65      | NO_MATCH |

## Project structure

```
compare.py          # CLI entry point
config.py           # thresholds, weights, model config
src/
  transliterate.py  # script detection and transliteration
  normalize.py      # lowercase, diacritics, titles, punctuation
  parse.py          # name component parsing (given/family/middle)
  match.py          # scoring, confidence, MatchResult dataclass
  pipeline.py       # NameMatcher orchestrator
  reason.py         # plain-English reasoning generator
```

## Dependencies

- [rapidfuzz](https://github.com/maxbachmann/RapidFuzz) — fast fuzzy string matching
- [jellyfish](https://github.com/jamesturk/jellyfish) — phonetic algorithms
- [unidecode](https://github.com/avian2/unidecode) — Unicode to ASCII transliteration fallback
- [nameparser](https://github.com/derek73/python-nameparser) — name component parsing
- [pypinyin](https://github.com/mozillazg/python-pinyin) — Chinese Pinyin transliteration
- [indic-transliteration](https://github.com/indic-transliteration/indic_transliteration) — Devanagari / IAST romanization
