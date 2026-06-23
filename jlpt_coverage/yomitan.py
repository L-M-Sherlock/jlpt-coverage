from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import JlptEntry, load_jlpt_entries


YOMITAN_LEVELS = ("N1", "N2", "N3", "N4", "N5")
YOMITAN_FREQUENCY_LEVELS = ("N1", "N2", "N3")
YOMITAN_BANK_FILENAMES = tuple(
    f"term_meta_bank_{index}.json" for index, _level in enumerate(YOMITAN_LEVELS, start=1)
)
YOMITAN_INDEX_FILENAME = "index.json"
YOMITAN_TITLE = "Eggrolls JLPT"
YOMITAN_SOURCE_URL = "https://github.com/5mdld/anki-jlpt-decks"
YOMITAN_PROJECT_URL = "https://github.com/L-M-Sherlock/jlpt-coverage"
YOMITAN_INDEX_URL = (
    "https://raw.githubusercontent.com/L-M-Sherlock/jlpt-coverage/"
    "refs/heads/main/yomitan-eggrolls-jlpt-vocab/index.json"
)
YOMITAN_DOWNLOAD_URL = (
    "https://github.com/L-M-Sherlock/jlpt-coverage/releases/latest/download/"
    "eggrolls-jlpt-yomitan.zip"
)

TermMetaEntry = list[Any]


@dataclass(frozen=True)
class YomitanDictionaryData:
    index: dict[str, Any]
    banks_by_level: dict[str, list[TermMetaEntry]]
    source_rows: int
    duplicate_rows: int

    @property
    def entry_count(self) -> int:
        return sum(len(entries) for entries in self.banks_by_level.values())


def default_index(revision: str) -> dict[str, Any]:
    return {
        "title": YOMITAN_TITLE,
        "author": "JLPT Coverage contributors; vocabulary data by 5mdld/eggrolls",
        "sequenced": False,
        "format": 3,
        "url": YOMITAN_SOURCE_URL,
        "isUpdatable": True,
        "indexUrl": YOMITAN_INDEX_URL,
        "downloadUrl": YOMITAN_DOWNLOAD_URL,
        "description": (
            "eggrolls JLPT10k vocabulary levels and frequency bands converted "
            "to a Yomitan term metadata dictionary."
        ),
        "attribution": (
            "Vocabulary data derived from the eggrolls JLPT10k deck by 5mdld.\n"
            f"Original deck: {YOMITAN_SOURCE_URL}\n\n"
            "The source vocabulary data is licensed under Creative Commons "
            "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). "
            "This derivative dictionary is for non-commercial use."
        ),
        "sourceLanguage": "ja",
        "targetLanguage": "zh",
        "revision": revision,
    }


def display_value_for_entry(entry: JlptEntry) -> str:
    if (
        entry.level in YOMITAN_FREQUENCY_LEVELS
        and entry.frequency
        and entry.frequency != "未分频"
    ):
        return f"{entry.level}{entry.frequency}"
    return entry.level


def term_meta_entry_for_entry(entry: JlptEntry) -> TermMetaEntry:
    return [
        entry.word_plain,
        "freq",
        {
            "reading": entry.matching_reading,
            "frequency": {
                "value": -1,
                "displayValue": display_value_for_entry(entry),
            },
        },
    ]


def dictionary_data(entries: list[JlptEntry], revision: str) -> YomitanDictionaryData:
    banks_by_level: dict[str, list[TermMetaEntry]] = {level: [] for level in YOMITAN_LEVELS}
    seen: set[tuple[str, str, str]] = set()
    duplicate_rows = 0

    for entry in entries:
        if entry.level not in banks_by_level:
            allowed = ", ".join(YOMITAN_LEVELS)
            raise ValueError(f"Unsupported Yomitan JLPT level: {entry.level}. Expected one of: {allowed}")

        display_value = display_value_for_entry(entry)
        key = (entry.word_plain, entry.matching_reading, display_value)
        if key in seen:
            duplicate_rows += 1
            continue

        seen.add(key)
        banks_by_level[entry.level].append(term_meta_entry_for_entry(entry))

    return YomitanDictionaryData(
        index=default_index(revision),
        banks_by_level=banks_by_level,
        source_rows=len(entries),
        duplicate_rows=duplicate_rows,
    )


def expected_filenames() -> tuple[str, ...]:
    return (YOMITAN_INDEX_FILENAME, *YOMITAN_BANK_FILENAMES)


def bank_filename_for_level(level: str) -> str:
    try:
        index = YOMITAN_LEVELS.index(level) + 1
    except ValueError as error:
        allowed = ", ".join(YOMITAN_LEVELS)
        raise ValueError(f"Unsupported Yomitan JLPT level: {level}. Expected one of: {allowed}") from error
    return f"term_meta_bank_{index}.json"


def bank_level_for_filename(filename: str) -> str:
    try:
        index = YOMITAN_BANK_FILENAMES.index(filename)
    except ValueError as error:
        expected = ", ".join(YOMITAN_BANK_FILENAMES)
        raise ValueError(f"Unsupported Yomitan bank filename: {filename}. Expected one of: {expected}") from error
    return YOMITAN_LEVELS[index]


def write_dictionary_files(data: YomitanDictionaryData, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_file in output_dir.glob("term_meta_bank_*.json"):
        stale_file.unlink()

    with (output_dir / YOMITAN_INDEX_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(data.index, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    for level in YOMITAN_LEVELS:
        path = output_dir / bank_filename_for_level(level)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data.banks_by_level[level], handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")


def package_dictionary(output_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for filename in expected_filenames():
            archive.write(output_dir / filename, arcname=filename)


def build_dictionary(vocab_path: Path, output_dir: Path, zip_path: Path, revision: str) -> YomitanDictionaryData:
    data = dictionary_data(load_jlpt_entries(vocab_path), revision)
    write_dictionary_files(data, output_dir)
    package_dictionary(output_dir, zip_path)
    return data


def read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_dictionary_dir(output_dir: Path) -> YomitanDictionaryData:
    index = read_json_file(output_dir / YOMITAN_INDEX_FILENAME)
    banks_by_level: dict[str, list[TermMetaEntry]] = {}
    for filename in YOMITAN_BANK_FILENAMES:
        level = bank_level_for_filename(filename)
        banks_by_level[level] = read_json_file(output_dir / filename)
    return YomitanDictionaryData(
        index=index,
        banks_by_level=banks_by_level,
        source_rows=0,
        duplicate_rows=0,
    )


def actual_entry_keys(data: YomitanDictionaryData) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for entries in data.banks_by_level.values():
        for term, _kind, metadata in entries:
            keys.add((term, metadata["reading"], metadata["frequency"]["displayValue"]))
    return keys


def duplicate_entry_keys(data: YomitanDictionaryData) -> dict[tuple[str, str, str], int]:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for entries in data.banks_by_level.values():
        for term, _kind, metadata in entries:
            counts[(term, metadata["reading"], metadata["frequency"]["displayValue"])] += 1
    return {key: count for key, count in counts.items() if count > 1}
