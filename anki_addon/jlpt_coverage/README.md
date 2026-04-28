# JLPT Coverage Checker Add-on

Adds `Tools -> JLPT Coverage` in Anki.

The packaged add-on bundles `data/jlpt_vocab.csv` and uses the current Anki collection through Anki's add-on API. It does not write to the collection.

Export CSV writes one vocabulary status file with `level,frequency,word_plain,reading,missing,unlearned`.

The Young/Mature option uses Anki intervals: Young is `ivl < 21`; Mature is `ivl >= 21`.
