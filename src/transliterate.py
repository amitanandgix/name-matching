"""Offline, script-aware transliteration to Latin script.

Script routing:
  Devanagari  -> indic_transliteration (IAST) + schwa deletion
  CJK/Chinese -> pypinyin (Pinyin)
  Arabic      -> custom letter map (ISO 233 / common romanization)
  Everything  -> unidecode
"""

import re
import unicodedata
from unidecode import unidecode

_cache: dict[str, str] = {}

# ── Unicode block detectors ───────────────────────────────────────────────────
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_CJK_RE        = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF\U00020000-\U0002A6DF]")
_ARABIC_RE     = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


# ── Arabic letter map (ISO 233 / common English romanization) ─────────────────
_ARABIC_MAP = str.maketrans({
    "\u0627": "a",   # ا alif
    "\u0628": "b",   # ب ba
    "\u062A": "t",   # ت ta
    "\u062B": "th",  # ث tha
    "\u062C": "j",   # ج jeem
    "\u062D": "h",   # ح ha
    "\u062E": "kh",  # خ kha
    "\u062F": "d",   # د dal
    "\u0630": "dh",  # ذ dhal
    "\u0631": "r",   # ر ra
    "\u0632": "z",   # ز zain
    "\u0633": "s",   # س seen
    "\u0634": "sh",  # ش sheen
    "\u0635": "s",   # ص sad
    "\u0636": "d",   # ض dad
    "\u0637": "t",   # ط ta
    "\u0638": "z",   # ظ za
    "\u0639": "a",   # ع ain
    "\u063A": "gh",  # غ ghain
    "\u0641": "f",   # ف fa
    "\u0642": "q",   # ق qaf
    "\u0643": "k",   # ك kaf
    "\u0644": "l",   # ل lam
    "\u0645": "m",   # م meem
    "\u0646": "n",   # ن noon
    "\u0647": "h",   # ه ha
    "\u0648": "w",   # و waw
    "\u064A": "y",   # ي ya
    "\u0629": "a",   # ة ta marbuta
    "\u0623": "a",   # أ hamza above
    "\u0625": "i",   # إ hamza below
    "\u0622": "aa",  # آ alif madda
    "\u0626": "y",   # ئ ya with hamza
    "\u0624": "w",   # ؤ waw with hamza
    "\u0621": "",    # ء hamza (silent)
    "\u0649": "a",   # ى alif maqsura
    # Diacritics (harakat) — drop them
    "\u064E": "",    # fatha (a)
    "\u064F": "",    # damma (u)
    "\u0650": "",    # kasra (i)
    "\u0651": "",    # shadda (double)
    "\u0652": "",    # sukun
    "\u064B": "",    # tanwin fath
    "\u064C": "",    # tanwin damm
    "\u064D": "",    # tanwin kasr
})


def _transliterate_arabic(text: str) -> str:
    result = text.translate(_ARABIC_MAP)
    # collapse multiple spaces, strip stray chars
    result = re.sub(r"[^\w\s]", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


# ── Devanagari (Hindi) ────────────────────────────────────────────────────────
def _remove_diacritics(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _transliterate_devanagari(text: str) -> str:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as iast_trans

    latin = iast_trans(text, sanscript.DEVANAGARI, sanscript.IAST)
    latin = _remove_diacritics(latin)
    tokens = latin.split()
    cleaned = []
    for token in tokens:
        if len(token) > 2 and token.endswith("a"):
            token = token[:-1]
        token = re.sub(r"m([bcdfghjklmnpqrstvwxyz])", r"n\1", token)
        cleaned.append(token)
    return " ".join(cleaned)


# ── Mandarin (CJK) ───────────────────────────────────────────────────────────
def _transliterate_cjk(text: str) -> str:
    from pypinyin import lazy_pinyin, Style
    # NORMAL style = no tone marks, plain ASCII Pinyin
    return " ".join(lazy_pinyin(text, style=Style.NORMAL))


# ── Latin check ───────────────────────────────────────────────────────────────
def _is_latin_char(char: str) -> bool:
    try:
        name = unicodedata.name(char)
        return name.startswith(("LATIN", "MODIFIER LETTER"))
    except ValueError:
        return False


def has_non_latin(text: str) -> bool:
    return any(c.isalpha() and not _is_latin_char(c) for c in text)


# ── Public API ────────────────────────────────────────────────────────────────
def transliterate(name: str) -> str:
    """Return the Latin-script version of *name* using the best offline method
    for each script. Results are cached."""
    if not has_non_latin(name):
        return name

    if name in _cache:
        return _cache[name]

    if _DEVANAGARI_RE.search(name):
        result = _transliterate_devanagari(name)
    elif _CJK_RE.search(name):
        result = _transliterate_cjk(name)
    elif _ARABIC_RE.search(name):
        result = _transliterate_arabic(name)
    else:
        result = unidecode(name).strip()

    _cache[name] = result
    return result
