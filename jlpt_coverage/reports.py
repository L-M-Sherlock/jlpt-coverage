from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .core import vocab_status_fieldnames


JLPT_EXPORT_LEVELS = ("N1", "N2", "N3", "N4", "N5")
JLPT_LEGACY_COMBINED_LEVEL = "N4+N5"
JLPT_EXPORT_LEVEL_ALIASES = {
    "N1": "N1",
    "N2": "N2",
    "N3": "N3",
    "N4": "N4",
    "N5": "N5",
    JLPT_LEGACY_COMBINED_LEVEL: JLPT_LEGACY_COMBINED_LEVEL,
}


def normalize_export_level(level: str) -> str:
    normalized = level.strip().upper()
    if normalized not in JLPT_EXPORT_LEVEL_ALIASES:
        allowed = ", ".join(JLPT_EXPORT_LEVEL_ALIASES)
        raise ValueError(f"Invalid JLPT export level: {level}. Expected one of: {allowed}")
    return JLPT_EXPORT_LEVEL_ALIASES[normalized]


def export_level_filter(mode: str, level: str | None = None) -> str:
    if mode == "all":
        return "all"
    if level is None:
        raise ValueError(f"Export level is required for mode: {mode}")
    return f"{mode}:{normalize_export_level(level)}"


def export_levels_for_filter(level_filter: str) -> set[str]:
    if not level_filter or level_filter == "all":
        return {*JLPT_EXPORT_LEVELS, JLPT_LEGACY_COMBINED_LEVEL}
    mode, _, raw_level = level_filter.partition(":")
    level = normalize_export_level(raw_level)
    if mode == "only":
        if level == JLPT_LEGACY_COMBINED_LEVEL:
            return {"N4", "N5", JLPT_LEGACY_COMBINED_LEVEL}
        if level in {"N4", "N5"}:
            return {level, JLPT_LEGACY_COMBINED_LEVEL}
        return {level}
    if mode == "up-to":
        if level == JLPT_LEGACY_COMBINED_LEVEL:
            return {"N4", "N5", JLPT_LEGACY_COMBINED_LEVEL}
        start = JLPT_EXPORT_LEVELS.index(level)
        levels = set(JLPT_EXPORT_LEVELS[start:])
        if {"N4", "N5"} & levels:
            levels.add(JLPT_LEGACY_COMBINED_LEVEL)
        return levels
    raise ValueError(f"Invalid export level filter: {level_filter}")


def filter_vocab_status_rows(
    rows: list[dict[str, str]],
    level_filter: str,
) -> list[dict[str, str]]:
    levels = export_levels_for_filter(level_filter)
    return [row for row in rows if row.get("level") in levels]


def export_level_filter_suffix(level_filter: str) -> str:
    if not level_filter or level_filter == "all":
        return ""
    mode, _, raw_level = level_filter.partition(":")
    level = normalize_export_level(raw_level).lower().replace("+", "_")
    if mode == "only":
        return f"_{level}"
    if mode == "up-to":
        return f"_up_to_{level}"
    return ""


def write_vocab_status_report(
    report_dir: Path,
    rows: list[dict[str, str]],
    *,
    level_filter: str = "all",
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = report_dir / f"jlpt_vocab_status{export_level_filter_suffix(level_filter)}_{stamp}.csv"
    filtered_rows = filter_vocab_status_rows(rows, level_filter)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=vocab_status_fieldnames(), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filtered_rows)

    return output_path
