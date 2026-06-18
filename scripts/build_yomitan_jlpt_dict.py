#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jlpt_coverage.yomitan import build_dictionary


DEFAULT_VOCAB = PROJECT_ROOT / "jlpt_coverage" / "data" / "jlpt_vocab.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "yomitan-eggrolls-jlpt-vocab"
DEFAULT_ZIP = PROJECT_ROOT / "dist" / "eggrolls-jlpt-yomitan.zip"


def default_revision() -> str:
    return f"{dt.date.today():%Y.%m.%d}.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the eggrolls JLPT Yomitan term metadata dictionary."
    )
    parser.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB, help="Project-local JLPT vocabulary CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for index.json and term_meta_bank_*.json",
    )
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP, help="Importable Yomitan dictionary zip")
    parser.add_argument("--revision", default=default_revision(), help="Yomitan dictionary revision")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = build_dictionary(
        args.vocab.expanduser(),
        args.output_dir.expanduser(),
        args.zip.expanduser(),
        args.revision,
    )
    print(
        f"Wrote {data.entry_count} Yomitan metadata entries "
        f"from {data.source_rows} CSV rows to {args.output_dir}"
    )
    if data.duplicate_rows:
        print(f"Skipped {data.duplicate_rows} exact duplicate metadata rows")
    print(f"Packaged {args.zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
