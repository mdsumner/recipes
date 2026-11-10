import pytest

from harvest.flow import FlowError, ingredients_from_markdown, layout, parse, to_html

BROWNIES = {
    "before": ["Butter and flour an 8x8-in pan", "Preheat oven"],
    "steps": [
        {"melt": [1]},
        {"mix": ["s1", 2, 3, 4]},
        {"mix": ["s2", 5]},
        {"fold in": ["s3", 6, 7, 8, 9]},
        {"bake": ["s4"]},
    ],
}


def cell(cells, kind, value=None, row=None):
    return [c for c in cells if c["kind"] == kind
            and (value is None or c["value"] == value)
            and (row is None or c["row"] == row)]


def test_brownie_layout_matches_card():
    _, steps, _ = parse(BROWNIES, 9)
    rows, ncols, cells = layout(steps)
    assert rows == list(range(9))
    assert ncols == 6  # ingredient column + 5 operation columns
    ops = {c["value"]: (c["row"], c["col"], c["rowspan"], c["colspan"]) for c in cell(cells, "op")}
    assert ops == {0: (0, 1, 1, 1), 1: (0, 2, 4, 1), 2: (0, 3, 5, 1),
                   3: (0, 4, 9, 1), 4: (0, 5, 9, 1)}
    gaps = sorted((c["row"], c["col"], c["rowspan"], c["colspan"]) for c in cell(cells, "gap"))
    # sugar/vanilla/espresso share one blank; eggs spans two columns;
    # the four dry ingredients share one blank three columns wide.
    assert gaps == [(1, 1, 3, 1), (4, 1, 1, 2), (5, 1, 4, 3)]


def test_short_branch_op_stretches_to_parent():
    flow = {"steps": [{"whisk": [1]}, {"melt": [2]}, {"mix": ["s2", 3]},
                      {"fold": ["s3", "s1"]}]}
    _, steps, _ = parse(flow, 3)
    rows, ncols, cells = layout(steps)
    whisk = cell(cells, "op", 0)[0]
    assert (whisk["col"], whisk["colspan"]) == (1, 2)
    assert rows == [1, 2, 0]


def test_every_row_fills_the_width():
    _, steps, _ = parse(BROWNIES, 9)
    rows, ncols, cells = layout(steps)
    cover = {}
    for c in cells:
        for r in range(c["row"], c["row"] + c["rowspan"]):
            for k in range(c["col"], c["col"] + c["colspan"]):
                assert (r, k) not in cover
                cover[(r, k)] = c
    assert len(cover) == len(rows) * ncols


@pytest.mark.parametrize("flow,msg", [
    ({"steps": [{"mix": [1, 1]}]}, "used by"),
    ({"steps": [{"mix": [1]}, {"mix": [2]}]}, "not used by a later step"),
    ({"steps": [{"mix": [1]}]}, "not in the flow"),
    ({"steps": [{"mix": ["s1", 1, 2]}]}, "not an earlier step"),
    ({"steps": [{"mix": [7]}]}, "no ingredient"),
    ({"steps": [{"mix": [1], "stir": [2]}]}, "one-key"),
])
def test_validation(flow, msg):
    with pytest.raises(FlowError, match=msg):
        parse(flow, 2)


def test_html_and_ingredients():
    body = "## Ingredients\n\n- a\n- b\n\n## Method\n\n1. go\n"
    ings = ingredients_from_markdown(body)
    assert ings == ["a", "b"]
    out = to_html({"before": ["heat"], "steps": [{"mix & stir": [1, 2]}]}, ings)
    assert 'rowspan="2"' in out and "mix &amp; stir" in out and 'colspan="2">heat' in out
    assert out.isascii()
