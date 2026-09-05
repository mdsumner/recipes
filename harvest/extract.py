"""Extract a normalised recipe dict from an HTML page.

Primary source is schema.org/Recipe JSON-LD, which nearly every recipe
site emits (WP Recipe Maker, Tasty Recipes, NYT Cooking, BBC Good Food,
Serious Eats, ...). A small WordPress-specific enrichment step picks up
recipe notes, which the schema does not carry.

The normalised dict is the contract for the renderer:

    {
      "name": str,
      "source_url": str,
      "site": str | None,
      "description": str | None,
      "yield": str | None,
      "prep_min": int | None,
      "cook_min": int | None,
      "total_min": int | None,
      "ingredients": [str],
      "steps": [str],              # flat list, section headings inlined as "Section: ..."
      "notes": [str],
      "tags": [str],
      "extraction": "jsonld",
    }
"""

import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .text import as_list, clean, duration_minutes, strip_html


class NoRecipeFound(Exception):
    pass


def _types(node):
    return [str(t) for t in as_list(node.get("@type"))]


def _walk(obj):
    """Yield every dict reachable inside a JSON-LD document."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def find_recipe_nodes(soup):
    """All JSON-LD nodes with @type Recipe, in document order."""
    found = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            # Some sites emit trailing commas or comments; try a lenient pass.
            try:
                doc = json.loads(raw.strip().rstrip(";"))
            except json.JSONDecodeError:
                continue
        for node in _walk(doc):
            if "Recipe" in _types(node):
                found.append(node)
    return found


def _text_of(item):
    """Instruction items are strings, HowToStep dicts, or {'text': ...}."""
    if isinstance(item, str):
        return clean(item)
    if isinstance(item, dict):
        return clean(item.get("text") or item.get("name") or "")
    return ""


def flatten_instructions(value):
    """recipeInstructions -> flat list of step strings.

    Handles: a single string (possibly with newlines), a list of strings,
    a list of HowToStep, a list of HowToSection each holding steps.
    """
    steps = []
    for item in as_list(value):
        if isinstance(item, dict) and "HowToSection" in _types(item):
            heading = clean(item.get("name") or "")
            inner = item.get("itemListElement") or item.get("steps") or []
            sub = flatten_instructions(inner)
            if heading and sub:
                sub[0] = "%s: %s" % (heading, sub[0])
            steps.extend(sub)
        elif isinstance(item, str) and "\n" in item:
            steps.extend(s for s in (clean(x) for x in item.split("\n")) if s)
        else:
            t = _text_of(item)
            if t:
                steps.append(t)
    return steps


def _yield(value):
    vals = [clean(v) for v in as_list(value)]
    vals = [v for v in vals if v]
    if not vals:
        return None
    # WPRM emits ["1", "1 loaf"]; prefer the most descriptive.
    return max(vals, key=len)


def _tags(node):
    raw = []
    raw += as_list(node.get("recipeCategory"))
    raw += as_list(node.get("recipeCuisine"))
    for kw in as_list(node.get("keywords")):
        raw += [k for k in str(kw).split(",")]
    for diet in as_list(node.get("suitableForDiet")):
        d = str(diet).rsplit("/", 1)[-1]
        d = d.replace("Diet", "")
        raw.append(d)
    seen, out = set(), []
    for t in raw:
        t = clean(t).lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _site(node, url):
    pub = node.get("publisher")
    if isinstance(pub, dict) and pub.get("name"):
        return clean(pub["name"])
    host = urlparse(url).netloc
    return host[4:] if host.startswith("www.") else host


def wordpress_notes(soup):
    """Recipe notes from common WordPress recipe plugins (not in JSON-LD)."""
    selectors = [
        ".wprm-recipe-notes",
        ".tasty-recipes-notes-body",
        ".tasty-recipes-notes",
        ".mv-create-notes",
        ".recipe-notes",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            parts = []
            for li in el.find_all(["li", "p"]):
                t = clean(li.get_text(" ", strip=True))
                if t:
                    parts.append(t)
            if not parts:
                t = clean(el.get_text(" ", strip=True))
                if t:
                    parts = [t]
            if parts:
                return parts
    return []


def extract(html, url):
    soup = BeautifulSoup(html, "html.parser")
    nodes = find_recipe_nodes(soup)
    if not nodes:
        raise NoRecipeFound("no schema.org/Recipe JSON-LD found at %s" % url)
    node = nodes[0]

    rec = {
        "name": clean(node.get("name") or node.get("headline") or ""),
        "source_url": url,
        "site": _site(node, url),
        "description": clean(node.get("description")) or None,
        "yield": _yield(node.get("recipeYield")),
        "prep_min": duration_minutes(node.get("prepTime")),
        "cook_min": duration_minutes(node.get("cookTime")),
        "total_min": duration_minutes(node.get("totalTime")),
        "ingredients": [clean(i) for i in as_list(node.get("recipeIngredient")) if clean(i)],
        "steps": flatten_instructions(node.get("recipeInstructions")),
        "notes": wordpress_notes(soup),
        "tags": _tags(node),
        "extraction": "jsonld",
    }
    if not rec["name"]:
        title = soup.find("title")
        rec["name"] = clean(title.get_text()) if title else strip_html(url)
    if not rec["ingredients"] and not rec["steps"]:
        raise NoRecipeFound("Recipe node had no ingredients or instructions at %s" % url)
    return rec
