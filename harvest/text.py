"""Small text utilities: HTML stripping, ASCII normalisation, durations, slugs."""

import html
import re
import unicodedata

# Characters that commonly appear in recipe text and have an obvious ASCII form.
_ASCII_MAP = {
    "\u00bc": "1/4",
    "\u00bd": "1/2",
    "\u00be": "3/4",
    "\u2153": "1/3",
    "\u2154": "2/3",
    "\u215b": "1/8",
    "\u215c": "3/8",
    "\u215d": "5/8",
    "\u215e": "7/8",
    "\u00b0": " deg ",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
    "\u00d7": "x",
    "\u00a0": " ",
    "\u2044": "/",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def strip_html(value):
    """Remove tags and unescape entities from a string."""
    if value is None:
        return ""
    value = _TAG_RE.sub(" ", str(value))
    value = html.unescape(value)
    return _WS_RE.sub(" ", value).strip()


def to_ascii(value):
    """Map common typographic and fraction characters to ASCII, drop the rest."""
    if value is None:
        return ""
    out = []
    for ch in str(value):
        if ch in _ASCII_MAP:
            rep = _ASCII_MAP[ch]
            # "1\u00bd" -> "1 1/2": a vulgar fraction glued to a digit needs a space.
            if "/" in rep and out and out[-1][-1:].isdigit():
                out.append(" ")
            out.append(rep)
        elif ord(ch) < 128:
            out.append(ch)
        else:
            decomposed = unicodedata.normalize("NFKD", ch)
            out.append("".join(c for c in decomposed if ord(c) < 128))
    text = "".join(out)
    text = re.sub(r"\s+deg\s+([CF])\b", r" \1", text)  # "400 deg F" -> "400 F"
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return _WS_RE.sub(" ", text).strip()


def clean(value):
    """strip_html then to_ascii."""
    return to_ascii(strip_html(value))


_DUR_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def duration_minutes(value):
    """ISO 8601 duration (PT1H30M) to integer minutes; None if unparseable."""
    if not value:
        return None
    m = _DUR_RE.match(str(value).strip())
    if not m:
        return None
    d = {k: int(v) for k, v in m.groupdict().items() if v}
    total = d.get("days", 0) * 1440 + d.get("hours", 0) * 60 + d.get("minutes", 0)
    if d.get("seconds", 0) >= 30:
        total += 1
    return total or None


def fmt_minutes(mins):
    """65 -> '1 h 5 min', 40 -> '40 min'."""
    if mins is None:
        return None
    h, m = divmod(int(mins), 60)
    if h and m:
        return "%d h %d min" % (h, m)
    if h:
        return "%d h" % h
    return "%d min" % m


def slugify(value, max_len=80):
    value = to_ascii(value).lower()
    value = _SLUG_RE.sub("-", value).strip("-")
    return value[:max_len].rstrip("-")


def as_list(value):
    """Normalise None / scalar / list to a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]
