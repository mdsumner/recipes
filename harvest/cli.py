"""Command line entry point.

    python -m harvest URL [--slug SLUG] [--force] [--root DIR]
    python -m harvest --reindex [--root DIR]

Writes recipes/<slug>.md and data/<slug>.json, then regenerates the
index block in README.md. Exit codes: 0 ok, 2 no recipe found, 3 exists
(use --force), 1 anything else.
"""

import argparse
import json
import sys
from pathlib import Path

import requests

from .extract import NoRecipeFound, extract
from .fetch import fetch
from .index import update_readme
from .render import render
from .text import slugify


def harvest(url, root, slug=None, force=False):
    root = Path(root)
    html, final_url = fetch(url)
    rec = extract(html, final_url)
    slug = slug or slugify(rec["name"])
    md_path = root / "recipes" / ("%s.md" % slug)
    json_path = root / "data" / ("%s.json" % slug)
    if md_path.exists() and not force:
        raise FileExistsError(str(md_path))
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render(rec, slug), encoding="utf-8")
    json_path.write_text(json.dumps(rec, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    update_readme(root / "README.md", root / "recipes")
    return slug, md_path, rec


def main(argv=None):
    ap = argparse.ArgumentParser(prog="harvest", description=__doc__.split("\n")[0])
    ap.add_argument("url", nargs="?", help="recipe page URL")
    ap.add_argument("--slug", help="override the output file name")
    ap.add_argument("--force", action="store_true", help="overwrite an existing recipe")
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--reindex", action="store_true", help="only regenerate README index")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if args.reindex:
        update_readme(root / "README.md", root / "recipes")
        print("reindexed")
        return 0
    if not args.url:
        ap.error("url is required unless --reindex")

    try:
        slug, md_path, rec = harvest(args.url, root, slug=args.slug, force=args.force)
    except NoRecipeFound as e:
        print("NO_RECIPE: %s" % e, file=sys.stderr)
        return 2
    except FileExistsError as e:
        print("EXISTS: %s (use --force to overwrite)" % e, file=sys.stderr)
        return 3
    except requests.RequestException as e:
        print("FETCH_FAILED: %s" % e, file=sys.stderr)
        return 1
    print("%s\t%s\t%d ingredients\t%d steps" % (
        slug, md_path.as_posix(), len(rec["ingredients"]), len(rec["steps"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
