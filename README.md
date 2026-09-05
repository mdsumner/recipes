# recipes

A growing collection of recipes in short form: one markdown file per
recipe, with the ingredient list, the method as numbered steps, and the
source link. No narrative, no photos.

## Adding a recipe

Open an issue with the **Add a recipe** template and paste the URL.
Within a minute or so the harvester commits `recipes/<slug>.md` (and the
structured data behind it in `data/<slug>.json`), updates the index below,
comments on the issue with a link, and closes it.

Only repository owners, members and collaborators trigger the harvester;
issues from anyone else just sit there until someone with access re-files them.

If the page has no machine-readable recipe (the issue gets labelled
`needs-manual`), write the file by hand following the layout of any
existing one, or just fix up whatever the harvester produced -- the files
are meant to be edited.

## How it works

Nearly every recipe site embeds a `schema.org/Recipe` block as JSON-LD
(WP Recipe Maker and the other WordPress plugins, NYT Cooking, BBC Good
Food, Serious Eats, ...). The harvester fetches the page, reads that block,
normalises it (ISO durations to minutes, HTML stripped, typographic
characters and vulgar fractions mapped to ASCII, sectioned instructions
flattened) and renders a fixed markdown template. It is deterministic and
does not call any model. Recipe notes, which the schema does not carry, are
picked up from the common WordPress plugin markup when present.

Locally:

    pip install -r requirements.txt
    python -m harvest https://example.com/some-recipe/
    python -m harvest --reindex          # rebuild the index only
    python -m pytest                     # tests

Layout:

    recipes/<slug>.md      short-form recipe, YAML front matter for metadata
    data/<slug>.json       the normalised structured recipe (search, scaling, exports later)
    harvest/               the Python package
    tests/                 fixture-based tests, no network
    .github/               issue form, harvest workflow, test workflow

Front matter fields: `title`, `slug`, `source`, `site`, `harvested`,
`extraction` (`jsonld` or `manual`), `yield`, `prep_min`, `cook_min`,
`total_min`, `tags`. Categories, cuisine, keywords and diets from the source
all land in `tags`; there are deliberately no category directories, a
recipe is usually several things at once.

## Website

`site/build.py` renders `recipes/*.md` into a static site in `_site/`:
a searchable, tag-filterable index and one page per recipe with tick-off
ingredients, tap-to-dim steps, a keep-screen-on button for the kitchen,
dark mode and a print stylesheet. No framework; one CSS block and a few
lines of script inlined into each page.

    pip install -r site/requirements.txt
    python site/build.py            # then open _site/index.html

The `Build and deploy site` workflow publishes it to GitHub Pages on every
push to `main` that touches `recipes/` or `site/`, and after every
harvester run. One-time setup: repository Settings > Pages > Source:
**GitHub Actions**. GitHub Pages on a free account requires the repo to be
public; see the note below before flipping it.

## A note on sources

Every file links to where it came from. Ingredient lists are facts, but
the method text is the author's writing; the harvester copies it in
short form as a starting point for a personal collection. Keep the repo
private, or rewrite the steps in your own words, before sharing it more
widely.

## Index

<!-- recipes:start -->
| Recipe | Yield | Time | Tags | Source |
|---|---|---|---|---|
| [Gluten-Free Vegan Focaccia](recipes/gluten-free-vegan-focaccia.md) | 1 loaf | 2h25 | bread, gluten free, vegan, italian | [The Vegan Harvest](https://theveganharvest.com/2021/04/15/delicious-gluten-free-vegan-focaccia-bread/) |

1 recipe.
<!-- recipes:end -->
