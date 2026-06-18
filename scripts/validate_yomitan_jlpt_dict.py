#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jlpt_coverage.core import load_jlpt_entries
from jlpt_coverage.yomitan import (
    YOMITAN_BANK_FILENAMES,
    YOMITAN_INDEX_FILENAME,
    YOMITAN_LEVELS,
    YOMITAN_SOURCE_URL,
    YOMITAN_TITLE,
    actual_entry_keys,
    dictionary_data,
    duplicate_entry_keys,
    expected_filenames,
    load_dictionary_dir,
)


DEFAULT_VOCAB = PROJECT_ROOT / "jlpt_coverage" / "data" / "jlpt_vocab.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "yomitan-eggrolls-jlpt-vocab"
DEFAULT_ZIP = PROJECT_ROOT / "dist" / "eggrolls-jlpt-yomitan.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the eggrolls JLPT Yomitan dictionary.")
    parser.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB, help="Project-local JLPT vocabulary CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory containing index.json and term_meta_bank_*.json",
    )
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP, help="Importable Yomitan dictionary zip")
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_index(index: dict[str, Any]) -> None:
    require(index.get("title") == YOMITAN_TITLE, "index.json has an unexpected title")
    require(index.get("format") == 3, "index.json must use Yomitan format 3")
    require(index.get("url") == YOMITAN_SOURCE_URL, "index.json must point to the eggrolls source URL")
    require(index.get("sequenced") is False, "index.json must set sequenced to false")
    require(bool(index.get("revision")), "index.json is missing revision")
    require(index.get("isUpdatable") is True, "index.json must set isUpdatable to true")
    require(bool(index.get("indexUrl")), "index.json is missing indexUrl")
    require(bool(index.get("downloadUrl")), "index.json is missing downloadUrl")
    require("CC BY-NC 4.0" in index.get("attribution", ""), "index.json must mention CC BY-NC 4.0")


def validate_meta_entry(entry: Any, filename: str, index: int) -> None:
    require(isinstance(entry, list), f"{filename}[{index}] must be an array")
    require(len(entry) == 3, f"{filename}[{index}] must contain exactly 3 items")
    term, kind, metadata = entry
    require(isinstance(term, str) and term, f"{filename}[{index}] has an invalid term")
    require(kind == "freq", f"{filename}[{index}] must be freq metadata")
    require(isinstance(metadata, dict), f"{filename}[{index}] metadata must be an object")
    require(isinstance(metadata.get("reading"), str), f"{filename}[{index}] has an invalid reading")
    frequency = metadata.get("frequency")
    require(isinstance(frequency, dict), f"{filename}[{index}] frequency must be an object")
    require(frequency.get("value") == -1, f"{filename}[{index}] frequency value must be -1")
    display_value = frequency.get("displayValue")
    require(isinstance(display_value, str) and display_value, f"{filename}[{index}] has no displayValue")
    if display_value.startswith(("N1", "N2", "N3")):
        require(
            display_value in {
                "N1高频",
                "N1中频",
                "N1中低频",
                "N1低频",
                "N1",
                "N2高频",
                "N2中频",
                "N2中低频",
                "N2低频",
                "N2",
                "N3高频",
                "N3中频",
                "N3中低频",
                "N3低频",
                "N3",
            },
            f"{filename}[{index}] has an unexpected displayValue: {display_value}",
        )
    else:
        require(display_value in {"N4", "N5"}, f"{filename}[{index}] has an unexpected displayValue")


def validate_zip(zip_path: Path) -> dict[str, Any]:
    require(zip_path.exists(), f"Missing Yomitan zip: {zip_path}")
    expected_names = set(expected_filenames())
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        require(names == expected_names, f"Zip entries differ from expected root files: {sorted(names)}")
        require(all("/" not in name for name in names), "Zip files must be at the archive root")
        return {name: json.loads(archive.read(name).decode("utf-8")) for name in sorted(names)}


def main() -> int:
    args = parse_args()
    vocab_path = args.vocab.expanduser()
    output_dir = args.output_dir.expanduser()
    zip_path = args.zip.expanduser()

    require(vocab_path.exists(), f"Missing vocabulary CSV: {vocab_path}")
    require(output_dir.exists(), f"Missing Yomitan dictionary directory: {output_dir}")

    actual = load_dictionary_dir(output_dir)
    validate_index(actual.index)
    for filename in YOMITAN_BANK_FILENAMES:
        path = output_dir / filename
        require(path.exists(), f"Missing Yomitan bank file: {path}")

    for level in YOMITAN_LEVELS:
        filename = f"term_meta_bank_{YOMITAN_LEVELS.index(level) + 1}.json"
        for index, entry in enumerate(actual.banks_by_level[level]):
            validate_meta_entry(entry, filename, index)

    expected = dictionary_data(load_jlpt_entries(vocab_path), actual.index["revision"])
    require(
        actual.banks_by_level == expected.banks_by_level,
        "Yomitan bank contents do not match the vocabulary CSV",
    )
    require(
        not duplicate_entry_keys(actual),
        "Yomitan dictionary contains duplicate term/reading/displayValue metadata entries",
    )
    require(
        actual_entry_keys(actual) == actual_entry_keys(expected),
        "Yomitan metadata keys do not match expected CSV-derived keys",
    )

    zipped = validate_zip(zip_path)
    require(zipped[YOMITAN_INDEX_FILENAME] == actual.index, "Zip index.json differs from output directory")
    for filename in YOMITAN_BANK_FILENAMES:
        level = YOMITAN_LEVELS[YOMITAN_BANK_FILENAMES.index(filename)]
        require(zipped[filename] == actual.banks_by_level[level], f"Zip {filename} differs from output directory")

    print(
        f"Validated {actual.entry_count} Yomitan metadata entries "
        f"across {len(YOMITAN_BANK_FILENAMES)} banks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
