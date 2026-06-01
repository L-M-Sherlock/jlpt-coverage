from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from .core import (
    DEFAULT_NOTE_TYPES,
    format_summary,
    load_jlpt_entries,
    summarize,
    vocab_status_rows,
)
from .localization import configure_translations
from .reports import JLPT_EXPORT_LEVEL_ALIASES, export_level_filter, write_vocab_status_report
from .sqlite_collection import collect_anki_keys, copy_collection


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_JLPT_VOCAB = PACKAGE_DIR / "data" / "jlpt_vocab.csv"
DEFAULT_REPORT_DIR = Path.cwd() / "jlpt_coverage_reports"


def anki_base_dirs() -> list[Path]:
    candidates: list[Path] = []
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "Anki2")
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "Anki2")
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            candidates.append(Path(xdg_data_home) / "Anki2")
        candidates.append(Path.home() / ".local" / "share" / "Anki2")
    return candidates


def discover_profile_dirs() -> list[Path]:
    env_profile = os.environ.get("ANKI_PROFILE_DIR")
    if env_profile:
        return [Path(env_profile).expanduser()]

    profiles: list[Path] = []
    for base_dir in anki_base_dirs():
        if not base_dir.exists():
            continue
        for child in sorted(base_dir.iterdir()):
            if child.is_dir() and (child / "collection.anki2").exists():
                profiles.append(child)
    return profiles


def resolve_profile_dir(value: Path | None) -> Path:
    if value is not None:
        return value.expanduser()

    profiles = discover_profile_dirs()
    if not profiles:
        raise FileNotFoundError(
            "Could not find an Anki profile automatically. Pass --profile-dir or set ANKI_PROFILE_DIR."
        )
    if len(profiles) > 1:
        choices = "\n".join(f"- {profile}" for profile in profiles)
        raise ValueError(
            "Multiple Anki profiles were found. Pass --profile-dir or set ANKI_PROFILE_DIR.\n"
            f"{choices}"
        )
    return profiles[0]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check JLPT vocabulary coverage in an Anki collection copy."
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=None,
        help="Anki profile directory. Defaults to ANKI_PROFILE_DIR or auto-detected single profile.",
    )
    parser.add_argument(
        "--jlpt-vocab",
        type=Path,
        default=DEFAULT_JLPT_VOCAB,
        help="JLPT CSV. Defaults to the vocabulary bundled with the package.",
    )
    parser.add_argument(
        "--note-type",
        action="append",
        dest="note_types",
        help="Note type to include. Defaults to Lapis, Kaishi 1.5k, and Kaishi 1.5k zh-CH.",
    )
    match_group = parser.add_mutually_exclusive_group()
    match_group.add_argument(
        "--match-mode",
        choices=("word-or-reading", "word-and-reading", "word", "reading"),
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
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Report output directory. Default: ./jlpt_coverage_reports",
    )
    parser.add_argument(
        "--language",
        choices=("auto", "en_US", "zh_CN", "en", "zh"),
        default="auto",
        help="Output language. Default: auto.",
    )
    parser.add_argument("--no-report-files", action="store_true", help="Print only; do not write CSV report")
    parser.add_argument("--show-missing", type=int, default=10, help="Print this many missing words per level")
    parser.add_argument("--keep-copy", action="store_true", help="Keep the copied Anki DB under report-dir")
    export_group = parser.add_mutually_exclusive_group()
    export_group.add_argument(
        "--export-level",
        choices=tuple(JLPT_EXPORT_LEVEL_ALIASES),
        help="Only write this JLPT level to the CSV report. N4+N5 is accepted for legacy combined exports.",
    )
    export_group.add_argument(
        "--export-up-to",
        choices=tuple(JLPT_EXPORT_LEVEL_ALIASES),
        help="Write the target level and easier levels to the CSV report, e.g. N2 exports N2, N3, N4, and N5.",
    )
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
    args = parser.parse_args(argv)
    if args.match_mode is None:
        args.match_mode = "word-or-reading"
    return args


def run(args: argparse.Namespace) -> int:
    profile_dir = resolve_profile_dir(args.profile_dir)
    vocab_path = args.jlpt_vocab.expanduser()
    report_dir = args.report_dir.expanduser()
    note_type_names = tuple(args.note_types or DEFAULT_NOTE_TYPES)
    translate = configure_translations(args.language)
    status_level_filter = "all"
    if args.export_level:
        status_level_filter = export_level_filter("only", args.export_level)
    elif args.export_up_to:
        status_level_filter = export_level_filter("up-to", args.export_up_to)

    if not vocab_path.exists():
        raise FileNotFoundError(
            translate("cli-missing-vocab", path=str(vocab_path))
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
        summary, missing_rows, _unlearned_rows = summarize(
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
        print(
            format_summary(
                summary,
                metadata,
                missing_rows,
                show_missing=args.show_missing,
                translate=translate,
            )
        )

        if not args.no_report_files:
            status_path = write_vocab_status_report(
                report_dir,
                status_rows,
                level_filter=status_level_filter,
            )
            print()
            print(translate("cli-report-written"))
            print(f"- {status_path}")
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()

    return 0


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))
