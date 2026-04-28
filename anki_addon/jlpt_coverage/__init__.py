from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from aqt import mw
from aqt.qt import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPalette,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showInfo, showWarning


try:
    from .jlpt_converge.core import (
        DEFAULT_NOTE_TYPES,
        NOTE_TYPE_FIELD_RULES,
        MatchKeys,
        format_summary_html,
        load_jlpt_entries,
        split_fields,
        summarize,
        vocab_status_rows,
    )
    from .jlpt_converge.reports import write_vocab_status_report
    from .jlpt_converge.text import text_keys
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from jlpt_converge.core import (
        DEFAULT_NOTE_TYPES,
        NOTE_TYPE_FIELD_RULES,
        MatchKeys,
        format_summary_html,
        load_jlpt_entries,
        split_fields,
        summarize,
        vocab_status_rows,
    )
    from jlpt_converge.reports import write_vocab_status_report
    from jlpt_converge.text import text_keys


ADDON_DIR = Path(__file__).resolve().parent
PACKAGE_VOCAB_PATH = ADDON_DIR / "data" / "jlpt_vocab.csv"
SOURCE_VOCAB_PATH = ADDON_DIR.parents[1] / "data" / "jlpt_vocab.csv"

MODE_CHOICES = (
    ("word-or-reading", "字形或读音"),
    ("reading", "只匹配读音"),
    ("word", "只匹配字形"),
)
NONE_FIELD = ""
NONE_FIELD_LABEL = "不使用"


def config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def vocab_path() -> Path:
    if PACKAGE_VOCAB_PATH.exists():
        return PACKAGE_VOCAB_PATH
    return SOURCE_VOCAB_PATH


def is_dark_mode() -> bool:
    try:
        palette = mw.app.palette()
        try:
            window_color = palette.color(QPalette.ColorRole.Window)
        except AttributeError:
            window_color = palette.color(QPalette.Window)
        return window_color.lightness() < 128
    except Exception:
        return False


def configured_note_types() -> tuple[str, ...]:
    value = config().get("note_types", list(DEFAULT_NOTE_TYPES))
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = value
    note_types = tuple(str(item).strip() for item in items if str(item).strip())
    return note_types or DEFAULT_NOTE_TYPES


def configured_field_mappings() -> dict[str, dict[str, str]]:
    mappings = config().get("field_mappings", {})
    if not isinstance(mappings, dict):
        mappings = {}
    result: dict[str, dict[str, str]] = {}
    for note_type, mapping in mappings.items():
        if isinstance(mapping, dict):
            result[str(note_type)] = {
                "term": str(mapping.get("term", "")).strip(),
                "reading": str(mapping.get("reading", "")).strip(),
            }
    for note_type, rule in NOTE_TYPE_FIELD_RULES.items():
        result.setdefault(
            note_type,
            {
                "term": next(iter(rule["term"]), ""),
                "reading": next(iter(rule["reading"]), ""),
            },
        )
    return result


def model_by_name(col, name: str):
    try:
        return col.models.by_name(name)
    except AttributeError:
        models = col.models.all()
        for model in models:
            if model.get("name") == name:
                return model
    return None


def all_note_type_models(col) -> list[tuple[str, dict]]:
    try:
        models = col.models.all()
    except Exception:
        return []
    pairs = []
    for model in models:
        name = str(model.get("name", "")).strip()
        if name:
            pairs.append((name, model))
    return sorted(pairs, key=lambda item: item[0].lower())


def field_names_from_model(model: dict) -> list[str]:
    return [str(field.get("name", "")).strip() for field in model.get("flds", []) if str(field.get("name", "")).strip()]


def select_combo_value(combo: QComboBox, value: str) -> None:
    normalized = value.strip().lower()
    for index in range(combo.count()):
        data = str(combo.itemData(index) or "").strip().lower()
        if data == normalized:
            combo.setCurrentIndex(index)
            return
    combo.setCurrentIndex(0)


