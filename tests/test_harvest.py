import datetime
import json
from pathlib import Path

import pytest

from harvest.extract import NoRecipeFound, extract, flatten_instructions
from harvest.index import build_index
from harvest.render import render
from harvest.text import duration_minutes, fmt_minutes, slugify, to_ascii

FIX = Path(__file__).parent / "fixtures"
URL = "https://example.test/flatbread/"


@pytest.fixture
def rec():
    return extract((FIX / "wprm-flatbread.html").read_text(encoding="utf-8"), URL)


def test_basic_fields(rec):
    assert rec["name"] == "Test Kitchen Flatbread"
    assert rec["site"] == "Example Blog"
    assert rec["yield"] == "4 flatbreads"
    assert (rec["prep_min"], rec["cook_min"], rec["total_min"]) == (10, 12, 82)
    assert rec["extraction"] == "jsonld"


def test_ingredients_ascii(rec):
    assert rec["ingredients"][1] == "1 1/2 tsp instant yeast"
    assert rec["ingredients"][2] == "1/2 tsp salt"
    for line in rec["ingredients"]:
        assert line.isascii()


def test_sections_flattened_and_entities(rec):
    assert rec["steps"][0] == "Dough: Whisk flour, yeast & salt in a bowl."
    assert rec["steps"][2].startswith("Cook: Rest 1 hour")
    assert "220 C" in rec["steps"][3]
    assert "2-3 minutes" in rec["steps"][3]
    # <br> inside a single step becomes a space, not a new step
    assert rec["steps"][4] == "Brush with remaining oil and sprinkle flaky salt. Serve warm."
    assert len(rec["steps"]) == 5


def test_notes_and_tags(rec):
    assert rec["notes"] == [
        "Weigh the flour - don't scoop.",
        "Rest time depends on room temperature.",
    ]
    assert rec["tags"] == ["bread", "side", "middle eastern", "flatbread", "quick",
                           "gluten free", "vegan"]


def test_render_is_ascii_and_has_front_matter(rec):
    md = render(rec, "test-kitchen-flatbread", harvested=datetime.date(2026, 9, 6))
    assert md.isascii()
    assert md.startswith("---\ntitle: Test Kitchen Flatbread\nslug: test-kitchen-flatbread\n")
    assert "harvested: '2026-09-06'" in md or "harvested: 2026-09-06" in md
    assert "\n# Test Kitchen Flatbread\n" in md
    assert "Source: %s" % URL in md
    assert "Prep 10 min | Cook 12 min | Total 1 h 22 min" in md
    assert "\n## Ingredients\n\n- 300 g plain flour\n" in md
    assert "\n## Method\n\n1. Dough: Whisk" in md
    assert "\n## Notes\n\n- Weigh the flour" in md


def test_json_roundtrip(rec):
    assert json.loads(json.dumps(rec)) == rec


def test_no_recipe():
    with pytest.raises(NoRecipeFound):
        extract("<html><body><p>nothing</p></body></html>", URL)


def test_string_instructions_split_on_newlines():
    assert flatten_instructions("Step one.\nStep two.\n") == ["Step one.", "Step two."]
    assert flatten_instructions(["a", {"@type": "HowToStep", "text": "b"}]) == ["a", "b"]


@pytest.mark.parametrize("iso,mins", [
    ("PT15M", 15), ("PT1H30M", 90), ("PT2H", 120), ("P1DT1H", 1500),
    ("PT40S", 1), ("", None), (None, None), ("garbage", None),
])
def test_durations(iso, mins):
    assert duration_minutes(iso) == mins


def test_fmt_minutes():
    assert fmt_minutes(90) == "1 h 30 min"
    assert fmt_minutes(120) == "2 h"
    assert fmt_minutes(40) == "40 min"


def test_slug_and_ascii():
    assert slugify("Delicious Gluten-Free Vegan Focaccia Bread!") == \
        "delicious-gluten-free-vegan-focaccia-bread"
    assert to_ascii("Cr\u00e8me br\u00fbl\u00e9e \u2014 400\u00b0F") == 'Creme brulee - 400 F'


def test_index(tmp_path, rec):
    d = tmp_path / "recipes"
    d.mkdir()
    (d / "b.md").write_text(render(rec, "b"), encoding="utf-8")
    (d / "a.md").write_text("# Alpha Hand Written\n\nno front matter\n", encoding="utf-8")
    idx = build_index(d)
    assert "2 recipes." in idx
    assert idx.index("Alpha Hand Written") < idx.index("Test Kitchen Flatbread")


def test_site_build(tmp_path, rec):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sitebuild", Path(__file__).parent.parent / "site" / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "b.md").write_text(render(rec, "b"), encoding="utf-8")
    n = mod.build(tmp_path, tmp_path / "_site", "./")
    assert n == 1
    idx = (tmp_path / "_site" / "index.html").read_text(encoding="ascii")
    page = (tmp_path / "_site" / "r" / "b.html").read_text(encoding="ascii")
    assert "Test Kitchen Flatbread" in idx and 'href="./r/b.html"' in idx
    assert "<h2>Ingredients</h2>" in page and "1 1/2 tsp instant yeast" in page
    assert page.count("Yield:") == 1
