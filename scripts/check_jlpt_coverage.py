#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jlpt_converge.core import (
    DEFAULT_NOTE_TYPES,
    format_summary,
    load_jlpt_entries,
    summarize,
    vocab_status_rows,
)
from jlpt_converge.reports import write_vocab_status_report
from jlpt_converge.sqlite_collection import collect_anki_keys, copy_collection


DEFAULT_PROFILE = Path("/Users/jarrettye/Library/Application Support/Anki2/JarrettYe")
DEFAULT_JLPT_VOCAB = PROJECT_ROOT / "data" / "jlpt_vocab.csv"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check JLPT vocabulary coverage in an Anki collection copy."
    )
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE, help="Anki profile directory")
    parser.add_argument("--jlpt-vocab", type=Path, default=DEFAULT_JLPT_VOCAB, help="Project-local JLPT CSV")
    parser.add_argument(
        "--note-type",
        action="append",
        dest="note_types",
        help="Note type to include. Defaults to Lapis, Kaishi 1.5k, and Kaishi 1.5k zh-CH.",
    )
    match_group = parser.add_mutually_exclusive_group()
    match_group.add_argument(
        "--match-mode",
        choices=("word-or-reading", "word", "reading"),
        default=None,
        help="How a JLPT row should be considered covered. Default: word-or-reading.",
    )
    match_group.add_argument(
        "--reading-only",
        action="store_const",
        const="reading",
        dest="match_mode",
        help="Only match JLPT reading against Anki reading fields.",
    )
    match_group.add_argument(
        "--strict-word",
        "--word-only",
        action="store_const",
        const="word",
        dest="match_mode",
        help="Only match JLPT word_plain against Anki word/expression fields.",
    )
    parser.add_argument(
        "--exclude-suspended",
        action="store_true",
        help="Only count notes with at least one non-suspended card.",
    )
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Report output directory")
    parser.add_argument("--no-report-files", action="store_true", help="Print only; do not write CSV report")
    parser.add_argument("--show-missing", type=int, default=10, help="Print this many missing words per level")
    parser.add_argument("--keep-copy", action="store_true", help="Keep the copied Anki DB under reports/collection-copy")
    parser.add_argument(
        "--by-frequency",
        action="store_true",
        help="Break coverage down by the frequency band from the JLPT source deck/tags.",
    )
    parser.add_argument(
        "--by-interval",
        action="store_true",
        help="Show Young/Mature coverage per level. Young is ivl < 21; Mature is ivl >= 21.",
    )
    args = parser.parse_args()
    if args.match_mode is None:
        args.match_mode = "word-or-reading"
    return args


def main() -> int:
    args = parse_args()
    profile_dir = args.profile_dir.expanduser()
    vocab_path = args.jlpt_vocab.expanduser()
    report_dir = args.report_dir.expanduser()
    note_type_names = tuple(args.note_types or DEFAULT_NOTE_TYPES)

    if not vocab_path.exists():
        raise FileNotFoundError(
            f"Missing project-local JLPT vocabulary file: {vocab_path}\n"
            "Run: python3 scripts/extract_jlpt_vocab.py"
        )

    db_copy, temp_ctx = copy_collection(
        profile_dir,
        keep_copy=args.keep_copy,
        report_dir=report_dir,
    )
    try:
        match_keys, anki_stats = collect_anki_keys(
            db_copy,
            note_type_names,
            exclude_suspended=args.exclude_suspended,
        )
        entries = load_jlpt_entries(vocab_path)
        summary, missing_rows, unlearned_rows = summarize(
            entries,
            match_keys,
            args.match_mode,
            by_frequency=args.by_frequency,
            by_interval=args.by_interval,
        )
        status_rows = vocab_status_rows(entries, match_keys, args.match_mode)

        metadata: dict[str, object] = {
            "profile_dir": str(profile_dir),
            "db_copy": str(db_copy) if args.keep_copy else "temporary copy deleted after run",
            "jlpt_vocab": str(vocab_path),
            "note_type_names": note_type_names,
            "match_mode": args.match_mode,
            "by_frequency": args.by_frequency,
            "by_interval": args.by_interval,
            "exclude_suspended": args.exclude_suspended,
            "anki_stats": anki_stats,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        print(format_summary(summary, metadata, missing_rows, show_missing=args.show_missing))

        if not args.no_report_files:
            status_path = write_vocab_status_report(
                report_dir,
                status_rows,
            )
            print()
            print("已写入报告:")
            print(f"- {status_path}")
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
