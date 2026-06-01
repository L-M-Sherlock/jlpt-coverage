# JLPT Coverage

Configuration fields:

- `note_types`: Anki note types to include.
- `field_mappings`: Per-note-type fields used for matching.
  - `term`: field containing the written form.
  - `reading`: field containing the reading.
- `match_mode`: `word-or-reading`, `word-and-reading`, `reading`, or `word`.
- `by_frequency`: `true` to split output by the JLPT source frequency band.
- `by_interval`: `true` to show Young/Mature coverage. Young is `ivl < 21`; Mature is `ivl >= 21`.
- `exclude_suspended`: `true` to ignore suspended cards when counting coverage.
- `export_level_filter`: CSV export filter. Use `all`, `only:N2`, or `up-to:N2`.

JLPT tagging uses the current note type, field, and suspended-card selections,
always requires strict written-form and reading matching, and writes fixed note
tags: `JLPT::N1`, `JLPT::N2`, `JLPT::N3`, `JLPT::N4`, and `JLPT::N5`.
N1, N2, and N3 matches also receive frequency tags such as
`JLPT::N2::高频`, `JLPT::N2::中频`, and `JLPT::N2::低频`.
