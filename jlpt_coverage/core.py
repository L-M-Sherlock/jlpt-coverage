from __future__ import annotations

import csv
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from html import escape
from pathlib import Path

from .text import JLPT_LEVELS, frequency_sort_key, level_sort_key, text_keys


DEFAULT_NOTE_TYPES = ("Lapis", "Kaishi 1.5k", "Kaishi 1.5k zh-CH")
JLPT_VOCAB_SOURCE_URL = "https://github.com/5mdld/anki-jlpt-decks"
Translator = Callable[..., str]

NOTE_TYPE_FIELD_RULES = {
    "Kaishi 1.5k": {
        "term": {"word"},
        "reading": {"word reading"},
    },
    "Kaishi 1.5k zh-CH": {
        "term": {"word"},
        "reading": {"word reading"},
    },
    "Lapis": {
        "term": {"expression"},
        "reading": {"expressionreading"},
    },
}
JLPT_TAG_PREFIX = "JLPT::"
JLPT_TAG_LEVELS = JLPT_LEVELS
JLPT_FREQUENCY_TAG_LEVELS = ("N1", "N2", "N3")


def translate_text(translate: Translator | None, key: str, default: str, **kwargs: object) -> str:
    if translate is None:
        return default
    return str(translate(key, default=default, **kwargs))


@dataclass(frozen=True)
class JlptEntry:
    level: str
    frequency: str
    word_plain: str
    reading: str

    @property
    def term_keys(self) -> set[str]:
        return text_keys(self.word_plain)

    @property
    def reading_keys(self) -> set[str]:
        return text_keys(self.reading)


@dataclass(frozen=True)
class MatchKeys:
    term: set[str]
    reading: set[str]
    learned_term: set[str]
    learned_reading: set[str]
    young_term: set[str]
    young_reading: set[str]
    mature_term: set[str]
    mature_reading: set[str]


@dataclass(frozen=True)
class JlptTagTarget:
    level: str
    frequency: str


@dataclass(frozen=True)
class JlptLevelIndexes:
    term: dict[str, set[str]]
    reading: dict[str, set[str]]
    term_reading: dict[tuple[str, str], set[JlptTagTarget]]
    skipped_levels: dict[str, int]


def load_jlpt_entries(path: Path) -> list[JlptEntry]:
    entries: list[JlptEntry] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "level",
            "frequency",
            "word_plain",
            "reading",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            entries.append(
                JlptEntry(
                    level=row["level"],
                    frequency=row["frequency"],
                    word_plain=row["word_plain"],
                    reading=row["reading"],
                )
            )
    return entries


def split_fields(flds: str, expected_count: int) -> list[str]:
    parts = flds.split("\x1f")
    if len(parts) < expected_count:
        parts.extend([""] * (expected_count - len(parts)))
    return parts


def field_is_term(note_type_name: str, field_name: str) -> bool:
    return field_name.strip().lower() in NOTE_TYPE_FIELD_RULES[note_type_name]["term"]


def field_is_reading(note_type_name: str, field_name: str) -> bool:
    return field_name.strip().lower() in NOTE_TYPE_FIELD_RULES[note_type_name]["reading"]


def classify_match(entry: JlptEntry, term_keys: set[str], reading_keys: set[str], mode: str) -> tuple[bool, str]:
    word_match = bool(entry.term_keys & term_keys)
    reading_match = bool(entry.reading_keys & reading_keys)

    if mode == "word":
        covered = word_match
    elif mode == "reading":
        covered = reading_match
    else:
        covered = word_match or reading_match

    if word_match and reading_match:
        matched_by = "word+reading"
    elif word_match:
        matched_by = "word"
    elif reading_match:
        matched_by = "reading"
    else:
        matched_by = ""
    return covered, matched_by


def jlpt_tag_for_level(level: str, prefix: str = JLPT_TAG_PREFIX) -> str:
    if level not in JLPT_TAG_LEVELS:
        allowed = ", ".join(JLPT_TAG_LEVELS)
        raise ValueError(f"Invalid JLPT tag level: {level}. Expected one of: {allowed}")
    return f"{prefix}{level}"


