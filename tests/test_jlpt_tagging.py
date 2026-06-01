from __future__ import annotations

import unittest

from jlpt_coverage.core import (
    JlptEntry,
    build_jlpt_level_indexes,
    jlpt_tag_for_level,
    jlpt_tags_for_target,
    matched_jlpt_levels,
    matched_jlpt_levels_strict,
    matched_jlpt_targets_strict,
)
from jlpt_coverage.text import text_keys


class JlptTaggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.indexes = build_jlpt_level_indexes(
            [
                JlptEntry("N2", "高频", "見る", "みる"),
                JlptEntry("N3", "中频", "観る", "みる"),
                JlptEntry("N4", "未分频", "読む", "よむ"),
                JlptEntry("N1", "高频", "称える", "たたえる"),
                JlptEntry("N1", "低频", "称える", "たたえる"),
                JlptEntry("N4+N5", "未分频", "食べる", "たべる"),
            ]
        )

    def tags_for_strict_match(self, word: str, reading: str) -> set[str]:
        targets = matched_jlpt_targets_strict(text_keys(word), text_keys(reading), self.indexes)
        tags: set[str] = set()
        for target in targets:
            tags.update(jlpt_tags_for_target(target))
        return tags

    def test_word_mode_matches_written_form_only(self) -> None:
        levels = matched_jlpt_levels(text_keys("観る"), text_keys("みる"), self.indexes, "word")

        self.assertEqual(levels, {"N3"})

    def test_reading_mode_can_match_multiple_levels(self) -> None:
        levels = matched_jlpt_levels(text_keys("観る"), text_keys("みる"), self.indexes, "reading")

        self.assertEqual(levels, {"N2", "N3"})

    def test_word_or_reading_returns_all_matched_levels(self) -> None:
        levels = matched_jlpt_levels(text_keys("見る"), text_keys("みる"), self.indexes, "word-or-reading")

        self.assertEqual(levels, {"N2", "N3"})

    def test_strict_tagging_requires_same_entry_word_and_reading(self) -> None:
        levels = matched_jlpt_levels_strict(text_keys("見る"), text_keys("みる"), self.indexes)

        self.assertEqual(levels, {"N2"})

    def test_strict_tagging_rejects_reading_only_homophone_match(self) -> None:
        levels = matched_jlpt_levels_strict(text_keys("見る"), text_keys("よむ"), self.indexes)

        self.assertEqual(levels, set())

    def test_n1_to_n3_strict_tagging_includes_frequency_tag(self) -> None:
        self.assertEqual(self.tags_for_strict_match("見る", "みる"), {"JLPT::N2", "JLPT::N2::高频"})

    def test_n4_strict_tagging_does_not_include_frequency_tag(self) -> None:
        self.assertEqual(self.tags_for_strict_match("読む", "よむ"), {"JLPT::N4"})

    def test_ambiguous_strict_frequency_matches_add_all_frequency_tags(self) -> None:
        self.assertEqual(
            self.tags_for_strict_match("称える", "たたえる"),
            {"JLPT::N1", "JLPT::N1::高频", "JLPT::N1::低频"},
        )

    def test_legacy_combined_levels_are_skipped_for_tagging(self) -> None:
        levels = matched_jlpt_levels_strict(text_keys("食べる"), text_keys("たべる"), self.indexes)

        self.assertEqual(levels, set())
        self.assertEqual(self.indexes.skipped_levels, {"N4+N5": 1})

    def test_jlpt_tag_for_level_uses_hierarchical_prefix(self) -> None:
        self.assertEqual(jlpt_tag_for_level("N1"), "JLPT::N1")


if __name__ == "__main__":
    unittest.main()
