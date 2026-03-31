"""Name Matching demo with AI-led transliteration.

Usage
-----
  python main.py                      # run built-in demo pairs
  python main.py "John Smith" "Jon Smith"    # compare two specific names
  python main.py --demo               # explicit demo flag (same as no args)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from src.pipeline import NameMatcher
from src.match import MatchResult

# ANSI colours (disabled on Windows if not supported, harmless otherwise)
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

_DECISION_COLOR = {
    "MATCH":          _GREEN,
    "POSSIBLE_MATCH": _YELLOW,
    "NO_MATCH":       _RED,
}
_CONFIDENCE_COLOR = {
    "HIGH":   _GREEN,
    "MEDIUM": _YELLOW,
    "LOW":    _RED,
}

_DEMO_PAIRS: list[tuple[str, str]] = [
    # Latin – exact / near-exact
    ("John Smith",           "John Smith"),
    ("John Smith",           "Jon Smith"),
    ("John Smith",           "Smith, John"),
    # Nicknames
    ("William Johnson",      "Bill Johnson"),
    # Diacritics
    ("José García",          "Jose Garcia"),
    ("François Müller",      "Francois Muller"),
    # Arabic -> Latin
    ("محمد علي",             "Muhammad Ali"),
    ("أحمد محمود",           "Ahmed Mahmoud"),
    # Chinese -> Latin (Pinyin)
    ("张伟",                  "Zhang Wei"),
    ("李明",                  "Li Ming"),
    # Russian (Cyrillic) -> Latin
    ("Александр Иванов",     "Alexander Ivanov"),
    ("Михаил Горбачёв",      "Mikhail Gorbachev"),
    # Hebrew -> Latin
    ("דוד לוי",              "David Levi"),
    # Hindi (Devanagari) -> Latin
    ("राहुल गांधी",          "Rahul Gandhi"),
    # Cross-script near-miss
    ("Муса Ибрагим",         "Moussa Ibrahim"),
    # No match
    ("John Smith",           "Jane Doe"),
]


def _bar(score: float, width: int = 20) -> str:
    filled = round(score * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def print_result(result: MatchResult, index: int | None = None) -> None:
    color = _DECISION_COLOR[result.decision]
    prefix = f"{index:>2}. " if index is not None else "    "

    lines = [
        f"{prefix}{_BOLD}Name 1:{_RESET} {result.name1}",
    ]
    if result.name1_latin != result.name1:
        lines.append(f"         -> {result.name1_latin}  (transliterated)")

    lines.append(f"    {_BOLD}Name 2:{_RESET} {result.name2}")
    if result.name2_latin != result.name2:
        lines.append(f"         -> {result.name2_latin}  (transliterated)")

    conf_color = _CONFIDENCE_COLOR.get(result.confidence_label, "")
    lines.append(
        f"    {_BOLD}Score:{_RESET}      {result.score:.4f}  {_bar(result.score)}  "
        f"{color}{_BOLD}{result.decision}{_RESET}"
    )
    lines.append(
        f"    {_BOLD}Confidence:{_RESET} {result.confidence:.4f}  {_bar(result.confidence)}  "
        f"{conf_color}{_BOLD}{result.confidence_label}{_RESET}"
    )

    if "exact" not in result.breakdown:
        lines.append("    Breakdown:")
        for key, val in result.breakdown.items():
            lines.append(f"      {key:<13} {val:.4f}  {_bar(val, 10)}")

    # Name components
    def _fmt_comp(c) -> str:
        parts = []
        if c.given_name:
            parts.append(f"given={c.given_name!r}")
        if c.middle_name:
            parts.append(f"middle={c.middle_name!r}")
        if c.family_name:
            parts.append(f"family={c.family_name!r}")
        return "  ".join(parts) if parts else "(unknown)"

    if result.components1 or result.components2:
        lines.append("    Components:")
        if result.components1:
            lines.append(f"      Name 1 -> {_fmt_comp(result.components1)}")
        if result.components2:
            lines.append(f"      Name 2 -> {_fmt_comp(result.components2)}")
        if result.component_scores:
            lines.append("    Component scores:")
            for part, val in result.component_scores.items():
                lines.append(f"      {part:<13} {val:.4f}  {_bar(val, 10)}")

    print("\n".join(lines))
    print()


def run_demo() -> None:
    matcher = NameMatcher()
    print(f"\n{_BOLD}{'='*64}{_RESET}")
    print(f"{_BOLD}  Name Matching - AI-led Transliteration Demo{_RESET}")
    print(f"{_BOLD}{'='*64}{_RESET}\n")

    results = matcher.batch_match(_DEMO_PAIRS)
    for i, result in enumerate(results, start=1):
        print_result(result, index=i)

    # Summary
    counts = {"MATCH": 0, "POSSIBLE_MATCH": 0, "NO_MATCH": 0}
    for r in results:
        counts[r.decision] += 1
    print(f"{_BOLD}Summary:{_RESET}  "
          f"{_GREEN}MATCH {counts['MATCH']}{_RESET}  "
          f"{_YELLOW}POSSIBLE_MATCH {counts['POSSIBLE_MATCH']}{_RESET}  "
          f"{_RED}NO_MATCH {counts['NO_MATCH']}{_RESET}\n")


def run_single(name1: str, name2: str) -> None:
    matcher = NameMatcher()
    result = matcher.match(name1, name2)
    print()
    print_result(result)


def run_interactive() -> None:
    matcher = NameMatcher()
    print(f"\n{_BOLD}Name Matcher - Interactive Mode{_RESET}")
    print("Enter two names separated by  |  (or 'q' to quit)\n")
    while True:
        try:
            line = input("  Names: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if line.lower() in ("q", "quit", "exit", ""):
            break
        parts = [p.strip() for p in line.split("|", 1)]
        if len(parts) != 2:
            print("  Format: Name 1 | Name 2\n")
            continue
        result = matcher.match(parts[0], parts[1])
        print()
        print_result(result)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a not in ("--demo", "-i", "--interactive")]
    flags = set(sys.argv[1:]) - set(args)

    if "-i" in flags or "--interactive" in flags:
        run_interactive()
    elif len(args) == 2:
        run_single(args[0], args[1])
    elif len(args) == 0:
        run_demo()
    else:
        print("Usage: python main.py [name1 name2 | -i]")
        sys.exit(1)
