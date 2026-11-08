"""Builds the spellchecker's word lists.

    python _work/tools/dict-build.py            (uses _work/dict-src/ when there)
    python _work/tools/dict-build.py --fetch    (downloads the lists again first)
    python _work/tools/dict-build.py --lang fr  (French, into ../BigNoteBox_SpellPack)
    python _work/tools/dict-build.py --lang de  (German, the same place)

Source: the English Speller Database (ESDB, the successor of SCOWL) by Kevin
Atkinson, through its list maker at app.aspell.net: size 60 (the size spell
checkers use), variant level "common", diacritics both, hacker words and roman
numerals. US = spelling US, UK = spelling GB(-ise). Its copyright notice ships
as BigNoteBox_Spell/LICENSE (the list's own header, word for word).

Writes, in BigNoteBox_Spell/:
    enUS.lua      every US word
    enGB.lua      the UK list as the US list plus `add` minus `drop`
    (the game words, WOW_WORDS below, go to BigNoteBox/Features/SpellWords.lua)
    LICENSE

Format (read by BigNoteBox/Features/Spellcheck.lua): buckets keyed by
byte length * 256 + first byte, each one string of same-length words joined
with nothing, so a word is found with one plain string.find at a multiple
of its length. No sorting is used on the Lua side (string comparison follows
the C locale there, not bytes). Bytes over 127 are written as \\ddd so the
files stay ASCII.
"""
import os
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "_work", "dict-src")
OUT = os.path.join(ROOT, "BigNoteBox_Spell")

BASE = ("http://app.aspell.net/create?max_size=60&spelling={}&max_variant=1&diacritic=both"
        "&special=hacker&special=roman-numerals&download=wordlist&encoding=utf-8&format=inline")
LISTS = {"us": "US", "gb": "GBs"}

# Game and chat words a note is full of. Lowercase; a word already in the
# English lists is dropped by the build, so this can be generous. Capitalized
# names (zones, bosses, races) are left to "Skip names". Raid and dungeon
# short forms (ICC, BWL) since words in capitals are checked.
WOW_WORDS = """
addon addons afk aggro aoe arena arenas aura auras azerite
bg bgs bis bop boe brb buff buffs buffed bugged
cd cds cooldown cooldowns crit crits critted
debuff debuffs debuffed dispel dispels dispelled dmg dot dots dps druid druids dungeon dungeons
emote emotes evoker evokers
farmable flightpath flightpaths gankers ganking gearscore gg gl guildie guildies guildmate guildmates
hearth hearthed hearthing hearthstone heroics hots hp hps
ilvl ilvls instanced
keybind keybinds keybinding keystone keystones kited kiting
lfg lfr lol loot looted looting lvl lvls lvling
macro macros mana minimap mob mobs mog mogs mount mounts mythic mythics
nerf nerfs nerfed noob noobs np npc npcs
omg op paladin paladins pally pallies plz pls proc procs procced pug pugs pugging pve pvp
questline questlines quest quests questing raid raids raider raiders raiding realm realms
rep respawn respawns respawned rez rezzed rng
shaman shamans spawn spawns spawned spec specs specced stun stuns stunned
tank tanks tanked tanking thx toon toons transmog transmogs trinket trinkets ty
ui unlockable warlock warlocks wtb wts xmog xp
ok btw imo irl atm idk tbh gz grats ppl nvm kinda gonna wanna gotta dunno alt alts
dk dks dh dhs rdps mdps cc hc nm ksm affix affixes
mc bwl zg aq ony naxx kara ssc tk bt za swp icc voa uld toc togc eoe rs
bwd bot tofw fl ds msv hof toes tot soo brf hfc en tov nh tos abt
bod ep nya cn sod sfo voti asc atdh nwp lou mfo
rfc wc sfk bfd rfk sm rfd zf brd lbrs ubrs strat scholo mara gnomer
hfr sv sp ub mt ac mgt hor fos pos hos hol cos dtk vh gd uk
"""


