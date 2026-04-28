#!/usr/bin/env python3
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = PROJECT_ROOT / "dist" / "jlpt_coverage.ankiaddon"
REQUIRED_FILES = {
    "__init__.py",
    "data/jlpt_vocab.csv",
    "jlpt_coverage/core.py",
    "python_i18n/i18n/__init__.py",
    "locale/en_US.json",
    "locale/zh_CN.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the packaged JLPT Coverage Anki add-on.")
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE, help="Path to .ankiaddon archive")
    return parser.parse_args()


def validate_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Invalid file in archive: {bad}")
        missing = sorted(REQUIRED_FILES - set(archive.namelist()))
        if missing:
            raise ValueError(f"Missing packaged files: {missing}")


def main() -> int:
    args = parse_args()
    path = args.archive.expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Missing add-on archive: {path}")
    validate_archive(path)
    print(f"Validated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
