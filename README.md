# JLPT Coverage for Anki

[Chinese README](README_CN.md)

JLPT Coverage is an Anki add-on for Japanese learners who mine vocabulary from native content and also want a clear view of their JLPT N1-N5 vocabulary coverage.

The main use case is the workflow described in the [Donkuri mining guide](https://donkuri.github.io/learn-japanese/mining/): you use tools such as Yomitan and Anki to create cards from visual novels, anime, novels, manga, games, or other immersion material. This add-on does not replace mining. It helps you answer a separate question: how much of a JLPT vocabulary list have you already mined, reviewed, or still missed?

## What It Does

- Shows JLPT coverage for selected Anki note types.
- Supports mining-oriented note types such as `Lapis`, `Kaishi 1.5k`, and `Kaishi 1.5k zh-CH`.
- Lets you configure term and reading fields per note type from the fields that already exist in your collection.
- Reports both card coverage and learning coverage.
- Can split results by source frequency band.
- Can show Young and Mature coverage using Anki's interval convention.
- Exports one vocabulary status CSV with missing and unlearned flags.
- Can add `JLPT::N1` through `JLPT::N5` tags, plus N1-N3 frequency tags, to matching Anki notes.
- Bundles the project-local JLPT vocabulary CSV, so the add-on does not read the original source deck files at runtime.

The coverage and CSV export actions only read your currently open Anki collection through Anki's add-on API. The optional `Tag JLPT` action writes note tags to matching notes.

## Who This Is For

This tool is intended for learners who:

- Mine Japanese vocabulary into Anki from immersion material.
- Use Lapis, Kaishi, or another note type with separate term and reading fields.
- Prefer continuing their mining workflow instead of switching to a premade JLPT deck.
- Still want to know which JLPT vocabulary items are already represented in their mining cards.
- Want to identify JLPT gaps before or during exam preparation.

It is a coverage and reporting tool, not an SRS scheduler, a JLPT course, or a replacement vocabulary deck.

## Installation

Download `jlpt_coverage.ankiaddon` from the latest [GitHub Release](https://github.com/L-M-Sherlock/jlpt-coverage/releases), then install it in Anki:

1. Open Anki.
2. Go to `Tools -> Add-ons`.
3. Choose `Install from file...`.
4. Select `jlpt_coverage.ankiaddon`.
5. Restart Anki.
6. Open `Tools -> JLPT Coverage`.

GitHub Actions artifacts are always wrapped by GitHub in an outer `.zip` file. If you download a workflow artifact instead of a Release asset, unzip it first and install the `.ankiaddon` file inside.

## Basic Use

Open `Tools -> JLPT Coverage` in Anki.

1. Select the note types to include.
2. Choose the term field and reading field for each selected note type.
3. Choose a match mode.
4. Optionally enable frequency breakdown, Young/Mature breakdown, or suspended-card exclusion.
5. Click `Run`.
6. Click `Save Defaults` if you want to reuse the same selections.
7. Choose an export level filter if you only want one level or a target level range.
8. Click `Export CSV` to save the vocabulary status file.
9. Click `Tag JLPT` to add JLPT level and N1-N3 frequency tags to matching notes.

The dialog loads note types and fields from the current Anki collection, so you do not need to type note type or field names manually.

## Default Field Mappings

The add-on ships with defaults for the note types this project was built around:

| Note type | Term field | Reading field |
| --- | --- | --- |
| `Lapis` | `Expression` | `ExpressionReading` |
| `Kaishi 1.5k` | `Word` | `Word Reading` |
| `Kaishi 1.5k zh-CH` | `Word` | `Word Reading` |

You can select different fields in the UI for any note type in your collection.

## Match Modes

| Mode | Meaning | Best for |
| --- | --- | --- |
| `word-or-reading` | A JLPT entry is covered if either the written form or the reading matches. | Default mining coverage checks. |
| `word-and-reading` | A JLPT entry is covered only if both the written form and the reading match. | Strict coverage checks that avoid reading-only or word-only false positives. |
| `reading` | Only readings are compared. | Avoiding missed matches caused by spelling, kana/kanji, or orthographic differences. |
| `word` | Only written forms are compared. | Stricter checks where the exact written vocabulary item matters more. |

The JLPT side uses `word_plain` as the written form and `reading` as the reading.

## JLPT Note Tags

`Tag JLPT` uses the same note type, field, and suspended-card settings shown in the dialog. It does not use the coverage match-mode selector: tagging always requires the same JLPT vocabulary entry's written form and reading to both match the note.

The generated level tags are `JLPT::N1`, `JLPT::N2`, `JLPT::N3`, `JLPT::N4`, and `JLPT::N5`. N1, N2, and N3 matches also receive frequency tags such as `JLPT::N2::高频`, `JLPT::N2::中频`, or `JLPT::N2::低频`. Anki tags are note-level, so every card generated from a tagged note will show the same tag.

Re-running the action only adds missing tags. It does not remove existing JLPT tags, so stale tags must be cleaned manually if you change fields, note types, or matching preferences later.

## Report Metrics

| Metric | Meaning |
| --- | --- |
| `Total` | Number of JLPT vocabulary entries in that level or bucket. |
| `Card` / `Card%` | Entries that match at least one selected Anki note. |
| `Learned` / `Learn%` | Entries that match at least one selected Anki note with a card whose `reps > 0`. |
| `Missing` | Entries with no matching selected Anki note. |
| `Unlearned` | Entries that match a selected note but have no matching card with `reps > 0`. |
| `Young` / `Young%` | Entries with at least one matching card whose `ivl < 21`. |
| `Mature` / `Mature%` | Entries with at least one matching card whose `ivl >= 21`. |

Young and Mature follow Anki's own interval-based convention.

## Frequency Breakdown

When enabled, the report expands each JLPT level by the frequency band found in the source vocabulary data.

Current source behavior:

- N1, N2, and N3 use high, medium, and low frequency bands.
- N4 and N5 are now separate levels in the bundled vocabulary.

## CSV Export

`Export CSV` writes one file containing the JLPT vocabulary list plus status flags:

```text
level,frequency,word_plain,reading,missing,unlearned
```

- `missing=1` means no selected Anki note matched that JLPT entry.
- `unlearned=1` means the entry matched a selected note, but no matching card has `reps > 0`.

The CSV is designed for sorting, filtering, and planning follow-up mining or JLPT review.

You can export all levels, one specific level, or a target level range. For example, `up to N2` exports N2, N3, N4, and N5 entries. The legacy `N4+N5` filter is still accepted for older combined vocabulary files.

## Language Support

The add-on supports English and Simplified Chinese. It follows Anki's default language.

Localization is implemented with the bundled `python_i18n` git submodule and JSON locale files under `anki_addon/jlpt_coverage/locale/`.

## Command Line Tool

The Anki add-on is the primary interface. A CLI is also available for one-off checks.

Run it directly from GitHub without cloning the repository:

```bash
uvx --from git+https://github.com/L-M-Sherlock/jlpt-coverage.git jlpt-coverage
```

If you have multiple Anki profiles, pass the profile explicitly:

```bash
uvx --from git+https://github.com/L-M-Sherlock/jlpt-coverage.git jlpt-coverage \
  --profile-dir "$HOME/Library/Application Support/Anki2/<ProfileName>"
```

Inside a local checkout, run the installed console command:

```bash
uv run jlpt-coverage
```

Common options:

```bash
uv run jlpt-coverage --reading-only
uv run jlpt-coverage --strict-word
uv run jlpt-coverage --match-mode word-and-reading
uv run jlpt-coverage --by-frequency
uv run jlpt-coverage --by-interval
uv run jlpt-coverage --exclude-suspended
uv run jlpt-coverage --export-level N2
uv run jlpt-coverage --export-up-to N2
uv run jlpt-coverage --language en_US
uv run jlpt-coverage --language zh_CN
```

The CLI auto-detects a single local Anki profile when possible. You can also pass `--profile-dir` or set `ANKI_PROFILE_DIR`.

The CLI copies `collection.anki2` and related SQLite sidecar files before connecting to SQLite. It does not connect directly to the live collection database. Reports are written to `./jlpt_coverage_reports` by default.

## Development

Install [uv](https://docs.astral.sh/uv/), then clone the repository and initialize submodules:

```bash
git submodule update --init --recursive
uv sync
```

Build and validate the add-on:

```bash
uv run scripts/package_anki_addon.py
uv run scripts/validate_anki_addon.py
```

The output is:

```text
dist/jlpt_coverage.ankiaddon
```

Extract the project-local vocabulary CSV from the original source deck:

```bash
uv run scripts/extract_jlpt_vocab.py
```

This writes only the columns needed by the tool into `jlpt_coverage/data/jlpt_vocab.csv`.

The GitHub Actions workflow builds and validates the add-on on pushes and pull requests. For `v*` tags, it also uploads `jlpt_coverage.ankiaddon` directly to the GitHub Release.

## Vocabulary Data and Acknowledgements

JLPT vocabulary data is extracted from the eggrolls JLPT10k deck in [5mdld/anki-jlpt-decks](https://github.com/5mdld/anki-jlpt-decks).

This project keeps only the fields needed for coverage reporting:

- `level`
- `frequency`
- `word_plain`
- `reading`

Thanks to the maintainers of that deck and to the authors of the tools and note types used by the Japanese mining community.