def fetch():
    os.makedirs(SRC, exist_ok=True)
    for name, spelling in LISTS.items():
        url = BASE.format(spelling)
        print("fetch", name, url)
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
        with open(os.path.join(SRC, name + ".txt"), "wb") as f:
            f.write(data)


def read_list(name):
    path = os.path.join(SRC, name + ".txt")
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    head, sep, body = text.partition("\n---\n")
    if not sep:
        sys.exit("no '---' line in " + path)
    words = {w.strip() for w in body.split("\n") if w.strip()}
    return head.rstrip() + "\n", words


def lua_str(b):
    out = []
    for c in b:
        if c >= 128 or c < 32 or c in (34, 92):
            out.append("\\%03d" % c)
        else:
            out.append(chr(c))
    return '"' + "".join(out) + '"'


def buckets(words):
    bk = {}
    for w in words:
        b = w.encode("utf-8")
        bk.setdefault(len(b) * 256 + b[0], []).append(b)
    return {k: b"".join(sorted(v)) for k, v in bk.items()}


def lua_table(words, indent="    "):
    lines = []
    for k, v in sorted(buckets(words).items()):
        lines.append("%s[%d] = %s," % (indent, k, lua_str(v)))
    return "\n".join(lines)


HEADER = """-- BigNoteBox_Spell {file} -- generated by _work/tools/dict-build.py, do not edit
--
-- {what}
-- Word list: the English Speller Database (ESDB) by Kevin Atkinson, see LICENSE.
-- Buckets: byte length * 256 + first byte -> same-length words, joined.
"""


def write(name, body):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print("wrote", os.path.relpath(path, ROOT), os.path.getsize(path), "bytes")


def main():
    if "--fetch" in sys.argv or not os.path.exists(os.path.join(SRC, "us.txt")):
        fetch()
    head, us = read_list("us")
    _, gb = read_list("gb")
    for w in us | gb:
        if any(ch.isdigit() for ch in w):
            sys.exit("a word with a digit: " + w)
    add, drop = gb - us, us - gb
    print("US %d words, UK %d (+%d / -%d)" % (len(us), len(gb), len(add), len(drop)))
    os.makedirs(OUT, exist_ok=True)

    write("enUS.lua", HEADER.format(file="enUS.lua", what="English (US), %d words." % len(us))
          + "local words = {\n" + lua_table(us) + "\n}\n"
          + "if BigNoteBox and BigNoteBox.ReceiveSpellData then\n"
          + "    BigNoteBox.ReceiveSpellData(\"enUS\", { words = words, count = %d })\nend\n" % len(us))

    write("enGB.lua", HEADER.format(file="enGB.lua",
          what="English (UK): the US list, plus `add` (%d UK spellings), minus `drop` (%d US ones)."
          % (len(add), len(drop)))
          + "local add = {\n" + lua_table(add) + "\n}\n"
          + "local drop = {\n" + lua_table(drop) + "\n}\n"
          + "if BigNoteBox and BigNoteBox.ReceiveSpellData then\n"
          + "    BigNoteBox.ReceiveSpellData(\"enGB\", { base = \"enUS\", add = add, drop = drop, count = %d })\nend\n"
          % len(gb))

    write_game_words()

    write("LICENSE", "BigNoteBox_Spell: English word lists for BigNoteBox's spellchecker.\n"
          "The lists in enUS.lua and enGB.lua were made from the English Speller\n"
          "Database (ESDB) with the list maker at https://app.aspell.net/create.\n"
          "Its notice, as it came with the lists:\n\n" + head)


GAME_WORDS = os.path.join(ROOT, "BigNoteBox", "Features", "SpellWords.lua")


