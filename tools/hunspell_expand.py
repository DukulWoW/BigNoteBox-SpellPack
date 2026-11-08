"""Expands a Hunspell .dic / .aff pair into every word form.

Used by dict-build.py for the languages that come as Hunspell files (French
first). Our own code, written for what those files use:

- FLAG long (two-character flags) or the default one-character flags
- SFX and PFX groups, the cross-product flag, strip / add / condition,
  continuation flags on an affix (a suffix after a suffix, a suffix after a
  prefix), FULLSTRIP
- NEEDAFFIX (the stem alone is not a word), FORBIDDENWORD (left out)
- prefixes whose text ends in an apostrophe are elisions (l', d', qu'): left
  out, the spellchecker splits them off the word instead
- ICONV ' for the typographic apostrophe (we write the plain one)
- SET ISO8859-1 (the German files) or UTF-8, read from the .aff
- compounding by flags (German): expand_compound() also returns
  the forms that may start / sit inside / end a compound word
  (COMPOUNDBEGIN / COMPOUNDMIDDLE / COMPOUNDEND, ONLYINCOMPOUND,
  COMPOUNDPERMITFLAG: an affixed form inside a compound only when its affix
  allows it, as Hunspell does)

Not handled (not used by the lists we build): COMPOUNDRULE, CIRCUMFIX pairs
(affixes with that flag are left out), morphological fields.
"""
import re

NL, CRLF = chr(10), chr(13) + chr(10)
TYPO_APOS = chr(0x2019)


def _encoding(path):
    """The .aff's SET line: ISO8859-1 -> latin-1, anything else UTF-8."""
    with open(path, "rb") as f:
        for raw in f.read().split(NL.encode()):
            parts = raw.split()
            if parts and parts[0] == b"SET" and len(parts) > 1:
                return "latin-1" if parts[1].upper() in (b"ISO8859-1", b"ISO-8859-1") else "utf-8"
    return "utf-8"


def _read_lines(path, enc):
    return open(path, encoding=enc).read().replace(CRLF, NL).split(NL)


def _flags(s, long_flags):
    if not s:
        return []
    if long_flags:
        return [s[i:i + 2] for i in range(0, len(s) - 1, 2)]
    return list(s)


def _cond(cond, suffix):
    if cond in (".", ""):
        return None
    # Hunspell conditions are letters, "." and [..] / [^..] classes: the same in a regex
    return re.compile(("(?:%s)$" if suffix else "^(?:%s)") % cond)


