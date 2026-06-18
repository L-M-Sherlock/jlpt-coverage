from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from jlpt_coverage.core import JlptEntry
from jlpt_coverage.yomitan import (
    YOMITAN_BANK_FILENAMES,
    dictionary_data,
    display_value_for_entry,
    expected_filenames,
    package_dictionary,
    write_dictionary_files,
)


class YomitanDictionaryTests(unittest.TestCase):
    def test_display_value_includes_frequency_for_n1_to_n3(self) -> None:
        self.assertEqual(display_value_for_entry(JlptEntry("N2", "高频", "見る", "みる")), "N2高频")
        self.assertEqual(display_value_for_entry(JlptEntry("N3", "低频", "作り", "つくり")), "N3低频")

    def test_display_value_uses_level_only_for_n4_and_n5(self) -> None:
        self.assertEqual(display_value_for_entry(JlptEntry("N4", "未分频", "読む", "よむ")), "N4")
        self.assertEqual(display_value_for_entry(JlptEntry("N5", "未分频", "高校", "こうこう")), "N5")

    def test_dictionary_data_removes_exact_duplicate_metadata(self) -> None:
        entries = [
            JlptEntry("N2", "低频", "甘み", "あまみ"),
            JlptEntry("N2", "低频", "甘み", "あまみ"),
        ]

        data = dictionary_data(entries, "2026.06.17.0")

        self.assertEqual(data.entry_count, 1)
        self.assertEqual(data.duplicate_rows, 1)

    def test_dictionary_data_keeps_same_word_reading_with_different_labels(self) -> None:
        entries = [
            JlptEntry("N4", "未分频", "先", "さき"),
            JlptEntry("N5", "未分频", "先", "さき"),
            JlptEntry("N2", "中频", "まく", "まく"),
            JlptEntry("N2", "高频", "まく", "まく"),
        ]

        data = dictionary_data(entries, "2026.06.17.0")

        self.assertEqual(data.entry_count, 4)
        self.assertEqual(data.banks_by_level["N4"][0][2]["frequency"]["displayValue"], "N4")
        self.assertEqual(data.banks_by_level["N5"][0][2]["frequency"]["displayValue"], "N5")
        self.assertEqual(data.banks_by_level["N2"][0][2]["frequency"]["displayValue"], "N2中频")
        self.assertEqual(data.banks_by_level["N2"][1][2]["frequency"]["displayValue"], "N2高频")

    def test_write_and_package_dictionary_use_zip_root_files(self) -> None:
        entries = [
            JlptEntry("N1", "高频", "昭和", "しょうわ"),
            JlptEntry("N5", "未分频", "高校", "こうこう"),
        ]
        data = dictionary_data(entries, "2026.06.17.0")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "dictionary"
            zip_path = root / "eggrolls-jlpt-yomitan.zip"
            write_dictionary_files(data, output_dir)
            package_dictionary(output_dir, zip_path)

            self.assertTrue((output_dir / "index.json").exists())
            for filename in YOMITAN_BANK_FILENAMES:
                self.assertTrue((output_dir / filename).exists())

            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(set(archive.namelist()), set(expected_filenames()))
                self.assertTrue(all("/" not in name for name in archive.namelist()))


if __name__ == "__main__":
    unittest.main()