def write_game_words():
    """The game and chat words, in BigNoteBox itself (always loaded, a few KB):
    every language uses them, so a French player does not load the English
    folder for them (Dukul, 2026-11-01). All of WOW_WORDS, also the ones the
    English lists have (raid, tank, buff are words in French notes too)."""
    wow = set(WOW_WORDS.split())
    body = ("-- BigNoteBox Features/SpellWords.lua -- generated by _work/tools/dict-build.py, do not edit\n"
            "--\n"
            "-- Game and chat words (%d) for the spellchecker, every language.\n"
            "-- Our own list (WOW_WORDS in dict-build.py). Loads after Features/Spellcheck.lua.\n"
            "-- Buckets: byte length * 256 + first byte -> same-length words, joined.\n"
            "local words = {\n" % len(wow)
            + lua_table(wow) + "\n}\n"
            + "if BigNoteBox and BigNoteBox.ReceiveSpellData then\n"
            + "    BigNoteBox.ReceiveSpellData(\"wow\", { words = words, count = %d })\nend\n" % len(wow))
    with open(GAME_WORDS, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(body)
    print("wrote", os.path.relpath(GAME_WORDS, ROOT), os.path.getsize(GAME_WORDS), "bytes")


# ── Other languages: the extra download BigNoteBox_SpellPack ──────
# One load-on-demand folder per language, next to this repo (its own repo, like
# BigNoteBox_FontsCN). Sources are Hunspell files, expanded by hunspell_expand.py.
#     python _work/tools/dict-build.py --lang fr
PACK = os.path.abspath(os.path.join(ROOT, "..", "BigNoteBox_SpellPack"))
FR_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/fr_FR/dictionaries/"
# French elisions: the checker looks the word up without them (l'arbre -> arbre)
FR_ELIDE = ["l'", "d'", "j'", "m'", "n'", "s'", "t'", "c'", "ç'", "qu'",
            "jusqu'", "lorsqu'", "puisqu'", "quoiqu'"]

TOC = """## Interface: 120105, 120100, 16001, 50504, 20506, 11509
## Title: |cff66bb6aB|cff72c476i|cff7ecd82g|cff8ad68eN|cff96df9ao|cffa2e8a6t|cffaef1b2e|cffbafabeB|cffc6ffcao|cffd2ffd6x|r |cffaaaaaaSpelling ({name})|r
## IconTexture: Interface/Addons/BigNoteBox/Assets/icon
## Notes: {name} word list for BigNoteBox's spellchecker. Loaded only when {name} is in use on the Spelling page or a note.
## Author: Dukul
## Group: BigNoteBox
## Version: 1.0.0
## Dependencies: BigNoteBox
## LoadOnDemand: 1

## Category-enUS: Notes & Organization
## Category-deDE: Notizen & Organisation
## Category-esES: Notas y organización
## Category-esMX: Notas y organización
## Category-frFR: Notes et organisation
## Category-itIT: Note e organizzazione

{code}.lua
"""


def pieces(words):
    """The words as the checker sees them: a hyphen splits a word (peut-etre =
    peut + etre; "a-grave" stays: one letter, two bytes), a word with a digit
    is never looked up, a final dot goes."""
    out = set()
    for w in words:
        w = w.rstrip(".")
        if any(ch.isdigit() for ch in w):
            continue
        for part in w.split("-"):
            if part:
                out.add(part)
    return out


def lua_table_raw(words, indent="    "):
    """Buckets with raw UTF-8 bytes: a data string, never drawn, half the size
    of \\ddd escapes for an accented language. Words hold no quote, backslash
    or control byte (checked)."""
    lines = []
    for k, v in sorted(buckets(words).items()):
        if b'"' in v or b"\\" in v or any(c < 32 for c in v):
            sys.exit("a word with a quote, backslash or control byte in bucket %d" % k)
        lines.append(indent.encode() + (b"[%d] = \"" % k) + v + b"\",")
    return b"\n".join(lines)


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", path, os.path.getsize(path), "bytes")


def build_fr():
    import hunspell_expand
    src = os.path.join(SRC, "fr")
    if "--fetch" in sys.argv or not os.path.exists(os.path.join(src, "fr.dic")):
        os.makedirs(src, exist_ok=True)
        for f in ("fr.aff", "fr.dic", "README_dict_fr.txt"):
            print("fetch", FR_URL + f)
            with urllib.request.urlopen(FR_URL + f, timeout=120) as r:
                data = r.read()
            with open(os.path.join(src, f), "wb") as fh:
                fh.write(data)
    forms = hunspell_expand.expand(os.path.join(src, "fr.dic"), os.path.join(src, "fr.aff"))
    words = pieces(forms)
    print("French: %d forms, %d words after the hyphen split" % (len(forms), len(words)))
    out = os.path.join(PACK, "BigNoteBox_Spell_frFR")
    os.makedirs(out, exist_ok=True)
    elide = ", ".join('"%s"' % e for e in FR_ELIDE)
    head = ("-- BigNoteBox_Spell_frFR frFR.lua -- generated by BNB's _work/tools/dict-build.py, do not edit\n"
            "--\n"
            "-- French, %d words (Dictionnaire \"Classique\" by Olivier R., grammalecte.net, MPL 2.0, see LICENSE).\n"
            "-- Buckets: byte length * 256 + first byte -> same-length words, joined. Raw UTF-8.\n"
            "local words = {\n" % len(words))
    tail = ("\n}\n"
            "if BigNoteBox and BigNoteBox.ReceiveSpellData then\n"
            "    BigNoteBox.ReceiveSpellData(\"frFR\", { words = words, count = %d, elide = { %s } })\n"
            "end\n" % (len(words), elide))
    path = os.path.join(out, "frFR.lua")
    with open(path, "wb") as f:
        f.write(head.encode("utf-8") + lua_table_raw(words) + tail.encode("utf-8"))
    print("wrote", path, os.path.getsize(path), "bytes")
    write_text(os.path.join(out, "BigNoteBox_Spell_frFR.toc"), TOC.format(name="French", code="frFR"))
    readme = open(os.path.join(src, "README_dict_fr.txt"), encoding="utf-8").read()
    write_text(os.path.join(out, "LICENSE"),
               "BigNoteBox_Spell_frFR: French word list for BigNoteBox's spellchecker.\n"
               "frFR.lua is every word form of the French Hunspell dictionary \"Classique\"\n"
               "(Dictionnaires orthographiques francais, Olivier R., https://grammalecte.net/),\n"
               "expanded from fr.dic / fr.aff. It is covered by the Mozilla Public License 2.0:\n"
               "https://www.mozilla.org/MPL/2.0/ . The dictionary's own notice follows.\n\n" + readme)


DE_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/de/"
DE_FILES = ("de_DE_frami.aff", "de_DE_frami.dic", "README_de_DE_frami.txt",
            "README_extension_owner.txt", "COPYING_GPLv2", "COPYING_GPLv3")


def cap_first(w):
    """The first letter in capitals, as the Lua side does (ss for a first
    sharp s would change the length: left as it is)."""
    u = w[:1].upper()
    return (u if len(u) == 1 else w[:1]) + w[1:]


def build_de():
    """German: igerman98 / frami (LibreOffice de_DE_frami,
    GPL v2 or v3). Every word form, plus three small lists for compound
    words, used by Features/Spellcheck.lua (Compound):
        begin   forms the dictionary lets start a compound (Arbeits, Drachen)
        middle  forms it lets sit inside one (schuppen)
        endx    forms it lets end one that are not a word with its first
                letter lowered (losigkeit, nahme): any noun can end one
    Every listed compound stays in `words`, so the strict setting (the
    dictionary's rules only) still knows them."""
    import hunspell_expand
    src = os.path.join(SRC, "de")
    if "--fetch" in sys.argv or not os.path.exists(os.path.join(src, "de_DE_frami.dic")):
        os.makedirs(src, exist_ok=True)
        for f in DE_FILES:
            print("fetch", DE_URL + f)
            with urllib.request.urlopen(DE_URL + f, timeout=120) as r:
                data = r.read()
            with open(os.path.join(src, f), "wb") as fh:
                fh.write(data)
    x = hunspell_expand.expand_compound(os.path.join(src, "de_DE_frami.dic"),
                                        os.path.join(src, "de_DE_frami.aff"))
    words = pieces(x["words"])
    def part(w):     # what the checker's words can be: no digit, dot or hyphen
        return not any(ch.isdigit() or ch in ".-" for ch in w)
    begin = {w for w in x["begin"] if part(w)}
    middle = {w for w in x["middle"] if part(w)}
    endx = {w for w in x["end"] if part(w) and cap_first(w) not in words}
    print("German: %d words, compound parts: %d begin, %d middle, %d end not from a noun"
          % (len(words), len(begin), len(middle), len(endx)))
    out = os.path.join(PACK, "BigNoteBox_Spell_deDE")
    os.makedirs(out, exist_ok=True)
    head = ("-- BigNoteBox_Spell_deDE deDE.lua -- generated by BNB's _work/tools/dict-build.py, do not edit\n"
            "--\n"
            "-- German, %d words (igerman98 by Bjoern Jacke, frami additions by Franz Michael Baumann,\n"
            "-- GNU GPL version 2 or 3, see LICENSE). begin / middle / endx: parts of compound words.\n"
            "-- Buckets: byte length * 256 + first byte -> same-length words, joined. Raw UTF-8.\n"
            "local words = {\n" % len(words))
    body = (head.encode("utf-8") + lua_table_raw(words)
            + b"\n}\nlocal begin = {\n" + lua_table_raw(begin)
            + b"\n}\nlocal middle = {\n" + lua_table_raw(middle)
            + b"\n}\nlocal endx = {\n" + lua_table_raw(endx) + b"\n}\n"
            + ("if BigNoteBox and BigNoteBox.ReceiveSpellData then\n"
               "    BigNoteBox.ReceiveSpellData(\"deDE\", { words = words, count = %d,\n"
               "        begin = begin, middle = middle, endx = endx, cmin = %d })\n"
               "end\n" % (len(words), x["cmin"])).encode("utf-8"))
    path = os.path.join(out, "deDE.lua")
    with open(path, "wb") as f:
        f.write(body)
    print("wrote", path, os.path.getsize(path), "bytes")
    write_text(os.path.join(out, "BigNoteBox_Spell_deDE.toc"), TOC.format(name="German", code="deDE"))
    def rd(name):
        return open(os.path.join(src, name), encoding="latin-1").read().replace("\r\n", "\n")
    write_text(os.path.join(out, "LICENSE"),
               "BigNoteBox_Spell_deDE: German word list for BigNoteBox's spellchecker.\n"
               "deDE.lua is every word form of the German Hunspell dictionary de_DE_frami\n"
               "(igerman98 by Bjoern Jacke, https://www.j3e.de/ispell/igerman98/ , with the\n"
               "frami additions by Franz Michael Baumann), expanded from de_DE_frami.dic /\n"
               "de_DE_frami.aff as shipped by LibreOffice:\n"
               "https://github.com/LibreOffice/dictionaries/tree/master/de\n"
               "It is covered by the GNU General Public License, version 2 or (at your\n"
               "option) version 3; the full text of version 3 is in COPYING. The\n"
               "dictionary's own notices follow.\n\n"
               + rd("README_de_DE_frami.txt") + "\n" + rd("README_extension_owner.txt"))
    write_text(os.path.join(out, "COPYING"), rd("COPYING_GPLv3"))


if __name__ == "__main__":
    if "--game-words" in sys.argv:
        write_game_words()
    elif "--lang" in sys.argv:
        lang = sys.argv[sys.argv.index("--lang") + 1]
        if lang == "fr":
            build_fr()
        elif lang == "de":
            build_de()
        else:
            sys.exit("unknown --lang " + lang)
    else:
        main()
