from __future__ import annotations

import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from .core import (
    DEFAULT_NOTE_TYPES,
    NOTE_TYPE_FIELD_RULES,
    MatchKeys,
    field_is_reading,
    field_is_term,
    split_fields,
)
from .text import text_keys


def copy_collection(
    profile_dir: Path,
    *,
    keep_copy: bool,
    report_dir: Path,
) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    source_db = profile_dir / "collection.anki2"
    if not source_db.exists():
        raise FileNotFoundError(f"Anki collection not found: {source_db}")

    if keep_copy:
        copy_dir = report_dir / "collection-copy"
        copy_dir.mkdir(parents=True, exist_ok=True)
        temp_ctx = None
    else:
        temp_ctx = tempfile.TemporaryDirectory(prefix="anki_collection_copy_")
        copy_dir = Path(temp_ctx.name)

    for suffix in ("", "-wal", "-shm"):
        source = profile_dir / f"collection.anki2{suffix}"
        if source.exists():
            shutil.copy2(source, copy_dir / source.name)

    return copy_dir / "collection.anki2", temp_ctx


def fetch_note_type_ids(conn: sqlite3.Connection, names: tuple[str, ...]) -> dict[int, str]:
    placeholders = ",".join("?" for _ in names)
    rows = conn.execute(
        f"""
        select id, name
        from notetypes
        where name collate binary in ({placeholders})
        """,
        names,
    ).fetchall()
    return {int(row[0]): str(row[1]) for row in rows}


def fetch_field_names(conn: sqlite3.Connection, note_type_ids: list[int]) -> dict[int, list[str]]:
    if not note_type_ids:
        return {}
    placeholders = ",".join("?" for _ in note_type_ids)
    fields: dict[int, list[str]] = defaultdict(list)
    for ntid, _ord, name in conn.execute(
        f"""
        select ntid, ord, name
        from fields
        where ntid in ({placeholders})
        order by ntid, ord
        """,
        note_type_ids,
    ):
        fields[int(ntid)].append(str(name))
    return fields


def collect_anki_keys(
    db_path: Path,
    note_type_names: tuple[str, ...] = DEFAULT_NOTE_TYPES,
    *,
    exclude_suspended: bool,
) -> tuple[MatchKeys, dict[str, int]]:
    conn = sqlite3.connect(str(db_path))
    try:
        note_types = fetch_note_type_ids(conn, note_type_names)
        missing_note_types = sorted(set(note_type_names) - set(note_types.values()))
        if missing_note_types:
            raise ValueError(f"Missing note types in collection copy: {', '.join(missing_note_types)}")
        missing_rules = sorted(set(note_type_names) - set(NOTE_TYPE_FIELD_RULES))
        if missing_rules:
            raise ValueError(f"Missing field rules for note types: {', '.join(missing_rules)}")

        field_names_by_ntid = fetch_field_names(conn, list(note_types))
        placeholders = ",".join("?" for _ in note_types)
        card_filter = "and c.queue != -1" if exclude_suspended else ""

        query = f"""
            select
                n.id,
                n.mid,
                n.flds,
                max(case when c.reps > 0 then 1 else 0 end) as has_learned_card,
                max(case when c.ivl < 21 then 1 else 0 end) as has_young_card,
                max(case when c.ivl >= 21 then 1 else 0 end) as has_mature_card
            from notes n
            join cards c on c.nid = n.id
            where n.mid in ({placeholders})
              {card_filter}
            group by n.id, n.mid, n.flds
        """

        term_keys: set[str] = set()
        reading_keys: set[str] = set()
        learned_term_keys: set[str] = set()
        learned_reading_keys: set[str] = set()
        young_term_keys: set[str] = set()
        young_reading_keys: set[str] = set()
        mature_term_keys: set[str] = set()
        mature_reading_keys: set[str] = set()
        stats = Counter()
        for _note_id, mid, flds, has_learned_card, has_young_card, has_mature_card in conn.execute(
            query, list(note_types)
        ):
            note_type_name = note_types[int(mid)]
            names = field_names_by_ntid[int(mid)]
            values = split_fields(str(flds), len(names))
            stats["notes"] += 1
            stats[f"notes:{note_type_name}"] += 1
            if has_learned_card:
                stats["learned_notes"] += 1
                stats[f"learned_notes:{note_type_name}"] += 1
            if has_young_card:
                stats["young_notes"] += 1
                stats[f"young_notes:{note_type_name}"] += 1
            if has_mature_card:
                stats["mature_notes"] += 1
                stats[f"mature_notes:{note_type_name}"] += 1

            for name, value in zip(names, values):
                if field_is_term(note_type_name, name):
                    keys = text_keys(value)
                    term_keys.update(keys)
                    if has_learned_card:
                        learned_term_keys.update(keys)
                    if has_young_card:
                        young_term_keys.update(keys)
                    if has_mature_card:
                        mature_term_keys.update(keys)
                elif field_is_reading(note_type_name, name):
                    keys = text_keys(value)
                    reading_keys.update(keys)
                    if has_learned_card:
                        learned_reading_keys.update(keys)
                    if has_young_card:
                        young_reading_keys.update(keys)
                    if has_mature_card:
                        mature_reading_keys.update(keys)

        stats["term_keys"] = len(term_keys)
        stats["reading_keys"] = len(reading_keys)
        stats["learned_term_keys"] = len(learned_term_keys)
        stats["learned_reading_keys"] = len(learned_reading_keys)
        stats["young_term_keys"] = len(young_term_keys)
        stats["young_reading_keys"] = len(young_reading_keys)
        stats["mature_term_keys"] = len(mature_term_keys)
        stats["mature_reading_keys"] = len(mature_reading_keys)
        return MatchKeys(
            term_keys,
            reading_keys,
            learned_term_keys,
            learned_reading_keys,
            young_term_keys,
            young_reading_keys,
            mature_term_keys,
            mature_reading_keys,
        ), dict(stats)
    finally:
        conn.close()
