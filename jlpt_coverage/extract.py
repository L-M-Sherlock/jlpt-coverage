from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from .text import frequency_from_deck_or_tags, level_from_deck_or_tags, strip_furigana


OUTPUT_FIELDS = (
    "level",
    "frequency",
    "word_plain",
    "reading",
)


def iter_vocab_rows(source: Path) -> Iterator[dict[str, str]]:
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

            yield {
                "level": level,
                "frequency": frequency_from_deck_or_tags(row[1], tags),
                "word_plain": strip_furigana(row[3].strip()).strip(),
                "reading": row[6].strip(),
            }


def write_vocab(source: Path, output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in iter_vocab_rows(source):
            writer.writerow(row)
            count += 1
    return count
