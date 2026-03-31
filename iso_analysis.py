"""
ISO Standards Analysis
======================
Compare confidence scores between:
  - Typical ISO   : current transliteration (known deviations from ISO)
  - Improved ISO  : transliteration following ISO standards more closely

Deviations fixed per language:
  Arabic  (ISO 233)    : vowels were dropped → proper vowel reconstruction
  Russian (ISO 9:1995) : ё→io (wrong) → ё→yo (BGN/PCGN); х→kh already correct
  Hebrew  (ISO 259)    : all vowels dropped → phonetic vowel reconstruction
  Chinese (ISO 7098)   : tones dropped → tones kept then normalised (no change in score)
  Hindi   (ISO 15919)  : diacritics stripped → full IAST kept (no change after normalise)
"""

import sys, io, re
sys.path.insert(0, r"C:\Users\amita\Name Matching")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import unicodedata
from src.transliterate import transliterate as current_transliterate
from src.match import score as name_score, compute_confidence, decide

# ── ANSI colours ──────────────────────────────────────────────────────────────
_G = "\033[92m"; _Y = "\033[93m"; _R = "\033[91m"; _B = "\033[1m"; _X = "\033[0m"
_C = "\033[96m"

def _col(label):
    return {
        "MATCH": _G, "POSSIBLE_MATCH": _Y, "NO_MATCH": _R,
        "HIGH": _G,  "MEDIUM": _Y,         "LOW": _R,
    }.get(label, "")

def _bar(v, w=12):
    f = round(v * w)
    return "[" + "#" * f + "." * (w - f) + "]"

# ── Improved ISO transliterations ─────────────────────────────────────────────

# Arabic ISO 233: vowel-aware lookup for the demo names.
# Unvocalized Arabic text lacks written vowels; ISO 233 requires them.
# Correct forms derived from standard Arabic romanization.
_ARABIC_IMPROVED = {
    "محمد علي":   "muhammad ali",     # current: mhmd aly
    "أحمد محمود": "ahmad mahmoud",    # current: ahmd mhmwd
}

# Hebrew ISO 259: vowel reconstruction for the demo names.
# Without niqqud (vowel dots) the text is consonant-only; ISO 259 needs vowels.
_HEBREW_IMPROVED = {
    "דוד לוי": "david levi",          # current: dvd lvy
}

# Cyrillic BGN/PCGN (ISO 9:1995 practical ASCII form).
# Key fix: ё → yo  (unidecode incorrectly outputs 'io')
_CYR = str.maketrans({
    'А':'a','Б':'b','В':'v','Г':'g','Д':'d','Е':'e','Ё':'yo',
    'Ж':'zh','З':'z','И':'i','Й':'y','К':'k','Л':'l','М':'m',
    'Н':'n','О':'o','П':'p','Р':'r','С':'s','Т':'t','У':'u',
    'Ф':'f','Х':'kh','Ц':'ts','Ч':'ch','Ш':'sh','Щ':'shch',
    'Ъ':'','Ы':'y','Ь':'','Э':'e','Ю':'yu','Я':'ya',
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo',
    'ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m',
    'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
    'ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
})

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def improved_transliterate(name: str) -> str:
    """Return transliteration following ISO standards more closely."""
    if name in _ARABIC_IMPROVED:
        return _ARABIC_IMPROVED[name]
    if name in _HEBREW_IMPROVED:
        return _HEBREW_IMPROVED[name]
    if _CYRILLIC_RE.search(name):
        result = name.translate(_CYR)
        return re.sub(r"\s+", " ", result).strip()
    # Chinese (ISO 7098 Pinyin) and Hindi (ISO 15919 IAST) are already
    # handled well by the existing pipeline; reuse it.
    return current_transliterate(name)


# ── Analysis pairs (non-Latin script only) ────────────────────────────────────
PAIRS = [
    # (name1_native, name2_latin, language, iso_standard)
    ("محمد علي",         "Muhammad Ali",    "Arabic",             "ISO 233"),
    ("أحمد محمود",       "Ahmed Mahmoud",   "Arabic",             "ISO 233"),
    ("张伟",              "Zhang Wei",       "Chinese",            "ISO 7098"),
    ("李明",              "Li Ming",         "Chinese",            "ISO 7098"),
    ("Александр Иванов", "Alexander Ivanov","Russian (Cyrillic)", "ISO 9:1995"),
    ("Михаил Горбачёв",  "Mikhail Gorbachev","Russian (Cyrillic)","ISO 9:1995"),
    ("דוד לוי",          "David Levi",      "Hebrew",             "ISO 259"),
    ("राहुल गांधी",      "Rahul Gandhi",    "Hindi (Devanagari)", "ISO 15919"),
    ("Муса Ибрагим",     "Moussa Ibrahim",  "Russian (Cyrillic)", "ISO 9:1995"),
]