def field_matches(field_rules: dict[str, dict[str, set[str]]], note_type_name: str, kind: str, field_name: str) -> bool:
    return field_name.strip().lower() in field_rules.get(note_type_name, {}).get(kind, set())


def collect_anki_keys_from_collection(
    col,
    note_type_names: tuple[str, ...],
    field_rules: dict[str, dict[str, set[str]]],
    *,
    exclude_suspended: bool,
) -> tuple[MatchKeys, dict[str, int]]:
    missing_rules = sorted(set(note_type_names) - set(field_rules))
    if missing_rules:
        raise ValueError(f"Missing field rules for note types: {', '.join(missing_rules)}")

    models = {}
    missing_note_types = []
    for note_type_name in note_type_names:
        model = model_by_name(col, note_type_name)
        if model is None:
            missing_note_types.append(note_type_name)
        else:
            models[note_type_name] = model
    if missing_note_types:
        raise ValueError(f"Missing note types in current collection: {', '.join(missing_note_types)}")

    term_keys: set[str] = set()
    reading_keys: set[str] = set()
    learned_term_keys: set[str] = set()
    learned_reading_keys: set[str] = set()
    young_term_keys: set[str] = set()
    young_reading_keys: set[str] = set()
    mature_term_keys: set[str] = set()
    mature_reading_keys: set[str] = set()
    stats = Counter()

    card_filter = "and c.queue != -1" if exclude_suspended else ""
    query = f"""
        select
            n.id,
            n.flds,
            max(case when c.reps > 0 then 1 else 0 end) as has_learned_card,
            max(case when c.ivl < 21 then 1 else 0 end) as has_young_card,
            max(case when c.ivl >= 21 then 1 else 0 end) as has_mature_card
        from notes n
        join cards c on c.nid = n.id
        where n.mid = ?
          {card_filter}
        group by n.id, n.flds
    """

    for note_type_name, model in models.items():
        field_names = [field["name"] for field in model["flds"]]
        for _note_id, flds, has_learned_card, has_young_card, has_mature_card in col.db.all(query, model["id"]):
            values = split_fields(str(flds), len(field_names))
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

            for name, value in zip(field_names, values, strict=False):
                if field_matches(field_rules, note_type_name, "term", name):
                    keys = text_keys(value)
                    term_keys.update(keys)
                    if has_learned_card:
                        learned_term_keys.update(keys)
                    if has_young_card:
                        young_term_keys.update(keys)
                    if has_mature_card:
                        mature_term_keys.update(keys)
                elif field_matches(field_rules, note_type_name, "reading", name):
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


