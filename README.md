# BigNoteBox Spelling Pack

More dictionaries for the spellchecker in [BigNoteBox](https://github.com/DukulWoW/BigNoteBox).
BigNoteBox itself comes with English (US and UK); this pack adds other languages.

| Folder | Language | Word list | License |
|---|---|---|---|
| `BigNoteBox_Spell_frFR` | French | Dictionnaire "Classique" by Olivier R. ([grammalecte.net](https://grammalecte.net/)) | MPL 2.0 |
| `BigNoteBox_Spell_deDE` | German | igerman98 by Bjoern Jacke with the frami additions by Franz Michael Baumann ([LibreOffice](https://github.com/LibreOffice/dictionaries/tree/master/de)) | GPL 2 or 3 |

Each language is its own load-on-demand folder: only the language you use is loaded,
the first time a note is checked in it.

## Using it

1. Install the pack next to BigNoteBox (BigNoteBox 2.1.0 or later).
2. Settings > Modules > Spelling: the language's flag is in color once it is installed.
   Pick it under Language to check every note in it.
3. Or give one note its own language: right-click a marked word in the note, then Language.

## Building

The word lists are generated, never edited by hand. They are built from the Hunspell files in
`sources/` by the build script in `tools/` (`dict-build.py`, with `hunspell_expand.py`), which
expands every word form. The scripts are a copy from BigNoteBox's development tree and expect
that layout: run `python dict-build.py --lang fr` or `--lang de` with the sources in
`_work/dict-src/<lang>/` and this folder next to BigNoteBox's.

| Folder | Source files | From |
|---|---|---|
| `sources/fr` | `fr.dic`, `fr.aff` | [LibreOffice dictionaries, fr_FR](https://github.com/LibreOffice/dictionaries/tree/master/fr_FR) |
| `sources/de` | `de_DE_frami.dic`, `de_DE_frami.aff` | [LibreOffice dictionaries, de](https://github.com/LibreOffice/dictionaries/tree/master/de) |

Each addon folder carries the license of its word list in `LICENSE` (German also the GPL text in
`COPYING`); each `sources/` folder keeps the dictionary's own README and license files.

German compound words (Gildenbank, Questgeber) are checked by splitting them into known words; Settings > Modules > Spelling can limit that to the compounds the German dictionary itself allows.

## License

The repository as a whole is under the GNU General Public License version 3 (`LICENSE`), as is
the German word list (GPL 2 or 3, its choice). The French word list stays under the Mozilla Public
License 2.0, the license of its source; its terms are in `BigNoteBox_Spell_frFR/LICENSE`.
