"""Recipe flow: which ingredients go into which operation, as a tree.

The layout is the tabular recipe card popularised by Cooking for Engineers:
ingredients down the left, operations in columns to the right, each
operation cell spanning the rows of everything that goes into it, so the
final operation is the rightmost column.

A flow is hand-written in a recipe's front matter (the harvester cannot
derive one, the schema.org data has no structure for it):

    flow:
      before:
      - Butter and flour an 8x8-in pan
      - Preheat oven to 350 F (175 C)
      steps:
      - melt: [1]
      - mix: [s1, 2, 3, 4]
      - mix: [s2, 5]
      - fold in: [s3, 6, 7, 8, 9]
      - bake 30-40 min: [s4]

Each step is a one-key mapping, operation -> inputs. An integer input is an
ingredient, 1-based, in the order of the Ingredients list. "sN" is the
output of step N (1-based), which must come earlier. The last step is the
result; every other step feeds exactly one later step, and each ingredient
is used at most once. `before` (and optional `after`) lines span the full
width above (below) the table.

Table rows follow the tree, not the ingredient list, so the layout is
always well formed. Ingredients the flow does not use are an error, so a
card never silently drops one.
"""

import html
import re


class FlowError(ValueError):
    pass


_STEP_RE = re.compile(r"^s(\d+)$")


def parse(flow, n_ingredients):
    """Validate a front-matter flow; return (before, steps, after).

    steps is a list of (label, inputs) with inputs as ("i", k) or ("s", k),
    both 0-based.
    """
    if not isinstance(flow, dict) or not flow.get("steps"):
        raise FlowError("flow needs a non-empty 'steps' list")
    before = [str(x) for x in (flow.get("before") or [])]
    after = [str(x) for x in (flow.get("after") or [])]
    steps = []
    used_i, used_s = {}, {}
    for n, item in enumerate(flow["steps"]):
        if not isinstance(item, dict) or len(item) != 1:
            raise FlowError("step %d must be a one-key mapping 'operation: [inputs]'" % (n + 1))
        (label, inputs), = item.items()
        if not isinstance(inputs, list) or not inputs:
            raise FlowError("step %d (%s) needs a list of inputs" % (n + 1, label))
        parsed = []
        for x in inputs:
            if isinstance(x, bool):
                raise FlowError("step %d: bad input %r" % (n + 1, x))
            if isinstance(x, int):
                k = x - 1
                if not 0 <= k < n_ingredients:
                    raise FlowError("step %d: no ingredient %d (have %d)" % (n + 1, x, n_ingredients))
                if k in used_i:
                    raise FlowError("ingredient %d used by steps %d and %d" % (x, used_i[k] + 1, n + 1))
                used_i[k] = n
                parsed.append(("i", k))
                continue
            m = _STEP_RE.match(str(x).strip())
            if not m:
                raise FlowError("step %d: input %r is not an ingredient number or sN" % (n + 1, x))
            k = int(m.group(1)) - 1
            if not 0 <= k < n:
                raise FlowError("step %d: s%d is not an earlier step" % (n + 1, k + 1))
            if k in used_s:
                raise FlowError("s%d used by steps %d and %d" % (k + 1, used_s[k] + 1, n + 1))
            used_s[k] = n
            parsed.append(("s", k))
        steps.append((str(label), parsed))
    dangling = [k + 1 for k in range(len(steps) - 1) if k not in used_s]
    if dangling:
        raise FlowError("steps not used by a later step: %s" % ", ".join("s%d" % k for k in dangling))
    unused = [k + 1 for k in range(n_ingredients) if k not in used_i]
    if unused:
        raise FlowError("ingredients not in the flow: %s" % ", ".join(map(str, unused)))
    return before, steps, after


def layout(steps):
    """Place the tree on a grid.

    Returns (rows, ncols, cells). rows is the ingredient index for each table
    row; column 0 holds ingredients and columns 1..ncols-1 operations. cells
    is a list of dicts with row, col, rowspan, colspan, kind ("ing", "op",
    "gap") and value (ingredient index or step index; None for gaps).
    """
    height = []
    for label, inputs in steps:
        height.append(1 + max([height[k] for t, k in inputs if t == "s"] or [0]))

    rows, cells = [], []

    def place(s):
        """Lay out step s; return (first_row, last_row)."""
        h = height[s]
        first = len(rows)
        run = None  # open gap cell for consecutive ingredient inputs
        for t, k in steps[s][1]:
            if t == "i":
                r = len(rows)
                rows.append(k)
                cells.append(dict(row=r, col=0, rowspan=1, colspan=1, kind="ing", value=k))
                if h > 1:
                    if run is None:
                        run = dict(row=r, col=1, rowspan=1, colspan=h - 1, kind="gap", value=None)
                        cells.append(run)
                    else:
                        run["rowspan"] += 1
            else:
                run = None
                a, b = place(k)
                # Stretch the child's op cell right to meet this column.
                child = next(c for c in cells if c["kind"] == "op" and c["value"] == k)
                child["colspan"] = h - height[k]
        cells.append(dict(row=first, col=h, rowspan=len(rows) - first, colspan=1,
                          kind="op", value=s))
        return first, len(rows) - 1

    place(len(steps) - 1)
    return rows, height[-1] + 1, cells


def to_html(flow, ingredients):
    """Render a flow as an HTML table, or raise FlowError."""
    before, steps, after = parse(flow, len(ingredients))
    rows, ncols, cells = layout(steps)
    esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731

    def span(c):
        out = ""
        if c["rowspan"] > 1:
            out += " rowspan=\"%d\"" % c["rowspan"]
        if c["colspan"] > 1:
            out += " colspan=\"%d\"" % c["colspan"]
        return out

    out = ["<div class=\"flow\"><table>"]
    for line in before:
        out.append("<tr><td class=\"pre\" colspan=\"%d\">%s</td></tr>" % (ncols, esc(line)))
    by_row = {}
    for c in cells:
        by_row.setdefault(c["row"], []).append(c)
    for r in range(len(rows)):
        tds = []
        for c in sorted(by_row.get(r, []), key=lambda c: c["col"]):
            if c["kind"] == "ing":
                tds.append("<td class=\"ing\">%s</td>" % esc(ingredients[c["value"]]))
            elif c["kind"] == "op":
                tds.append("<td class=\"op\"%s>%s</td>" % (span(c), esc(steps[c["value"]][0])))
            else:
                tds.append("<td class=\"gap\"%s></td>" % span(c))
        out.append("<tr>%s</tr>" % "".join(tds))
    for line in after:
        out.append("<tr><td class=\"pre\" colspan=\"%d\">%s</td></tr>" % (ncols, esc(line)))
    out.append("</table></div>")
    return "\n".join(out)


def ingredients_from_markdown(body):
    """The bullet lines of the first '## Ingredients' section, in order."""
    m = re.search(r"^## Ingredients[^\n]*\n(.*?)(?=^## |\Z)", body, flags=re.M | re.S)
    if not m:
        return []
    return [line[2:].strip() for line in m.group(1).splitlines() if line.startswith("- ")]