def jlpt_tag_for_frequency(level: str, frequency: str, prefix: str = JLPT_TAG_PREFIX) -> str:
    if level not in JLPT_FREQUENCY_TAG_LEVELS:
        allowed = ", ".join(JLPT_FREQUENCY_TAG_LEVELS)
        raise ValueError(f"Invalid JLPT frequency tag level: {level}. Expected one of: {allowed}")
    if not frequency:
        raise ValueError("JLPT frequency tag needs a frequency value.")
    return f"{prefix}{level}::{frequency}"


def jlpt_tags_for_target(target: JlptTagTarget, prefix: str = JLPT_TAG_PREFIX) -> tuple[str, ...]:
    tags = [jlpt_tag_for_level(target.level, prefix)]
    if target.level in JLPT_FREQUENCY_TAG_LEVELS:
        tags.append(jlpt_tag_for_frequency(target.level, target.frequency, prefix))
    return tuple(tags)


def build_jlpt_level_indexes(entries: list[JlptEntry]) -> JlptLevelIndexes:
    term_index: dict[str, set[str]] = defaultdict(set)
    reading_index: dict[str, set[str]] = defaultdict(set)
    term_reading_index: dict[tuple[str, str], set[JlptTagTarget]] = defaultdict(set)
    skipped_levels: Counter[str] = Counter()

    for entry in entries:
        if entry.level not in JLPT_TAG_LEVELS:
            skipped_levels[entry.level] += 1
            continue
        target = JlptTagTarget(entry.level, entry.frequency)
        term_keys = entry.term_keys
        reading_keys = entry.reading_keys
        for key in term_keys:
            term_index[key].add(entry.level)
        for key in reading_keys:
            reading_index[key].add(entry.level)
        for term_key in term_keys:
            for reading_key in reading_keys:
                term_reading_index[(term_key, reading_key)].add(target)

    return JlptLevelIndexes(
        term=dict(term_index),
        reading=dict(reading_index),
        term_reading=dict(term_reading_index),
        skipped_levels=dict(skipped_levels),
    )


def _levels_for_keys(keys: set[str], index: dict[str, set[str]]) -> set[str]:
    levels: set[str] = set()
    for key in keys:
        levels.update(index.get(key, set()))
    return levels


def matched_jlpt_levels(
    term_keys: set[str],
    reading_keys: set[str],
    indexes: JlptLevelIndexes,
    mode: str,
) -> set[str]:
    if mode == "word":
        return _levels_for_keys(term_keys, indexes.term)
    if mode == "reading":
        return _levels_for_keys(reading_keys, indexes.reading)
    return _levels_for_keys(term_keys, indexes.term) | _levels_for_keys(reading_keys, indexes.reading)


def matched_jlpt_levels_strict(
    term_keys: set[str],
    reading_keys: set[str],
    indexes: JlptLevelIndexes,
) -> set[str]:
    return {target.level for target in matched_jlpt_targets_strict(term_keys, reading_keys, indexes)}


def matched_jlpt_targets_strict(
    term_keys: set[str],
    reading_keys: set[str],
    indexes: JlptLevelIndexes,
) -> set[JlptTagTarget]:
    targets: set[JlptTagTarget] = set()
    for term_key in term_keys:
        for reading_key in reading_keys:
            targets.update(indexes.term_reading.get((term_key, reading_key), set()))
    return targets


def detail_row(entry: JlptEntry) -> dict[str, str]:
    return {
        "level": entry.level,
        "frequency": entry.frequency,
        "word_plain": entry.word_plain,
        "reading": entry.reading,
    }


