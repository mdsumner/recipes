"""Regenerate the recipe index block in README.md from the recipes/ folder."""

import re
from pathlib import Path

import yaml

START = "<!-- recipes:start -->"
END = "<!-- recipes:end -->"
_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def read_front_matter(path):
    text = Path(path).read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        # Fall back to the first H1 for hand-written files without front matter.
        h1 = re.search(r"^# (.+)$", text, re.M)
        return {"title": h1.group(1).strip() if h1 else path.stem, "tags": []}
    fm = yaml.safe_load(m.group(1)) or {}
    fm.setdefault("title", path.stem)
    fm.setdefault("tags", [])
    return fm


def build_index(recipes_dir):
    rows = []
    for path in sorted(Path(recipes_dir).glob("*.md")):
        fm = read_front_matter(path)
        rows.append((fm["title"], path, fm))
    rows.sort(key=lambda r: r[0].lower())
    lines = ["| Recipe | Yield | Time | Tags | Source |", "|---|---|---|---|---|"]
    for title, path, fm in rows:
        total = fm.get("total_min")
        time = _fmt(total) if total else ""
        tags = ", ".join(fm.get("tags") or [])
        src = fm.get("site") or ""
        if fm.get("source"):
            src = "[%s](%s)" % (src or "link", fm["source"])
        lines.append("| [%s](%s) | %s | %s | %s | %s |" % (
            title, path.as_posix(), fm.get("yield") or "", time, tags, src))
    lines.append("")
    lines.append("%d recipe%s." % (len(rows), "" if len(rows) == 1 else "s"))
    return "\n".join(lines)


def _fmt(mins):
    h, m = divmod(int(mins), 60)
    if h and m:
        return "%dh%02d" % (h, m)
    if h:
        return "%dh" % h
    return "%dm" % m


def update_readme(readme_path, recipes_dir):
    readme = Path(readme_path)
    text = readme.read_text(encoding="utf-8") if readme.exists() else "# recipes\n\n"
    block = "%s\n%s\n%s" % (START, build_index(recipes_dir), END)
    if START in text and END in text:
        pre = text[: text.index(START)]
        post = text[text.index(END) + len(END):]
        text = pre + block + post
    else:
        text = text.rstrip("\n") + "\n\n## Index\n\n" + block + "\n"
    readme.write_text(text, encoding="utf-8")
    return text
