from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from jlpt_coverage.core import load_jlpt_entries
from jlpt_coverage.extract import (
    VerifiedAlternative,
    iter_vocab_rows,
    kanji_alternative_forms,
    load_verified_alternatives,
)


class ExtractVocabTests(unittest.TestCase):
    def test_kanji_alternative_forms_uses_only_leading_variant_clause(self) -> None:
        self.assertEqual(kanji_alternative_forms("称える・讃える"), ("称える", "讃える"))
        self.assertEqual(kanji_alternative_forms("撒く；「蒔く」と同語源"), ("撒く",))
        self.assertEqual(kanji_alternative_forms("「高等学校」の略"), ())

    def test_only_frequency_conflicts_retain_kanji_alternatives(self) -> None:
        rows = [
            self.source_row("eggrolls::5-N1::3-低频", "たたえる", "たたえる", "湛える"),
            self.source_row("eggrolls::5-N1::1-高频", "たたえる", "たたえる", "称える・讃える"),
            self.source_row("eggrolls::3-N3::3-低频", "なす", "なす", "茄子"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle, delimiter="\t").writerows(rows)

            extracted = list(iter_vocab_rows(source))

        self.assertEqual(extracted[0]["word_alternatives"], "湛える")
        self.assertEqual(extracted[1]["word_alternatives"], "称える;讃える")
        self.assertEqual(extracted[2]["word_alternatives"], "")

    def test_loader_accepts_legacy_vocab_without_alternatives_column(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vocab = Path(directory) / "vocab.csv"
            with vocab.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("level", "frequency", "word_plain", "reading"),
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "level": "N1",
                        "frequency": "高频",
                        "word_plain": "称える",
                        "reading": "たたえる",
                    }
                )

            entries = load_jlpt_entries(vocab)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].word_alternatives, "")

    def test_verified_alternatives_are_added_to_non_conflicting_rows(self) -> None:
        rows = [self.source_row("eggrolls::2-N4", "ひどい", "ひどい", "酷い")]
        rows[0][2] = "verified-note-id"

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle, delimiter="\t").writerows(rows)

            extracted = list(
                iter_vocab_rows(
                    source,
                    verified_alternatives={
                        "verified-note-id": (VerifiedAlternative("酷い", "", "vocab_plus"),)
                    },
                )
            )

        self.assertEqual(extracted[0]["word_alternatives"], "酷い")

    def test_verified_common_glyph_variant_is_accepted(self) -> None:
        rows = [self.source_row("eggrolls::3-N3::3-低频", "つかむ", "つかむ", "摑む")]
        rows[0][2] = "verified-note-id"

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle, delimiter="\t").writerows(rows)

            extracted = list(
                iter_vocab_rows(
                    source,
                    verified_alternatives={
                        "verified-note-id": (
                            VerifiedAlternative("摑む", "", "vocab_plus"),
                            VerifiedAlternative("掴む", "", "vocab_plus"),
                        )
                    },
                )
            )

        self.assertEqual(extracted[0]["word_alternatives"], "摑む;掴む")

    def test_verified_alternative_must_still_match_source_vocab_plus(self) -> None:
        rows = [self.source_row("eggrolls::2-N4", "ひどい", "ひどい", "酷い")]
        rows[0][2] = "verified-note-id"

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle, delimiter="\t").writerows(rows)

            with self.assertRaisesRegex(ValueError, "not present in source VocabPlus"):
                list(
                    iter_vocab_rows(
                        source,
                        verified_alternatives={
                            "verified-note-id": (VerifiedAlternative("辛い", "", "vocab_plus"),)
                        },
                    )
                )

    def test_verified_alternatives_file_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alternatives.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("note_id", "word_alternative", "reading", "evidence"),
                )
                writer.writeheader()
                row = {
                    "note_id": "note-1",
                    "word_alternative": "酷い",
                    "reading": "ひどい",
                    "evidence": "jmdict:1634130",
                }
                writer.writerow(row)
                writer.writerow(row)

            alternatives = load_verified_alternatives(path)

        self.assertEqual(
            alternatives,
            {"note-1": (VerifiedAlternative("酷い", "ひどい", "jmdict:1634130"),)},
        )

    @staticmethod
    def source_row(deck: str, word: str, reading: str, vocab_plus: str) -> list[str]:
        row = [""] * 39
        row[0] = "eggrolls-JLPT10k-v3.5"
        row[1] = deck
        row[3] = word
        row[6] = reading
        row[9] = vocab_plus
        row[38] = deck.split("::")[-1]
        return row


if __name__ == "__main__":
    unittest.main()