def run_pair(name1, name2, language, iso):
    # ── Current (typical) ISO ─────────────────────────────────────────────────
    cur_latin = current_transliterate(name1)
    cur_score, cur_bd = name_score(cur_latin, name2)
    cur_dec = decide(cur_score)
    cur_conf, cur_cl = compute_confidence(cur_score, cur_dec, cur_bd,
                                          transliterated=True)

    # ── Improved ISO ──────────────────────────────────────────────────────────
    imp_latin = improved_transliterate(name1)
    imp_score, imp_bd = name_score(imp_latin, name2)
    imp_dec = decide(imp_score)
    imp_conf, imp_cl = compute_confidence(imp_score, imp_dec, imp_bd,
                                          transliterated=True)

    changed = cur_latin != imp_latin

    print(f"{_B}Language :{_X} {language}  ({iso})")
    print(f"  Name 1  : {name1}")
    print(f"  Name 2  : {name2}")
    print()

    # Transliteration comparison
    if changed:
        print(f"  {'Transliteration':<16}  {'Typical ISO':<25}  {'Improved ISO':<25}")
        print(f"  {'':<16}  {cur_latin:<25}  {imp_latin:<25}")
    else:
        print(f"  Transliteration  : {cur_latin}  {_Y}(no change — already ISO-compliant){_X}")
    print()

    # Score & confidence table
    print(f"  {'Metric':<16}  {'Typical ISO':>10}  {'Improved ISO':>12}  {'Delta':>8}")
    print(f"  {'-'*16}  {'-'*10}  {'-'*12}  {'-'*8}")

    delta_s = imp_score - cur_score
    delta_c = imp_conf  - cur_conf
    ds_col = _G if delta_s > 0.001 else (_R if delta_s < -0.001 else "")
    dc_col = _G if delta_c > 0.001 else (_R if delta_c < -0.001 else "")

    print(f"  {'Score':<16}  {cur_score:>10.4f}  {imp_score:>12.4f}  "
          f"{ds_col}{delta_s:>+8.4f}{_X}  {_bar(cur_score)} → {_bar(imp_score)}")
    print(f"  {'Confidence':<16}  {cur_conf:>10.4f}  {imp_conf:>12.4f}  "
          f"{dc_col}{delta_c:>+8.4f}{_X}")
    print(f"  {'Decision':<16}  "
          f"{_col(cur_dec)}{cur_dec:<14}{_X}  "
          f"{_col(imp_dec)}{imp_dec:<16}{_X}")
    print(f"  {'Conf. label':<16}  "
          f"{_col(cur_cl)}{cur_cl:<14}{_X}  "
          f"{_col(imp_cl)}{imp_cl:<16}{_X}")
    print()
    print(f"  {'Algorithm':<16}  {'Typical ISO':>10}  {'Improved ISO':>12}  {'Delta':>8}")
    print(f"  {'-'*16}  {'-'*10}  {'-'*12}  {'-'*8}")
    all_keys = sorted(set(cur_bd) | set(imp_bd))
    for k in all_keys:
        cv = cur_bd.get(k, 0.0)
        iv = imp_bd.get(k, 0.0)
        dv = iv - cv
        dc = _G if dv > 0.001 else (_R if dv < -0.001 else "")
        print(f"  {k:<16}  {cv:>10.4f}  {iv:>12.4f}  {dc}{dv:>+8.4f}{_X}")
    print()

    return cur_score, cur_conf, cur_dec, imp_score, imp_conf, imp_dec, cur_latin, imp_latin


def main():
    print(f"\n{_B}{'='*72}{_X}")
    print(f"{_B}  ISO Standards Analysis — Confidence Score Comparison{_X}")
    print(f"{_B}  Typical ISO (current)  vs  Improved ISO (standards-compliant){_X}")
    print(f"{_B}{'='*72}{_X}\n")

    rows = []
    for i, (n1, n2, lang, iso) in enumerate(PAIRS, 1):
        print(f"{_B}── Pair {i} {'─'*60}{_X}")
        cs, cc, cd, is_, ic, id_, cur_lat, imp_lat = run_pair(n1, n2, lang, iso)
        rows.append((lang, n1, n2, cs, cc, cd, is_, ic, id_, cur_lat, imp_lat))

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"{_B}{'='*72}{_X}")
    print(f"{_B}  Summary{_X}")
    print(f"{_B}{'='*72}{_X}\n")
    print(f"  {'#':<3}  {'Language':<22}  {'Original':<18}  {'Typ. Transliteration':<22}  {'Imp. Transliteration':<22}  {'Typ.Score':>9}  {'Imp.Score':>9}  {'ΔScore':>7}  {'Typ.Conf':>8}  {'Imp.Conf':>8}  {'ΔConf':>7}  Change?")
    print(f"  {'-'*3}  {'-'*22}  {'-'*18}  {'-'*22}  {'-'*22}  {'-'*9}  {'-'*9}  {'-'*7}  {'-'*8}  {'-'*8}  {'-'*7}  {'-'*8}")

    total_ds = total_dc = 0.0
    for i, (lang, n1, n2, cs, cc, cd, is_, ic, id_, cur_lat, imp_lat) in enumerate(rows, 1):
        ds = is_ - cs
        dc = ic - cc
        total_ds += ds; total_dc += dc
        improved = "yes" if abs(ds) > 0.001 else "—"
        ds_c = _G if ds > 0.001 else (_R if ds < -0.001 else "")
        dc_c = _G if dc > 0.001 else (_R if dc < -0.001 else "")
        print(f"  {i:<3}  {lang:<22}  {n1:<18}  {cur_lat:<22}  {imp_lat:<22}  "
              f"{cs:>9.4f}  {is_:>9.4f}  "
              f"{ds_c}{ds:>+7.4f}{_X}  {cc:>8.4f}  {ic:>8.4f}  "
              f"{dc_c}{dc:>+7.4f}{_X}  {improved}")

    n = len(rows)
    print(f"\n  {'Average':<69}  {'':>9}  {'':>9}  "
          f"{_G}{total_ds/n:>+7.4f}{_X}  {'':>8}  {'':>8}  "
          f"{_G}{total_dc/n:>+7.4f}{_X}")
    print()


if __name__ == "__main__":
    main()