class Aff:
    def __init__(self, path):
        self.long = False
        self.need = None
        self.forbid = None
        self.circum = None
        self.cbegin = self.cmiddle = self.cend = self.only = self.permit = None
        self.cmin = 3
        self.sfx = {}   # flag -> (cross, [(strip, add, contflags, regex)])
        self.pfx = {}
        self.enc = _encoding(path)
        lines = _read_lines(path, self.enc)
        i = 0
        while i < len(lines):
            parts = lines[i].split()
            i += 1
            if not parts or parts[0].startswith("#"):
                continue
            key = parts[0]
            if key == "FLAG" and len(parts) > 1 and parts[1] == "long":
                self.long = True
            elif key == "NEEDAFFIX":
                self.need = parts[1]
            elif key == "FORBIDDENWORD":
                self.forbid = parts[1]
            elif key == "CIRCUMFIX":
                self.circum = parts[1]
            elif key == "COMPOUNDBEGIN":
                self.cbegin = parts[1]
            elif key == "COMPOUNDMIDDLE":
                self.cmiddle = parts[1]
            elif key == "COMPOUNDEND":
                self.cend = parts[1]
            elif key == "ONLYINCOMPOUND":
                self.only = parts[1]
            elif key == "COMPOUNDPERMITFLAG":
                self.permit = parts[1]
            elif key == "COMPOUNDMIN":
                self.cmin = int(parts[1])
            elif key in ("SFX", "PFX") and len(parts) == 4 and parts[2] in ("Y", "N"):
                flag, cross, n = parts[1], parts[2] == "Y", int(parts[3])
                entries = []
                for _ in range(n):
                    p = lines[i].split()
                    i += 1
                    strip = "" if p[2] == "0" else p[2]
                    add, _, cont = p[3].partition("/")
                    add = "" if add == "0" else add
                    cond = p[4] if len(p) > 4 else "."
                    entries.append((strip, add, _flags(cont, self.long), _cond(cond, key == "SFX")))
                (self.sfx if key == "SFX" else self.pfx)[flag] = (cross, entries)

    def _apply_sfx(self, word, flag):
        out = []
        cross, entries = self.sfx[flag]
        for strip, add, cont, rx in entries:
            if self.circum in cont:
                continue
            if strip and not word.endswith(strip):
                continue
            if rx and not rx.search(word):
                continue
            base = word[:len(word) - len(strip)] if strip else word
            out.append((base + add, cont, cross))
        return out

    def _apply_pfx(self, word, flag):
        out = []
        cross, entries = self.pfx[flag]
        for strip, add, cont, rx in entries:
            if "'" in add or TYPO_APOS in add:
                continue                       # an elision (l', l'A): split off when checking
            if self.circum in cont:
                continue
            if strip and not word.startswith(strip):
                continue
            if rx and not rx.search(word):
                continue
            out.append((add + word[len(strip):], cont, cross))
        return out

    def forms(self, stem, flagstr):
        flags = _flags(flagstr, self.long)
        if self.forbid and self.forbid in flags:
            return set()
        out = set()
        if not (self.need and self.need in flags):
            out.add(stem)
        suffixed = []
        for f in flags:
            if f not in self.sfx:
                continue
            for w, cont, cross in self._apply_sfx(stem, f):
                if not (self.need and self.need in cont):
                    out.add(w)
                suffixed.append((w, cross))
                for c in cont:                 # a second suffix
                    if c in self.sfx:
                        for w2, _, _ in self._apply_sfx(w, c):
                            out.add(w2)
        for f in flags:
            if f not in self.pfx:
                continue
            pcross = self.pfx[f][0]
            for w, cont, _ in self._apply_pfx(stem, f):
                if not (self.need and self.need in cont):
                    out.add(w)
                for c in cont:                 # a suffix carried by the prefix
                    if c in self.sfx:
                        for w2, _, _ in self._apply_sfx(w, c):
                            out.add(w2)
            if pcross:
                for sw, scross in suffixed:
                    if scross:
                        for w, _, _ in self._apply_pfx(sw, f):
                            out.add(w)
        return out

    def flagged_forms(self, stem, flagstr):
        """Every form with what it may be: -> [(form, flags, suffixed, prefixed,
        affix flags)]. flags = the stem's flags plus its affixes' continuation
        flags (Hunspell reads a compound flag from either)."""
        R = set(_flags(flagstr, self.long))
        if self.forbid and self.forbid in R:
            return []
        out = []
        if not (self.need and self.need in R):
            out.append((stem, R, False, False, set()))
        suffixed = []
        for f in R:
            if f not in self.sfx:
                continue
            for w, cont, cross in self._apply_sfx(stem, f):
                C = set(cont)
                if not (self.need and self.need in C):
                    out.append((w, R | C, True, False, C))
                suffixed.append((w, cross, C))
                for c in cont:                 # a second suffix
                    if c in self.sfx:
                        for w2, cont2, _ in self._apply_sfx(w, c):
                            C2 = C | set(cont2)
                            out.append((w2, R | C2, True, False, C2))
        for f in R:
            if f not in self.pfx:
                continue
            pcross = self.pfx[f][0]
            for w, cont, _ in self._apply_pfx(stem, f):
                C = set(cont)
                if not (self.need and self.need in C):
                    out.append((w, R | C, False, True, C))
                for c in cont:                 # a suffix carried by the prefix
                    if c in self.sfx:
                        for w2, cont2, _ in self._apply_sfx(w, c):
                            C2 = C | set(cont2)
                            out.append((w2, R | C2, True, True, C2))
            if pcross:
                for sw, scross, SC in suffixed:
                    if scross:
                        for w, cont, _ in self._apply_pfx(sw, f):
                            C2 = SC | set(cont)
                            out.append((w, R | C2, True, True, C2))
        return out


def _stems(dic_path, enc):
    for line in _read_lines(dic_path, enc)[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tok = line.split()[0]
        stem, _, fl = tok.partition("/")
        yield stem, fl


def expand_compound(dic_path, aff_path):
    """-> dict: words (forms that stand alone), begin / middle / end (forms
    that may start / sit inside / end a compound), cmin. A form with a hyphen
    at its start or end (-auto, Arbeits-, haus-) is left out: the hyphen
    halves would bring in lower-case nouns (haus-) and bare linking forms;
    the checker takes a compound start right before a "-" in the text
    instead ("Arbeits- und Sozialminister"). Typographic apostrophes become
    plain ones."""
    aff = Aff(aff_path)
    words, begin, middle, end = set(), set(), set(), set()
    for stem, fl in _stems(dic_path, aff.enc):
        for w, F, sfx, pfx, C in aff.flagged_forms(stem, fl):
            if not w or w.startswith("-") or w.endswith("-"):
                continue
            w = w.replace(TYPO_APOS, "'")
            if not (aff.only and aff.only in F):
                words.add(w)
            permit = aff.permit is not None and aff.permit in C
            # Hunspell: a suffix inside a compound (not at its end) and a
            # prefix not at its start need COMPOUNDPERMITFLAG on the affix
            if aff.cbegin and aff.cbegin in F and (not sfx or permit):
                begin.add(w)
            if aff.cmiddle and aff.cmiddle in F and ((not sfx and not pfx) or permit):
                middle.add(w)
            if aff.cend and aff.cend in F and (not pfx or permit):
                end.add(w)
    return {"words": words, "begin": begin, "middle": middle, "end": end, "cmin": aff.cmin}


def expand(dic_path, aff_path):
    aff = Aff(aff_path)
    words = set()
    for stem, fl in _stems(dic_path, aff.enc):
        words |= aff.forms(stem, fl)
    return {w.replace(TYPO_APOS, "'") for w in words if w}
