#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jlpt_coverage.extract import load_verified_alternatives, write_vocab


SOURCE_REPO = Path("/Users/jarrettye/Codes/anki-jlpt-decks")
DEFAULT_SOURCE_CANDIDATES = (
    SOURCE_REPO / "deck-source" / "notes.csv",
    SOURCE_REPO / "eggrolls-JLPT10k-v3" / "notes.csv",
)
DEFAULT_OUTPUT = PROJECT_ROOT / "jlpt_coverage" / "data" / "jlpt_vocab.csv"
DEFAULT_VERIFIED_ALTERNATIVES = PROJECT_ROOT / "scripts" / "data" / "verified_word_alternatives.csv"


def default_source() -> Path:
    for source in DEFAULT_SOURCE_CANDIDATES:
        if source.exists():
            return source
    return DEFAULT_SOURCE_CANDIDATES[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the JLPT vocabulary columns needed by the coverage checker."
    )
    parser.add_argument("--source", type=Path, default=default_source(), help="Original eggrolls notes.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Project-local extracted CSV")
    parser.add_argument(
        "--verified-alternatives",
        type=Path,
        default=DEFAULT_VERIFIED_ALTERNATIVES,
        help="Reviewed word alternatives keyed by stable eggrolls note ID",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verified_alternatives = load_verified_alternatives(args.verified_alternatives.expanduser())
    count = write_vocab(
        args.source.expanduser(),
        args.output.expanduser(),
        verified_alternatives=verified_alternatives,
    )
    print(f"Wrote {count} JLPT vocabulary rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
