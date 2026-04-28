#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jlpt_coverage.extract import write_vocab


DEFAULT_SOURCE = Path(
    "/Users/jarrettye/Codes/anki-jlpt-decks/eggrolls-JLPT10k-v3/notes.csv"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "jlpt_coverage" / "data" / "jlpt_vocab.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the JLPT vocabulary columns needed by the coverage checker."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Original eggrolls notes.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Project-local extracted CSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    count = write_vocab(args.source.expanduser(), args.output.expanduser())
    print(f"Wrote {count} JLPT vocabulary rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
