from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from .text import (
    clean_markup,
    frequency_from_deck_or_tags,
    level_from_deck_or_tags,
    strip_furigana,
    strip_placeholder_marks,
)


OUTPUT_FIELDS = (
    "level",
    "frequency",
    "word_plain",
    "reading",
    "word_alternatives",
)

_KANJI_RE = re.compile(r"[一-龯々〆ヵヶ]")
_JAPANESE_WORD_RE = re.compile(r"^[一-龯々〆ヵヶぁ-ゖァ-ヺー~〜～]+$")
_COMMON_GLYPH_VARIANTS = str.maketrans({"摑": "掴", "剝": "剥"})
_JMDICT_EVIDENCE_RE = re.compile(r"^jmdict:[1-9][0-9]*$")


@dataclass(frozen=True)
class VerifiedAlternative:
    term: str
    reading: str
    evidence: str

    def encoded(self, source_reading: str) -> str:
        if self.reading and self.reading != strip_placeholder_marks(source_reading):
            return f"{self.term}[{self.reading}]"
        return self.term


def _glyph_variant_key(value: str) -> str:
    return value.translate(_COMMON_GLYPH_VARIANTS)


def kanji_alternative_forms(vocab_plus: str) -> tuple[str, ...]:
    """Extract a conservative list of written variants from VocabPlus.

    VocabPlus is a mixed-purpose field, so only its leading clause is considered.
    Callers further restrict this to rows whose frequency labels need disambiguation.
    """
    leading_clause = re.split(r"[;；]", clean_markup(vocab_plus), maxsplit=1)[0].strip()
    alternatives: list[str] = []
    for candidate in re.split(r"[・･]", leading_clause):
        candidate = re.sub(r"\s+", "", strip_furigana(candidate)).strip()
        if not candidate or not _JAPANESE_WORD_RE.fullmatch(candidate):
            continue
        if not _KANJI_RE.search(candidate):
            continue
        if candidate not in alternatives:
            alternatives.append(candidate)
    return tuple(alternatives)


def load_verified_alternatives(path: Path) -> dict[str, tuple[VerifiedAlternative, ...]]:
    alternatives_by_note_id: dict[str, list[VerifiedAlternative]] = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"note_id", "word_alternative", "reading", "evidence"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

        for line_no, row in enumerate(reader, start=2):
            note_id = (row.get("note_id") or "").strip()
            alternative = re.sub(r"\s+", "", strip_furigana(row.get("word_alternative") or "")).strip()
            reading = strip_placeholder_marks(row.get("reading") or "")
            evidence = (row.get("evidence") or "").strip()
            if not note_id:
                raise ValueError(f"{path}:{line_no} has an empty note_id")
            if not alternative or not _JAPANESE_WORD_RE.fullmatch(alternative):
                raise ValueError(f"{path}:{line_no} has an invalid word_alternative: {alternative!r}")
            if reading and not _JAPANESE_WORD_RE.fullmatch(reading):
                raise ValueError(f"{path}:{line_no} has an invalid reading: {reading!r}")
            if evidence != "vocab_plus" and not _JMDICT_EVIDENCE_RE.fullmatch(evidence):
                raise ValueError(f"{path}:{line_no} has invalid evidence: {evidence!r}")
            verified = VerifiedAlternative(alternative, reading, evidence)
            if verified not in alternatives_by_note_id[note_id]:
                alternatives_by_note_id[note_id].append(verified)

    return {note_id: tuple(alternatives) for note_id, alternatives in alternatives_by_note_id.items()}


def _source_vocab_rows(source: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for line_no, row in enumerate(reader, start=1):
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 39:
                raise ValueError(f"{source}:{line_no} has {len(row)} columns; expected at least 39")

            tags = row[38].strip()
            level = level_from_deck_or_tags(row[1], tags)
            if not level:
                continue

            rows.append(
                {
                    "level": level,
                    "note_id": row[2].strip(),
                    "frequency": frequency_from_deck_or_tags(row[1], tags),
                    "word_plain": strip_furigana(row[3].strip()).strip(),
                    "reading": row[6].strip(),
                    "vocab_plus": row[9].strip(),
                }
            )
    return rows


def iter_vocab_rows(
    source: Path,
    *,
    verified_alternatives: Mapping[str, Iterable[VerifiedAlternative]] | None = None,
) -> Iterator[dict[str, str]]:
    rows = _source_vocab_rows(source)
    verified_alternatives = verified_alternatives or {}
    source_note_ids = {row["note_id"] for row in rows}
    unknown_note_ids = sorted(set(verified_alternatives) - source_note_ids)
    if unknown_note_ids:
        raise ValueError(
            "Verified word alternatives refer to missing source note IDs: " + ", ".join(unknown_note_ids)
        )

    rows_by_note_id = {row["note_id"]: row for row in rows}
    for note_id, alternatives in verified_alternatives.items():
        source_candidates = kanji_alternative_forms(rows_by_note_id[note_id]["vocab_plus"])
        source_keys = {_glyph_variant_key(candidate) for candidate in source_candidates}
        invalid = [
            alternative.term
            for alternative in alternatives
            if alternative.evidence == "vocab_plus" and _glyph_variant_key(alternative.term) not in source_keys
        ]
        if invalid:
            raise ValueError(
                f"Verified word alternatives for {note_id} are not present in source VocabPlus: "
                + ", ".join(invalid)
            )

    frequencies_by_term: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        key = (row["level"], row["word_plain"], row["reading"])
        frequencies_by_term[key].add(row["frequency"])

    conflicting_terms = {key for key, frequencies in frequencies_by_term.items() if len(frequencies) > 1}
    for row in rows:
        key = (row["level"], row["word_plain"], row["reading"])
        alternatives = list(kanji_alternative_forms(row["vocab_plus"]) if key in conflicting_terms else ())
        for verified in verified_alternatives.get(row["note_id"], ()):
            alternative = verified.encoded(row["reading"])
            if alternative not in alternatives:
                alternatives.append(alternative)
        yield {
            "level": row["level"],
            "frequency": row["frequency"],
            "word_plain": row["word_plain"],
            "reading": row["reading"],
            "word_alternatives": ";".join(alternatives),
        }


def write_vocab(
    source: Path,
    output: Path,
    *,
    verified_alternatives: Mapping[str, Iterable[VerifiedAlternative]] | None = None,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in iter_vocab_rows(source, verified_alternatives=verified_alternatives):
            writer.writerow(row)
            count += 1
    return count
