# JLPT Coverage

Configuration fields:

- `note_types`: Anki note types to include.
- `field_mappings`: Per-note-type fields used for matching.
  - `term`: field containing the written form.
  - `reading`: field containing the reading.
- `match_mode`: `word-or-reading`, `reading`, or `word`.
- `by_frequency`: `true` to split output by the JLPT source frequency band.
- `by_interval`: `true` to show Young/Mature coverage. Young is `ivl < 21`; Mature is `ivl >= 21`.
- `exclude_suspended`: `true` to ignore suspended cards when counting coverage.
- `export_level_filter`: CSV export filter. Use `all`, `only:N2`, or `up-to:N2`.
