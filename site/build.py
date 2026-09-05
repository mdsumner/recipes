"""Build a static site from recipes/*.md into _site/.

    python site/build.py [--root DIR] [--out DIR] [--base-url /recipes/]

Output:
    _site/index.html              searchable, tag-filterable index
    _site/r/<slug>.html           one page per recipe
    _site/recipes.json            the index data (title, slug, tags, ...)

No template engine: one CSS block, one small script, inlined into every
page so the site works offline once a page is open. Everything written
is ASCII.
"""

import argparse
import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path

import markdown
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from harvest.index import read_front_matter  # noqa: E402
from harvest.text import fmt_minutes, to_ascii  # noqa: E402

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)

CSS = (HERE / "style.css").read_text(encoding="utf-8")
JS_INDEX = (HERE / "index.js").read_text(encoding="utf-8")
JS_RECIPE = (HERE / "recipe.js").read_text(encoding="utf-8")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_recipe(path):
    text = path.read_text(encoding="utf-8")
    fm = read_front_matter(path)
    m = _FM_RE.match(text)
    body = text[m.end():] if m else text
    # Drop the H1 and the "Source:" line: both are rendered from metadata.
    body = re.sub(r"^# .*\n", "", body, count=1, flags=re.M)
    body = re.sub(r"^Source: \S+\n", "", body, count=1, flags=re.M)
    # The yield and timing lines are rendered from front matter; drop them
    # from the preamble (everything before the first H2) when present there.
    # A hand-written body line wins over the front matter when it says more.
    head, sep, rest = body.partition("\n## ")
    ym = re.search(r"^Yield:\s*(.+)$", head, flags=re.M)
    tm = re.search(r"^((?:Prep|Cook|Total|Rise|Bake)\b[^\n]*\|[^\n]*)$", head, flags=re.M)
    head = re.sub(r"^Yield:.*\n?", "", head, flags=re.M)
    head = re.sub(r"^(?:Prep|Cook|Total|Rise|Bake)\b[^\n]*\|[^\n]*\n?", "", head, flags=re.M)
    body = head.strip("\n") + ("\n\n" + sep.lstrip("\n") + rest if sep else "")
    yield_text = ym.group(1).strip() if ym else fm.get("yield")
    times_text = tm.group(1).strip() if tm else None
    md = markdown.Markdown(extensions=["sane_lists"])
    return {
        "slug": fm.get("slug") or path.stem,
        "title": fm.get("title") or path.stem,
        "source": fm.get("source"),
        "site": fm.get("site"),
        "yield": yield_text,
        "times": times_text,
        "total_min": fm.get("total_min"),
        "prep_min": fm.get("prep_min"),
        "cook_min": fm.get("cook_min"),
        "tags": [str(t) for t in (fm.get("tags") or [])],
        "harvested": str(fm.get("harvested") or ""),
        "extraction": fm.get("extraction", "manual"),
        "html": md.convert(body),
        "search": to_ascii(re.sub(r"\s+", " ", body)).lower(),
    }


def page(title, body, base, script="", desc=""):
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title>\n"
        "<meta name=\"description\" content=\"%s\">\n"
        "<style>\n%s</style>\n</head>\n<body>\n"
        "<header class=\"top\"><a class=\"brand\" href=\"%sindex.html\">recipes</a>"
        "<a class=\"gh\" href=\"https://github.com/mdsumner/recipes\">source repo</a></header>\n"
        "<main>\n%s\n</main>\n"
        "<footer>Built %s. Every recipe links to where it came from.</footer>\n"
        "%s</body>\n</html>\n"
    ) % (esc(title), esc(desc), CSS, base, body,
         _dt.date.today().isoformat(),
         "<script>\n%s</script>\n" % script if script else "")


def meta_line(r):
    bits = []
    if r["yield"]:
        bits.append("<span>Yield: %s</span>" % esc(r["yield"]))
    if r.get("times"):
        bits.append("<span>%s</span>" % esc(r["times"].replace(" | ", ", ").lower()))
        return "".join(bits)
    parts = []
    if r["prep_min"]:
        parts.append("prep %s" % fmt_minutes(r["prep_min"]))
    if r["cook_min"]:
        parts.append("cook %s" % fmt_minutes(r["cook_min"]))
    if r["total_min"]:
        parts.append("total %s" % fmt_minutes(r["total_min"]))
    if parts:
        bits.append("<span>%s</span>" % esc(", ".join(parts)))
    return "".join(bits)


