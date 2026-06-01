# JLPT Coverage Checker Add-on

Adds `Tools -> JLPT Coverage` in Anki.

The packaged add-on bundles `data/jlpt_vocab.csv` and uses the current Anki collection through Anki's add-on API. Coverage and export actions are read-only; `Tag JLPT` writes JLPT level tags plus N1-N3 frequency tags to notes whose written form and reading both match the same JLPT entry.

Export CSV writes one vocabulary status file with `level,frequency,word_plain,reading,missing,unlearned`.
The export level filter can write all levels, one specific level, or a target range such as N2 through N5.

The Young/Mature option uses Anki intervals: Young is `ivl < 21`; Mature is `ivl >= 21`.

The UI is localized through the bundled `python_i18n` submodule and supports English and Simplified Chinese, following Anki's default language.
