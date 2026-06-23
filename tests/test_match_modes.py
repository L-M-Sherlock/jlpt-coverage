from __future__ import annotations

import unittest

from jlpt_coverage.cli import parse_args
from jlpt_coverage.core import JlptEntry, classify_match
from jlpt_coverage.text import text_keys


class MatchModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = JlptEntry("N2", "高频", "見る", "みる")

    def classify(self, word: str, reading: str, mode: str) -> bool:
        covered, _matched_by = classify_match(self.entry, text_keys(word), text_keys(reading), mode)
        return covered

    def test_word_or_reading_matches_either_side(self) -> None:
        self.assertTrue(self.classify("見る", "", "word-or-reading"))
        self.assertTrue(self.classify("", "みる", "word-or-reading"))

    def test_placeholder_mark_is_ignored_for_word_and_reading_matching(self) -> None:
        entry = JlptEntry("N5", "未分频", "〜か月", "〜かげつ")

        covered, matched_by = classify_match(entry, text_keys("か月"), text_keys("かげつ"), "word-and-reading")

        self.assertTrue(covered)
        self.assertEqual(matched_by, "word+reading")

    def test_word_and_reading_requires_both_sides(self) -> None:
        self.assertFalse(self.classify("見る", "", "word-and-reading"))
        self.assertFalse(self.classify("", "みる", "word-and-reading"))
        self.assertTrue(self.classify("見る", "みる", "word-and-reading"))

    def test_word_and_reading_rejects_wrong_reading(self) -> None:
        self.assertFalse(self.classify("見る", "よむ", "word-and-reading"))

    def test_pure_katakana_entry_matches_reading_by_word_not_source_language(self) -> None:
        entry = JlptEntry("N4", "未分频", "アイスクリーム", "ice cream")

        covered_by_katakana, _matched_by = classify_match(entry, set(), text_keys("アイスクリーム"), "reading")
        covered_by_hiragana, _matched_by = classify_match(entry, set(), text_keys("あいすくりーむ"), "reading")
        covered_by_source, _matched_by = classify_match(entry, set(), text_keys("ice cream"), "reading")

        self.assertTrue(covered_by_katakana)
        self.assertTrue(covered_by_hiragana)
        self.assertFalse(covered_by_source)

    def test_mixed_katakana_entry_uses_source_reading(self) -> None:
        entry = JlptEntry("N4", "未分频", "電子レンジ", "でんしレンジ")

        covered_by_reading, _matched_by = classify_match(entry, set(), text_keys("でんしレンジ"), "reading")
        covered_by_word, _matched_by = classify_match(entry, set(), text_keys("電子レンジ"), "reading")

        self.assertTrue(covered_by_reading)
        self.assertFalse(covered_by_word)

    def test_word_and_reading_is_accepted_by_cli_parser(self) -> None:
        args = parse_args(["--match-mode", "word-and-reading"])

        self.assertEqual(args.match_mode, "word-and-reading")


if __name__ == "__main__":
    unittest.main()