def vocab_status_rows(entries: list[JlptEntry], match_keys: MatchKeys, mode: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in entries:
        covered, _matched_by = classify_match(entry, match_keys.term, match_keys.reading, mode)
        learned, _learned_matched_by = classify_match(
            entry,
            match_keys.learned_term,
            match_keys.learned_reading,
            mode,
        )
        row = detail_row(entry)
        row["missing"] = "1" if not covered else "0"
        row["unlearned"] = "1" if covered and not learned else "0"
        rows.append(row)
    return rows


def summarize(
    entries: list[JlptEntry],
    match_keys: MatchKeys,
    mode: str,
    *,
    by_frequency: bool,
    by_interval: bool,
) -> tuple[list[dict[str, object]], list[dict[str, str]], list[dict[str, str]]]:
    buckets: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    missing_rows: list[dict[str, str]] = []
    unlearned_rows: list[dict[str, str]] = []

    for entry in entries:
        covered, matched_by = classify_match(entry, match_keys.term, match_keys.reading, mode)
        learned, learned_matched_by = classify_match(
            entry,
            match_keys.learned_term,
            match_keys.learned_reading,
            mode,
        )
        if by_interval:
            young, _young_matched_by = classify_match(
                entry,
                match_keys.young_term,
                match_keys.young_reading,
                mode,
            )
            mature, _mature_matched_by = classify_match(
                entry,
                match_keys.mature_term,
                match_keys.mature_reading,
                mode,
            )
        else:
            young = False
            mature = False
        frequency = entry.frequency if by_frequency else ""
        bucket = buckets[(entry.level, frequency)]
        bucket["total"] += 1
        if covered:
            bucket["card_covered"] += 1
        else:
            bucket["card_missing"] += 1
            missing_rows.append(detail_row(entry))
        if learned:
            bucket["learning_covered"] += 1
        elif covered:
            bucket["unlearned"] += 1
            unlearned_rows.append(detail_row(entry))
        if young:
            bucket["young"] += 1
        if mature:
            bucket["mature"] += 1
        if matched_by == "word":
            bucket["card_word_matches"] += 1
        elif matched_by == "reading":
            bucket["card_reading_matches"] += 1
        elif matched_by == "word+reading":
            bucket["card_word_matches"] += 1
            bucket["card_reading_matches"] += 1
        if learned_matched_by == "word":
            bucket["learning_word_matches"] += 1
        elif learned_matched_by == "reading":
            bucket["learning_reading_matches"] += 1
        elif learned_matched_by == "word+reading":
            bucket["learning_word_matches"] += 1
            bucket["learning_reading_matches"] += 1

    summary: list[dict[str, object]] = []
    for (level, frequency), counter in sorted(
        buckets.items(),
        key=lambda item: (*level_sort_key(item[0][0]), *frequency_sort_key(item[0][1])),
    ):
        total = counter["total"]
        card_covered = counter["card_covered"]
        learning_covered = counter["learning_covered"]
        row = {
            "level": level,
            "frequency": frequency,
            "total": total,
            "card_covered": card_covered,
            "card_coverage_pct": round(card_covered / total * 100, 2) if total else 0.0,
            "learning_covered": learning_covered,
            "learning_coverage_pct": round(learning_covered / total * 100, 2) if total else 0.0,
            "card_missing": counter["card_missing"],
            "unlearned": counter["unlearned"],
            "card_word_matches": counter["card_word_matches"],
            "card_reading_matches": counter["card_reading_matches"],
            "learning_word_matches": counter["learning_word_matches"],
            "learning_reading_matches": counter["learning_reading_matches"],
        }
        if by_interval:
            young_count = counter["young"]
            mature_count = counter["mature"]
            row.update(
                {
                    "young": young_count,
                    "young_pct": round(young_count / total * 100, 2) if total else 0.0,
                    "mature": mature_count,
                    "mature_pct": round(mature_count / total * 100, 2) if total else 0.0,
                }
            )
        summary.append(row)
    return summary, missing_rows, unlearned_rows


def summary_fieldnames(*, by_frequency: bool, by_interval: bool = False) -> list[str]:
    fields = ["level"]
    if by_frequency:
        fields.append("frequency")
    fields.extend(
        [
            "total",
            "card_covered",
            "card_coverage_pct",
            "learning_covered",
            "learning_coverage_pct",
            "card_missing",
            "unlearned",
            "card_word_matches",
            "card_reading_matches",
            "learning_word_matches",
            "learning_reading_matches",
        ]
    )
    if by_interval:
        fields.extend(["young", "young_pct", "mature", "mature_pct"])
    return fields


def detail_fieldnames() -> list[str]:
    return [
        "level",
        "frequency",
        "word_plain",
        "reading",
    ]


def vocab_status_fieldnames() -> list[str]:
    return [*detail_fieldnames(), "missing", "unlearned"]


def format_summary(
    summary: list[dict[str, object]],
    metadata: dict[str, object],
    missing_rows: list[dict[str, str]] | None = None,
    *,
    show_missing: int = 0,
    translate: Translator | None = None,
) -> str:
    note_types = ", ".join(metadata.get("note_type_names", ()))
    profile_dir = str(metadata.get("profile_dir", ""))
    match_mode = str(metadata.get("match_mode", ""))
    lines = [
        translate_text(translate, "report-title", "JLPT Coverage"),
        f"- {translate_text(translate, 'report-anki-profile', 'Anki profile')}: {profile_dir}",
        f"- {translate_text(translate, 'report-note-types', 'Note types')}: {note_types}",
        f"- {translate_text(translate, 'report-match-mode', 'Match mode')}: {match_mode}",
    ]
    if metadata.get("by_frequency"):
        lines.append(
            f"- {translate_text(translate, 'report-frequency-band', 'Frequency band')}: "
            f"{translate_text(translate, 'report-frequency-band-value', 'Expanded by source vocabulary frequency')}"
        )
    if metadata.get("by_interval"):
        lines.append(
            f"- {translate_text(translate, 'report-by-interval', 'Young/Mature')}: "
            f"{translate_text(translate, 'report-by-interval-value', 'Young: ivl < 21; Mature: ivl >= 21')}"
        )
    anki_stats = metadata.get("anki_stats", {})
    lines.extend(
        [
            f"- {translate_text(translate, 'report-stats-notes', 'Stats notes')}: {anki_stats.get('notes', 0)}",
            f"- {translate_text(translate, 'report-learned-notes', 'Learned notes')}: "
            f"{anki_stats.get('learned_notes', 0)}",
            f"- {translate_text(translate, 'report-learning-coverage', 'Learning coverage')}: "
            f"{translate_text(translate, 'report-learning-coverage-value', 'Matched at least one card with reps > 0')}",
            "",
        ]
    )

    by_interval = bool(metadata.get("by_interval"))
    level_header = translate_text(translate, "report-level", "Level")
    frequency_header = translate_text(translate, "report-frequency", "Freq")
    total_header = translate_text(translate, "report-total", "Total")
    card_header = translate_text(translate, "report-card", "Card")
    card_pct_header = translate_text(translate, "report-card-pct", "Card%")
    learned_header = translate_text(translate, "report-learned", "Learned")
    learned_pct_header = translate_text(translate, "report-learned-pct", "Learn%")
    missing_header = translate_text(translate, "report-missing", "Missing")
    unlearned_header = translate_text(translate, "report-unlearned", "Unlearned")
    young_header = translate_text(translate, "report-young", "Young")
    young_pct_header = translate_text(translate, "report-young-pct", "Young%")
    mature_header = translate_text(translate, "report-mature", "Mature")
    mature_pct_header = translate_text(translate, "report-mature-pct", "Mature%")
    if metadata.get("by_frequency"):
        header = (
            f"{level_header:<8}"
            f"{frequency_header:<10}"
            f"{total_header:>8}"
            f"{card_header:>9}"
            f"{card_pct_header:>9}"
            f"{learned_header:>10}"
            f"{learned_pct_header:>9}"
            f"{missing_header:>10}"
            f"{unlearned_header:>11}"
        )
    else:
        header = (
            f"{level_header:<8}"
            f"{total_header:>8}"
            f"{card_header:>9}"
            f"{card_pct_header:>9}"
            f"{learned_header:>10}"
            f"{learned_pct_header:>9}"
            f"{missing_header:>10}"
            f"{unlearned_header:>11}"
        )
    if by_interval:
        header += f"{young_header:>8}{young_pct_header:>9}{mature_header:>8}{mature_pct_header:>9}"
    lines.append(header)

    for row in summary:
        if metadata.get("by_frequency"):
            line = (
                f"{row['level']:<8}"
                f"{row['frequency']:<10}"
                f"{row['total']:>8}"
                f"{row['card_covered']:>9}"
                f"{row['card_coverage_pct']:>8.2f}%"
                f"{row['learning_covered']:>10}"
                f"{row['learning_coverage_pct']:>8.2f}%"
                f"{row['card_missing']:>10}"
                f"{row['unlearned']:>11}"
            )
        else:
            line = (
                f"{row['level']:<8}"
                f"{row['total']:>8}"
                f"{row['card_covered']:>9}"
                f"{row['card_coverage_pct']:>8.2f}%"
                f"{row['learning_covered']:>10}"
                f"{row['learning_coverage_pct']:>8.2f}%"
                f"{row['card_missing']:>10}"
                f"{row['unlearned']:>11}"
            )
        if by_interval:
            line += (
                f"{row['young']:>8}"
                f"{row['young_pct']:>8.2f}%"
                f"{row['mature']:>8}"
                f"{row['mature_pct']:>8.2f}%"
            )
        lines.append(line)

    if any(row["level"] == "N4+N5" for row in summary):
        lines.extend(
            [
                "",
                translate_text(
                    translate,
                    "report-n4n5-warning",
                    "Note: The current JLPT source vocabulary merges N4 and N5 into N4+N5; "
                    "this file cannot reliably split them into separate N4/N5 levels.",
                ),
            ]
        )

    if show_missing > 0 and missing_rows:
        lines.extend(
            [
                "",
                translate_text(
                    translate,
                    "report-top-missing",
                    f"Top {show_missing} missing words by level:",
                    count=show_missing,
                ),
            ]
        )
        by_level: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in missing_rows:
            by_level[row["level"]].append(row)
        for level in sorted(by_level, key=level_sort_key):
            sample = by_level[level][:show_missing]
            words = "、".join(row["word_plain"] for row in sample)
            lines.append(f"- {level}: {words}")

    return "\n".join(lines)


def format_summary_html(
    summary: list[dict[str, object]],
    metadata: dict[str, object],
    translate: Translator | None = None,
) -> str:
    by_frequency = bool(metadata.get("by_frequency"))
    by_interval = bool(metadata.get("by_interval"))
    dark_mode = bool(metadata.get("dark_mode"))
    anki_stats = metadata.get("anki_stats", {})
    note_types = ", ".join(str(item) for item in metadata.get("note_type_names", ()))
    if dark_mode:
        colors = {
            "page_bg": "#1f1f1f",
            "text": "#e5e7eb",
            "muted": "#a7b0bd",
            "header_bg": "#2f3742",
            "header_text": "#f3f4f6",
            "border": "#3f4854",
            "note_bg": "#3b2a1f",
            "note_border": "#8a5a2b",
            "note_text": "#fed7aa",
            "source": "#a7b0bd",
            "link": "#60a5fa",
        }
    else:
        colors = {
            "page_bg": "#ffffff",
            "text": "#202124",
            "muted": "#4b5563",
            "header_bg": "#f3f4f6",
            "header_text": "#374151",
            "border": "#d1d5db",
            "note_bg": "#fff7ed",
            "note_border": "#fed7aa",
            "note_text": "#7c2d12",
            "source": "#4b5563",
            "link": "#2563eb",
        }

    meta_rows = [
        (translate_text(translate, "report-anki-profile", "Anki profile"), metadata.get("profile_dir", "")),
        (translate_text(translate, "report-note-types", "Note types"), note_types),
        (translate_text(translate, "report-match-mode", "Match mode"), metadata.get("match_mode", "")),
        (translate_text(translate, "report-stats-notes", "Stats notes"), anki_stats.get("notes", 0)),
        (translate_text(translate, "report-learned-notes", "Learned notes"), anki_stats.get("learned_notes", 0)),
        (
            translate_text(translate, "report-learning-coverage", "Learning coverage"),
            translate_text(translate, "report-learning-coverage-value", "Matched at least one card with reps > 0"),
        ),
    ]
    if by_frequency:
        meta_rows.insert(
            3,
            (
                translate_text(translate, "report-frequency-band", "Frequency band"),
                translate_text(
                    translate,
                    "report-frequency-band-value",
                    "Expanded by source vocabulary frequency",
                ),
            ),
        )
    if by_interval:
        meta_rows.insert(
            4 if by_frequency else 3,
            (
                translate_text(translate, "report-by-interval", "Young/Mature"),
                translate_text(translate, "report-by-interval-value", "Young: ivl < 21; Mature: ivl >= 21"),
            ),
        )

    headers = [translate_text(translate, "report-level", "Level")]
    if by_frequency:
        headers.append(translate_text(translate, "report-frequency", "Freq"))
    headers.extend(
        [
            translate_text(translate, "report-total", "Total"),
            translate_text(translate, "report-card", "Card"),
            translate_text(translate, "report-card-pct", "Card%"),
            translate_text(translate, "report-learned", "Learned"),
            translate_text(translate, "report-learned-pct", "Learn%"),
            translate_text(translate, "report-missing", "Missing"),
            translate_text(translate, "report-unlearned", "Unlearned"),
        ]
    )
    if by_interval:
        headers.extend(
            [
                translate_text(translate, "report-young", "Young"),
                translate_text(translate, "report-young-pct", "Young%"),
                translate_text(translate, "report-mature", "Mature"),
                translate_text(translate, "report-mature-pct", "Mature%"),
            ]
        )

    def td(value: object, *, numeric: bool = False) -> str:
        klass = ' class="num"' if numeric else ""
        return f"<td{klass}>{escape(str(value))}</td>"

    def pct(value: object) -> str:
        return f"{float(value):.2f}%"

    rows_html = []
    for row in summary:
        cells = [td(row["level"])]
        if by_frequency:
            cells.append(td(row["frequency"]))
        cells.extend(
            [
                td(row["total"], numeric=True),
                td(row["card_covered"], numeric=True),
                td(pct(row["card_coverage_pct"]), numeric=True),
                td(row["learning_covered"], numeric=True),
                td(pct(row["learning_coverage_pct"]), numeric=True),
                td(row["card_missing"], numeric=True),
                td(row["unlearned"], numeric=True),
            ]
        )
        if by_interval:
            cells.extend(
                [
                    td(row["young"], numeric=True),
                    td(pct(row["young_pct"]), numeric=True),
                    td(row["mature"], numeric=True),
                    td(pct(row["mature_pct"]), numeric=True),
                ]
            )
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    meta_html = "\n".join(
        "<tr>"
        f"<th>{escape(str(label))}</th>"
        f"<td>{escape(str(value))}</td>"
        "</tr>"
        for label, value in meta_rows
    )
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = "\n".join(rows_html)

    warning_html = ""
    if any(row["level"] == "N4+N5" for row in summary):
        warning_html = (
            f'<p class="note">{escape(translate_text(translate, "report-n4n5-warning", "Note: The current JLPT source vocabulary merges N4 and N5 into N4+N5; this file cannot reliably split them into separate N4/N5 levels."))}</p>'
        )

    source_link = f'<a href="{JLPT_VOCAB_SOURCE_URL}">5mdld/anki-jlpt-decks</a>'
    source_html = (
        '<p class="source">'
        f'{translate_text(translate, "report-source", f"Vocabulary source and acknowledgements: {source_link} provides the eggrolls JLPT10k vocabulary data.", link=source_link)}'
        "</p>"
    )

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body {{
      background: {colors["page_bg"]};
      color: {colors["text"]};
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", sans-serif;
      font-size: 14px;
      line-height: 1.45;
      margin: 0;
      padding: 14px 16px 20px;
    }}
    h2 {{
      font-size: 20px;
      margin: 0 0 12px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
    }}
    .meta {{
      margin-bottom: 16px;
    }}
    .meta th {{
      color: {colors["muted"]};
      font-weight: 600;
      padding: 3px 12px 3px 0;
      text-align: left;
      white-space: nowrap;
      width: 120px;
    }}
    .meta td {{
      color: {colors["text"]};
      padding: 3px 0;
    }}
    .summary th {{
      background: {colors["header_bg"]};
      border-bottom: 1px solid {colors["border"]};
      color: {colors["header_text"]};
      font-weight: 700;
      padding: 7px 9px;
      text-align: left;
      white-space: nowrap;
    }}
    .summary td {{
      border-bottom: 1px solid {colors["border"]};
      color: {colors["text"]};
      padding: 7px 9px;
      white-space: nowrap;
    }}
    .summary .num {{
      font-variant-numeric: tabular-nums;
      text-align: right;
    }}
    .note {{
      background: {colors["note_bg"]};
      border: 1px solid {colors["note_border"]};
      border-radius: 6px;
      color: {colors["note_text"]};
      margin: 16px 0 0;
      padding: 10px 12px;
    }}
    .source {{
      color: {colors["source"]};
      font-size: 12px;
      margin: 12px 0 0;
    }}
    a {{
      color: {colors["link"]};
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <h2>{escape(translate_text(translate, "report-title", "JLPT Coverage"))}</h2>
  <table class="meta">
    {meta_html}
  </table>
  <table class="summary">
    <thead><tr>{header_html}</tr></thead>
    <tbody>
      {body_html}
    </tbody>
  </table>
  {warning_html}
  {source_html}
</body>
</html>
"""