class CoverageDialog(QDialog):
    def __init__(self) -> None:
        super().__init__(mw)
        self.setWindowTitle("JLPT Coverage")
        self.resize(920, 620)
        self.summary: list[dict[str, object]] = []
        self.missing_rows: list[dict[str, str]] = []
        self.unlearned_rows: list[dict[str, str]] = []
        self.status_rows: list[dict[str, str]] = []
        self.metadata: dict[str, object] = {}
        self.note_type_checkboxes: dict[str, QCheckBox] = {}
        self.term_field_combos: dict[str, QComboBox] = {}
        self.reading_field_combos: dict[str, QComboBox] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Note types"))
        note_type_scroll = QScrollArea()
        note_type_scroll.setWidgetResizable(True)
        note_type_scroll.setMinimumHeight(88)
        note_type_scroll.setMaximumHeight(150)
        note_type_container = QWidget()
        note_type_layout = QVBoxLayout()
        note_type_layout.setContentsMargins(6, 4, 6, 4)

        configured = set(configured_note_types())
        mappings = configured_field_mappings()
        model_pairs = all_note_type_models(mw.col)
        if not model_pairs:
            model_pairs = [(name, {"flds": []}) for name in sorted(set(DEFAULT_NOTE_TYPES))]
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Use"), 0)
        header_row.addWidget(QLabel("Note type"), 3)
        header_row.addWidget(QLabel("字形字段"), 2)
        header_row.addWidget(QLabel("读音字段"), 2)
        note_type_layout.addLayout(header_row)

        for name, model in model_pairs:
            row = QHBoxLayout()
            checkbox = QCheckBox(name)
            checkbox.setChecked(name in configured)
            row.addWidget(checkbox, 3)

            term_combo = QComboBox()
            reading_combo = QComboBox()
            for combo in (term_combo, reading_combo):
                combo.addItem(NONE_FIELD_LABEL, NONE_FIELD)
                for field_name in field_names_from_model(model):
                    combo.addItem(field_name, field_name)

            mapping = mappings.get(name, {})
            select_combo_value(term_combo, mapping.get("term", ""))
            select_combo_value(reading_combo, mapping.get("reading", ""))

            term_combo.setEnabled(checkbox.isChecked())
            reading_combo.setEnabled(checkbox.isChecked())
            checkbox.toggled.connect(term_combo.setEnabled)
            checkbox.toggled.connect(reading_combo.setEnabled)

            row.addWidget(term_combo, 2)
            row.addWidget(reading_combo, 2)
            note_type_layout.addLayout(row)
            self.note_type_checkboxes[name] = checkbox
            self.term_field_combos[name] = term_combo
            self.reading_field_combos[name] = reading_combo

        note_type_layout.addStretch()
        note_type_container.setLayout(note_type_layout)
        note_type_scroll.setWidget(note_type_container)
        layout.addWidget(note_type_scroll)

        option_row = QHBoxLayout()
        option_row.addWidget(QLabel("Match mode"))
        self.mode_combo = QComboBox()
        configured_mode = config().get("match_mode", "word-or-reading")
        for value, label in MODE_CHOICES:
            self.mode_combo.addItem(label, value)
            if value == configured_mode:
                self.mode_combo.setCurrentIndex(self.mode_combo.count() - 1)
        option_row.addWidget(self.mode_combo)

        self.by_frequency_checkbox = QCheckBox("按频率分档")
        self.by_frequency_checkbox.setChecked(bool(config().get("by_frequency", False)))
        option_row.addWidget(self.by_frequency_checkbox)

        self.by_interval_checkbox = QCheckBox("统计 Young/Mature")
        self.by_interval_checkbox.setChecked(bool(config().get("by_interval", False)))
        option_row.addWidget(self.by_interval_checkbox)

        self.exclude_suspended_checkbox = QCheckBox("排除暂停卡片")
        self.exclude_suspended_checkbox.setChecked(bool(config().get("exclude_suspended", False)))
        option_row.addWidget(self.exclude_suspended_checkbox)
        option_row.addStretch()
        layout.addLayout(option_row)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_analysis)
        button_row.addWidget(self.run_button)
        self.save_button = QPushButton("Save Defaults")
        self.save_button.clicked.connect(self.save_defaults)
        button_row.addWidget(self.save_button)
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_reports)
        self.export_button.setEnabled(False)
        button_row.addWidget(self.export_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.output = QTextBrowser()
        self.output.setOpenExternalLinks(True)
        layout.addWidget(self.output)

        self.setLayout(layout)

    def selected_note_types(self) -> tuple[str, ...]:
        note_types = tuple(
            name
            for name, checkbox in self.note_type_checkboxes.items()
            if checkbox.isChecked()
        )
        return note_types

    def selected_field_rules(self, note_type_names: tuple[str, ...], match_mode: str) -> dict[str, dict[str, set[str]]]:
        if not note_type_names:
            raise ValueError("请至少选择一个 note type。")

        rules: dict[str, dict[str, set[str]]] = {}
        for note_type_name in note_type_names:
            term_field = self.term_field_combos[note_type_name].currentData() or ""
            reading_field = self.reading_field_combos[note_type_name].currentData() or ""
            if match_mode in ("word", "word-or-reading") and not term_field:
                raise ValueError(f"{note_type_name} 需要选择字形字段。")
            if match_mode in ("reading", "word-or-reading") and not reading_field:
                raise ValueError(f"{note_type_name} 需要选择读音字段。")
            rules[note_type_name] = {
                "term": {term_field.strip().lower()} if term_field else set(),
                "reading": {reading_field.strip().lower()} if reading_field else set(),
            }
        return rules

    def selected_config(self) -> dict:
        note_type_names = self.selected_note_types()
        mappings = {}
        for note_type_name in note_type_names:
            mappings[note_type_name] = {
                "term": self.term_field_combos[note_type_name].currentData() or "",
                "reading": self.reading_field_combos[note_type_name].currentData() or "",
            }
        return {
            "note_types": list(note_type_names),
            "field_mappings": mappings,
            "match_mode": self.mode_combo.currentData(),
            "by_frequency": self.by_frequency_checkbox.isChecked(),
            "by_interval": self.by_interval_checkbox.isChecked(),
            "exclude_suspended": self.exclude_suspended_checkbox.isChecked(),
        }

    def save_defaults(self) -> None:
        mw.addonManager.writeConfig(__name__, self.selected_config())
        showInfo("JLPT Coverage defaults saved.")

    def run_analysis(self) -> None:
        path = vocab_path()
        if not path.exists():
            showWarning(f"Missing JLPT vocabulary CSV: {path}")
            return

        try:
            self.run_button.setEnabled(False)
            self.export_button.setEnabled(False)
            note_type_names = self.selected_note_types()
            match_mode = self.mode_combo.currentData()
            field_rules = self.selected_field_rules(note_type_names, match_mode)
            by_frequency = self.by_frequency_checkbox.isChecked()
            by_interval = self.by_interval_checkbox.isChecked()
            exclude_suspended = self.exclude_suspended_checkbox.isChecked()
            dark_mode = is_dark_mode()
            if dark_mode:
                self.output.setStyleSheet("QTextBrowser { background-color: #1f1f1f; color: #e5e7eb; }")
            else:
                self.output.setStyleSheet("QTextBrowser { background-color: #ffffff; color: #202124; }")

            entries = load_jlpt_entries(path)
            match_keys, anki_stats = collect_anki_keys_from_collection(
                mw.col,
                note_type_names,
                field_rules,
                exclude_suspended=exclude_suspended,
            )
            self.summary, self.missing_rows, self.unlearned_rows = summarize(
                entries,
                match_keys,
                match_mode,
                by_frequency=by_frequency,
                by_interval=by_interval,
            )
            self.status_rows = vocab_status_rows(entries, match_keys, match_mode)
            self.metadata = {
                "profile_dir": mw.pm.profileFolder(),
                "db_copy": "Anki add-on current collection API",
                "jlpt_vocab": str(path),
                "note_type_names": note_type_names,
                "field_mappings": self.selected_config()["field_mappings"],
                "match_mode": match_mode,
                "by_frequency": by_frequency,
                "by_interval": by_interval,
                "exclude_suspended": exclude_suspended,
                "dark_mode": dark_mode,
                "anki_stats": anki_stats,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
            self.output.setHtml(format_summary_html(self.summary, self.metadata))
            self.export_button.setEnabled(True)
        except Exception as exc:
            showWarning(str(exc))
        finally:
            self.run_button.setEnabled(True)

    def export_reports(self) -> None:
        if not self.summary:
            showWarning("Run coverage analysis before exporting.")
            return
        default_dir = Path(mw.pm.profileFolder()) / "jlpt_coverage_reports"
        directory = QFileDialog.getExistingDirectory(self, "Export JLPT Vocabulary Status", str(default_dir))
        if not directory:
            return
        status_path = write_vocab_status_report(
            Path(directory),
            self.status_rows,
        )
        showInfo(f"CSV exported:\n{status_path}")


def show_coverage_dialog() -> None:
    dialog = CoverageDialog()
    dialog.exec()


def setup_menu() -> None:
    action = QAction("JLPT Coverage", mw)
    action.triggered.connect(show_coverage_dialog)
    mw.form.menuTools.addAction(action)


setup_menu()
