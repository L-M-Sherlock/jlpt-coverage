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

    def test_word_and_reading_requires_both_sides(self) -> None:
        self.assertFalse(self.classify("見る", "", "word-and-reading"))
        self.assertFalse(self.classify("", "みる", "word-and-reading"))
        self.assertTrue(self.classify("見る", "みる", "word-and-reading"))

    def test_word_and_reading_rejects_wrong_reading(self) -> None:
        self.assertFalse(self.classify("見る", "よむ", "word-and-reading"))

    def test_word_and_reading_is_accepted_by_cli_parser(self) -> None:
        args = parse_args(["--match-mode", "word-and-reading"])

        self.assertEqual(args.match_mode, "word-and-reading")


if __name__ == "__main__":
    unittest.main()
