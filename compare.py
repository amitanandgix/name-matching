"""List-based name comparison.

Usage
-----
  python compare.py "John Smith" "Jon Smith, John A. Smith, Jane Doe"
  python compare.py "John Smith" candidates.txt
  python compare.py "John Smith"
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import textwrap
from pathlib import Path

from src.pipeline import NameMatcher
from src.transliterate import transliterate, has_non_latin
from src.parse import parse
from src.match import MatchResult

# -- ANSI colours --------------------------------------------------------------
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"

_DECISION_COLOR = {"MATCH": _GREEN, "POSSIBLE_MATCH": _YELLOW, "NO_MATCH": _RED}
_CONF_COLOR     = {"HIGH": _GREEN,  "MEDIUM": _YELLOW,         "LOW": _RED}


# -- Helpers -------------------------------------------------------------------

def _bar(v: float, width: int = 16) -> str:
    filled = round(v * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def _wrap(text: str, width: int = 72, indent: str = "     ") -> str:
    return textwrap.fill(text, width=width, subsequent_indent=indent)


def _parse_candidates(raw: str) -> list[str]:
    """Accept a file path or a comma-separated string of names."""
    raw = raw.strip()
    if not raw:
        return []
    p = Path(raw)
    if p.exists() and p.is_file():
        lines = p.read_text(encoding="utf-8").splitlines()
        return [ln.strip() for ln in lines if ln.strip()]
    return [n.strip() for n in raw.split(",") if n.strip()]


# -- Display -------------------------------------------------------------------

def _print_analysis(name: str) -> None:
    """Show what we know about a single name with no candidates to compare."""
    latin  = transliterate(name)
    comp   = parse(name)
    script = "Latin (no transliteration needed)" if latin == name else f"Non-Latin -> transliterated to '{latin}'"

    print(f"\n{_BOLD}Analysing:{_RESET} {name}")
    print("-" * 60)
    print(f"  {'Script:':<14} {script}")
    if comp.given_name:
        print(f"  {'Given name:':<14} {comp.given_name}")
    if comp.middle_name:
        print(f"  {'Middle name:':<14} {comp.middle_name}")
    if comp.family_name:
        print(f"  {'Family name:':<14} {comp.family_name}")
    if not any([comp.given_name, comp.middle_name, comp.family_name]):
        print(f"  (Could not parse components)")
    print()


def _print_table(query: str, results: list[MatchResult]) -> None:
    # Column widths
    C0 = 3
    C1 = max(len(query), 12)
    C2 = max(max(len(r.name2) for r in results), 14)
    C3 = max(max(len(r.name2_latin) if r.name2_latin != r.name2 else 1
                 for r in results), 14)
    C4 = 15
    C5 = 7
    C6 = 10

    def sep():
        print(f"  +-{'-'*C0}-+-{'-'*C1}-+-{'-'*C2}-+-{'-'*C3}-+"
              f"-{'-'*C4}-+-{'-'*C5}-+-{'-'*C6}-+")

    def row(*cols):
        c0, c1, c2, c3, c4, c5, c6 = cols
        print(f"  | {c0} | {c1} | {c2} | {c3} | {c4} | {c5} | {c6} |")

    sep()
    row(
        f"{'#':<{C0}}",
        f"{_BOLD}{'Input Name':<{C1}}{_RESET}",
        f"{_BOLD}{'Candidate':<{C2}}{_RESET}",
        f"{_BOLD}{'Transliterated':<{C3}}{_RESET}",
        f"{_BOLD}{'Decision':<{C4}}{_RESET}",
        f"{_BOLD}{'Score':<{C5}}{_RESET}",
        f"{_BOLD}{'Confidence':<{C6}}{_RESET}",
    )
    sep()

    for i, r in enumerate(results, start=1):
        dc = _DECISION_COLOR[r.decision]
        cc = _CONF_COLOR[r.confidence_label]
        translit = r.name2_latin if r.name2_latin != r.name2 else "-"
        row(
            f"{i:<{C0}}",
            f"{r.name1:<{C1}}",
            f"{r.name2:<{C2}}",
            f"{translit:<{C3}}",
            f"{dc}{r.decision:<{C4}}{_RESET}",
            f"{r.score:<{C5}.3f}",
            f"{cc}{r.confidence_label:<{C6}}{_RESET}",
        )
        sep()

    # Reasoning section below the table
    print(f"\n  {_BOLD}Reasoning{_RESET}")
    print(f"  {'-' * 70}")
    for i, r in enumerate(results, start=1):
        if r.reasoning:
            print(f"  #{i}  {_BOLD}{r.name1}{_RESET} vs {_BOLD}{r.name2}{_RESET}")
            print("  " + _wrap(r.reasoning, width=70, indent="  "))
            print()

    # Summary
    counts = {"MATCH": 0, "POSSIBLE_MATCH": 0, "NO_MATCH": 0}
    for r in results:
        counts[r.decision] += 1
    print(
        f"  {_BOLD}Summary:{_RESET}  "
        f"{_GREEN}MATCH {counts['MATCH']}{_RESET}   "
        f"{_YELLOW}POSSIBLE_MATCH {counts['POSSIBLE_MATCH']}{_RESET}   "
        f"{_RED}NO_MATCH {counts['NO_MATCH']}{_RESET}\n"
    )


# -- Core run ------------------------------------------------------------------

def run(query: str, candidates: list[str], matcher: NameMatcher) -> None:
    """Match *query* against *candidates* and print ranked results."""
    if not candidates:
        _print_analysis(query)
        return

    results = [matcher.match(query, c) for c in candidates]

    _order = {"MATCH": 0, "POSSIBLE_MATCH": 1, "NO_MATCH": 2}
    results.sort(key=lambda r: (_order[r.decision], -r.score))

    W = 62
    print(f"\n  {'=' * W}")
    print(f"  {_BOLD}  COMPARING{_RESET}")
    print(f"  {'=' * W}")
    print(f"  {_BOLD}  Input Name  :{_RESET}  {_BOLD}{query}{_RESET}")
    if has_non_latin(query):
        print(f"  {_BOLD}  Transliterated:{_RESET} {transliterate(query)}")
    print(f"  {'─' * W}")
    n = len(candidates)
    print(f"  {_BOLD}  Against     :{_RESET}  {n} candidate{'s' if n != 1 else ''}")
    for c in candidates:
        latin = transliterate(c)
        suffix = f"  {_DIM}-> {latin}{_RESET}" if latin != c else ""
        print(f"               -  {c}{suffix}")
    print(f"  {'=' * W}\n")

    _print_table(query, results)


# -- Interactive mode -----------------------------------------------------------

def run_interactive() -> None:
    matcher = NameMatcher()

    print(f"\n{_BOLD}+==========================================+{_RESET}")
    print(f"{_BOLD}|       Name Matching - Interactive        |{_RESET}")
    print(f"{_BOLD}+==========================================+{_RESET}")
    print(f"  {_DIM}Type 'q' at any prompt to quit.{_RESET}\n")

    while True:
        # -- Step 1: query name ------------------------------------------------
        try:
            query = input(f"  {_BOLD}Query name:{_RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye.")
            break

        if query.lower() in ("q", "quit", "exit"):
            print("  Bye.")
            break
        if not query:
            print("  (Please enter a name)\n")
            continue

        # -- Step 2: candidate list --------------------------------------------
        print(
            f"  {_BOLD}Candidates:{_RESET} "
            f"{_DIM}comma-separated names, a .txt file path, or Enter to skip{_RESET}"
        )
        try:
            raw = input("             ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye.")
            break

        if raw.lower() in ("q", "quit", "exit"):
            print("  Bye.")
            break

        candidates = _parse_candidates(raw)
        run(query, candidates, matcher)

        print()   # blank line before next round


# -- Main ----------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    # No arguments -> interactive mode
    if not args or args[0] in ("-i", "--interactive"):
        run_interactive()
        return

    query      = args[0].strip()
    raw_cands  = args[1].strip() if len(args) > 1 else ""
    candidates = _parse_candidates(raw_cands)
    matcher    = NameMatcher()
    run(query, candidates, matcher)


if __name__ == "__main__":
    main()
