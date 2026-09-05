"""Render a normalised recipe dict to short-form markdown with YAML front matter."""

import datetime as _dt

import yaml

from .text import fmt_minutes, to_ascii


def _times_line(rec):
    parts = []
    if rec.get("prep_min"):
        parts.append("Prep %s" % fmt_minutes(rec["prep_min"]))
    if rec.get("cook_min"):
        parts.append("Cook %s" % fmt_minutes(rec["cook_min"]))
    if rec.get("total_min"):
        parts.append("Total %s" % fmt_minutes(rec["total_min"]))
    return " | ".join(parts)


def front_matter(rec, slug, harvested=None):
    fm = {
        "title": rec["name"],
        "slug": slug,
        "source": rec["source_url"],
        "site": rec.get("site"),
        "harvested": (harvested or _dt.date.today()).isoformat(),
        "extraction": rec.get("extraction", "jsonld"),
        "yield": rec.get("yield"),
        "prep_min": rec.get("prep_min"),
        "cook_min": rec.get("cook_min"),
        "total_min": rec.get("total_min"),
        "tags": rec.get("tags") or [],
    }
    fm = {k: v for k, v in fm.items() if v not in (None, "", [])}
    text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=False, width=1000)
    return "---\n%s---\n" % text


def render(rec, slug, harvested=None):
    out = [front_matter(rec, slug, harvested)]
    out.append("\n# %s\n" % rec["name"])
    out.append("\nSource: %s\n" % rec["source_url"])
    if rec.get("yield"):
        out.append("\nYield: %s" % rec["yield"])
    times = _times_line(rec)
    if times:
        out.append("\n%s" % times)
    out.append("\n")

    if rec.get("ingredients"):
        out.append("\n## Ingredients\n\n")
        out.append("\n".join("- %s" % i for i in rec["ingredients"]))
        out.append("\n")

    if rec.get("steps"):
        out.append("\n## Method\n\n")
        out.append("\n".join("%d. %s" % (n, s) for n, s in enumerate(rec["steps"], 1)))
        out.append("\n")

    if rec.get("notes"):
        out.append("\n## Notes\n\n")
        out.append("\n".join("- %s" % n for n in rec["notes"]))
        out.append("\n")

    return to_ascii_doc("".join(out))


def to_ascii_doc(text):
    """Defensive final pass: the whole document must be ASCII, line by line."""
    return "\n".join(to_ascii(line) if any(ord(c) > 127 for c in line) else line
                     for line in text.split("\n"))
