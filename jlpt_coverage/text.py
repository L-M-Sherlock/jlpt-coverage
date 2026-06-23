from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterable


JLPT_LEVELS = ("N1", "N2", "N3", "N4", "N5")

_MEDIA_RE = re.compile(r"\[(?:sound|anki:play:[^\]]+):[^\]]*\]", re.IGNORECASE)
_RT_RE = re.compile(r"<rt\b[^>]*>.*?</rt>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_BRACKET_READING_RE = re.compile(r"([一-龯々〆ヵヶ]+)\[([^\[\]]+)\]")
_SPLIT_RE = re.compile(r"[;；,，、/／|｜\n\r]+")
_CIRCLED_NUM_RE = re.compile(r"[⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚]")
_DROP_CHARS_RE = re.compile(
    r"[\s\u3000"
    r"\-‐‑‒–—―"
    r"~〜～"
    r"・･·"
    r"。．.、,，;；:："
    r"()（）［］\[\]{}｛｝<>〈〉《》「」『』“”\"'`]"
)
_PURE_KATAKANA_RE = re.compile(r"^[ァ-ヶー・ヽヾ]+$")
_KATAKANA_LETTER_RE = re.compile(r"[ァ-ヶ]")


def clean_markup(value: str) -> str:
    value = html.unescape(value or "")
    value = _MEDIA_RE.sub("", value)
    value = _RT_RE.sub("", value)
    value = _TAG_RE.sub("", value)
    return unicodedata.normalize("NFKC", value)


def bracket_readings(value: str) -> set[str]:
    clean = clean_markup(value)
    readings: set[str] = set()
    parts: list[str] = []
    last_end = 0
    for match in _BRACKET_READING_RE.finditer(clean):
        parts.append(clean[last_end : match.start()])
        readings.add(match.group(2))
        parts.append(match.group(2))
        last_end = match.end()
    parts.append(clean[last_end:])
    joined = "".join(parts)
    if joined != clean:
        readings.add(joined)
    return readings


def strip_furigana(value: str) -> str:
    clean = clean_markup(value)
    while True:
        stripped = _BRACKET_READING_RE.sub(r"\1", clean)
        if stripped == clean:
            return stripped
        clean = stripped


def kata_to_hira(value: str) -> str:
    chars: list[str] = []
    for char in value:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def is_katakana_word(value: str) -> bool:
    clean = strip_furigana(value).strip()
    return bool(_KATAKANA_LETTER_RE.search(clean)) and bool(_PURE_KATAKANA_RE.fullmatch(clean))


def normalize_key(value: str) -> str:
    value = strip_furigana(value)
    value = _CIRCLED_NUM_RE.sub("", value)
    value = _DROP_CHARS_RE.sub("", value)
    return value.lower()


def has_japanese(value: str) -> bool:
    return any(
        "\u3040" <= char <= "\u30ff"
        or "\u3400" <= char <= "\u9fff"
        or char in "々〆ヵヶ"
        for char in value
    )


def split_variants(value: str) -> Iterable[str]:
    clean = clean_markup(value)
    for part in _SPLIT_RE.split(clean):
        part = part.strip()
        if part:
            yield part


def text_keys(value: str, *, include_bracket_readings: bool = True) -> set[str]:
    keys: set[str] = set()
    candidates: list[str] = []
    for part in split_variants(value):
        candidates.append(part)
        candidates.append(strip_furigana(part))
        if include_bracket_readings:
            candidates.extend(bracket_readings(part))

    for candidate in candidates:
        key = normalize_key(candidate)
        if key and has_japanese(key):
            keys.add(key)
            keys.add(kata_to_hira(key))
    return keys


def level_from_deck_or_tags(deck: str, tags: str = "") -> str | None:
    source = f"{deck} {tags}"
    if "N4+N5" in source:
        return "N4+N5"
    for level in ("N1", "N2", "N3", "N4", "N5"):
        if re.search(rf"(?<![A-Z0-9]){level}(?![A-Z0-9])", source):
            return level
    return None


def frequency_from_deck_or_tags(deck: str, tags: str = "") -> str:
    source = f"{deck} {tags}"
    if "中低频" in source:
        return "中低频"
    if "高频" in source:
        return "高频"
    if "中频" in source:
        return "中频"
    if "低频" in source:
        return "低频"
    return "未分频"


def level_sort_key(level: str) -> tuple[int, str]:
    order = {"N1": 1, "N2": 2, "N3": 3, "N4": 4, "N5": 5, "N4+N5": 45}
    return order.get(level, 99), level


def frequency_sort_key(frequency: str) -> tuple[int, str]:
    order = {"高频": 1, "中频": 2, "中低频": 3, "低频": 4, "未分频": 9}
    return order.get(frequency, 99), frequency
