from __future__ import annotations

import csv
from html import escape
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .text import frequency_sort_key, level_sort_key, text_keys


DEFAULT_NOTE_TYPES = ("Lapis", "Kaishi 1.5k", "Kaishi 1.5k zh-CH")
JLPT_VOCAB_SOURCE_URL = "https://github.com/5mdld/anki-jlpt-decks"

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
) -> str:
    lines = [
        "JLPT 覆盖率",
        f"- Anki profile: {metadata.get('profile_dir', '')}",
        f"- 已统计 note types: {', '.join(metadata.get('note_type_names', ()))}",
        f"- 匹配模式: {metadata.get('match_mode', '')}",
    ]
    if metadata.get("by_frequency"):
        lines.append("- 频率分档: 已按源词表 frequency 展开")
    if metadata.get("by_interval"):
        lines.append("- Young/Mature: Young 为 ivl < 21，Mature 为 ivl >= 21")
    anki_stats = metadata.get("anki_stats", {})
    lines.extend(
        [
            f"- 统计 notes: {anki_stats.get('notes', 0)}",
            f"- 已学习 notes: {anki_stats.get('learned_notes', 0)}",
            "- 学习覆盖: 命中至少一张 reps > 0 的 card",
            "",
        ]
    )

    by_interval = bool(metadata.get("by_interval"))
    if metadata.get("by_frequency"):
        header = (
            f"{'Level':<8}"
            f"{'Freq':<10}"
            f"{'Total':>8}"
            f"{'Card':>9}"
            f"{'Card%':>9}"
            f"{'Learned':>10}"
            f"{'Learn%':>9}"
            f"{'Missing':>10}"
            f"{'Unlearned':>11}"
        )
    else:
        header = (
            f"{'Level':<8}"
            f"{'Total':>8}"
            f"{'Card':>9}"
            f"{'Card%':>9}"
            f"{'Learned':>10}"
            f"{'Learn%':>9}"
            f"{'Missing':>10}"
            f"{'Unlearned':>11}"
        )
    if by_interval:
        header += f"{'Young':>8}{'Young%':>9}{'Mature':>8}{'Mature%':>9}"
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
                "注意: 当前 JLPT 源词表将 N4 和 N5 合并为 N4+N5，无法仅凭该文件拆成独立 N4/N5。",
            ]
        )

    if show_missing > 0 and missing_rows:
        lines.extend(["", f"每级前 {show_missing} 个缺词:"])
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
        ("Anki profile", metadata.get("profile_dir", "")),
        ("Note types", note_types),
        ("匹配模式", metadata.get("match_mode", "")),
        ("统计 notes", anki_stats.get("notes", 0)),
        ("已学习 notes", anki_stats.get("learned_notes", 0)),
        ("学习覆盖", "命中至少一张 reps > 0 的 card"),
    ]
    if by_frequency:
        meta_rows.insert(3, ("频率分档", "按源词表 frequency 展开"))
    if by_interval:
        meta_rows.insert(4 if by_frequency else 3, ("Young/Mature", "Young: ivl < 21; Mature: ivl >= 21"))

    headers = ["Level"]
    if by_frequency:
        headers.append("Freq")
    headers.extend(["Total", "Card", "Card%", "Learned", "Learn%", "Missing", "Unlearned"])
    if by_interval:
        headers.extend(["Young", "Young%", "Mature", "Mature%"])

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
            '<p class="note">注意: 当前 JLPT 源词表将 N4 和 N5 合并为 '
            "N4+N5，无法仅凭该文件拆成独立 N4/N5。</p>"
        )

    source_html = (
        '<p class="source">'
        '词表来源与致谢: '
        f'<a href="{JLPT_VOCAB_SOURCE_URL}">5mdld/anki-jlpt-decks</a>'
        " 提供 eggrolls JLPT10k 词汇数据。"
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
  <h2>JLPT 覆盖率</h2>
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
