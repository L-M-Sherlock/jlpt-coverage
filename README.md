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
- Bundles the project-local JLPT vocabulary CSV, so the add-on does not read the original source deck files at runtime.

The add-on reads your currently open Anki collection through Anki's add-on API and does not write to the collection.

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
7. Click `Export CSV` to save the vocabulary status file.

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
| `reading` | Only readings are compared. | Avoiding missed matches caused by spelling, kana/kanji, or orthographic differences. |
| `word` | Only written forms are compared. | Stricter checks where the exact written vocabulary item matters more. |

The JLPT side uses `word_plain` as the written form and `reading` as the reading.

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

- N1 uses high, medium, and low frequency bands.
- N2 and N3 use high and lower-frequency bands.
- N4 and N5 are merged by the source deck as `N4+N5`, and cannot be reliably split into separate N4 and N5 levels from this file alone.

## CSV Export

`Export CSV` writes one file containing the JLPT vocabulary list plus status flags:

```text
level,frequency,word_plain,reading,missing,unlearned
```

- `missing=1` means no selected Anki note matched that JLPT entry.
- `unlearned=1` means the entry matched a selected note, but no matching card has `reps > 0`.

The CSV is designed for sorting, filtering, and planning follow-up mining or JLPT review.

## Language Support

The add-on supports English and Simplified Chinese. It follows Anki's default language.

Localization is implemented with the bundled `python_i18n` git submodule and JSON locale files under `anki_addon/jlpt_coverage/locale/`.

## Command Line Tool

The Anki add-on is the primary interface. A CLI is also available for local checks and development:

```bash
uv run scripts/check_jlpt_coverage.py
```

Common options:

```bash
uv run scripts/check_jlpt_coverage.py --reading-only
uv run scripts/check_jlpt_coverage.py --strict-word
uv run scripts/check_jlpt_coverage.py --by-frequency
uv run scripts/check_jlpt_coverage.py --by-interval
uv run scripts/check_jlpt_coverage.py --exclude-suspended
uv run scripts/check_jlpt_coverage.py --language en_US
uv run scripts/check_jlpt_coverage.py --language zh_CN
```

The CLI copies `collection.anki2` and related SQLite sidecar files before connecting to SQLite. It does not connect directly to the live collection database.

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

This writes only the columns needed by the tool into `data/jlpt_vocab.csv`.

The GitHub Actions workflow builds and validates the add-on on pushes and pull requests. For `v*` tags, it also uploads `jlpt_coverage.ankiaddon` directly to the GitHub Release.

## Vocabulary Data and Acknowledgements

JLPT vocabulary data is extracted from the eggrolls JLPT10k deck in [5mdld/anki-jlpt-decks](https://github.com/5mdld/anki-jlpt-decks).

This project keeps only the fields needed for coverage reporting:

- `level`
- `frequency`
- `word_plain`
- `reading`

Thanks to the maintainers of that deck and to the authors of the tools and note types used by the Japanese mining community.