def tag_links(tags, base):
    return "".join("<a class=\"tag\" href=\"%sindex.html?tag=%s\">%s</a>" % (base, esc(t), esc(t))
                   for t in tags)


def recipe_page(r, base):
    body = [
        "<article class=\"recipe\">",
        "<h1>%s</h1>" % esc(r["title"]),
        "<p class=\"meta\">%s</p>" % meta_line(r),
        "<p class=\"tags\">%s</p>" % tag_links(r["tags"], base),
        "<div class=\"toolbar\"><button id=\"wake\" type=\"button\">Keep screen on</button>"
        "<button id=\"reset\" type=\"button\">Untick all</button></div>",
        r["html"],
        "<p class=\"source\">Source: <a href=\"%s\">%s</a></p>" % (
            esc(r["source"]), esc(r["site"] or r["source"])) if r["source"] else "",
        "</article>",
    ]
    return page(r["title"], "\n".join(body), base, JS_RECIPE, desc=r["title"])


def index_page(recipes, base):
    all_tags = sorted({t for r in recipes for t in r["tags"]})
    cards = []
    for r in recipes:
        cards.append(
            "<li class=\"card\" data-slug=\"%s\" data-tags=\"%s\">"
            "<a href=\"%sr/%s.html\"><h2>%s</h2></a>"
            "<p class=\"meta\">%s</p><p class=\"tags\">%s</p></li>" % (
                esc(r["slug"]), esc(" ".join(r["tags"])), base, esc(r["slug"]),
                esc(r["title"]), meta_line(r), tag_links(r["tags"], base)))
    body = [
        "<h1>Recipes</h1>",
        "<p class=\"lead\">%d recipe%s in short form. Search matches titles, "
        "ingredients and steps.</p>" % (len(recipes), "" if len(recipes) == 1 else "s"),
        "<input id=\"q\" type=\"search\" placeholder=\"Search...\" autocomplete=\"off\">",
        "<p class=\"tagbar\" id=\"tags\"><a class=\"tag on\" data-tag=\"\" href=\"#\">all</a>%s</p>" % "".join(
            "<a class=\"tag\" data-tag=\"%s\" href=\"#\">%s</a>" % (esc(t), esc(t)) for t in all_tags),
        "<ul class=\"cards\" id=\"cards\">%s</ul>" % "".join(cards),
        "<p id=\"none\" class=\"none\" hidden>Nothing matches.</p>",
    ]
    return page("Recipes", "\n".join(body), base, JS_INDEX, desc="Recipe collection")


def build(root, out, base):
    root, out = Path(root), Path(out)
    recipes = [load_recipe(p) for p in sorted((root / "recipes").glob("*.md"))]
    recipes.sort(key=lambda r: r["title"].lower())
    (out / "r").mkdir(parents=True, exist_ok=True)
    for r in recipes:
        (out / "r" / ("%s.html" % r["slug"])).write_text(recipe_page(r, "../"), encoding="ascii",
                                                          errors="xmlcharrefreplace")
    (out / "index.html").write_text(index_page(recipes, "./"), encoding="ascii",
                                    errors="xmlcharrefreplace")
    data = [{k: r[k] for k in ("slug", "title", "tags", "yield", "total_min", "site", "source", "search")}
            for r in recipes]
    (out / "recipes.json").write_text(json.dumps(data, ensure_ascii=True), encoding="ascii")
    (out / ".nojekyll").write_text("")
    return len(recipes)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--out", default=str(HERE.parent / "_site"))
    ap.add_argument("--base-url", default="./", help="unused for now; links are relative")
    a = ap.parse_args(argv)
    n = build(a.root, a.out, a.base_url)
    print("built %d recipes into %s" % (n, a.out))


if __name__ == "__main__":
    main()
