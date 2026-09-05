"""Parse the 'Add a recipe' issue form body into GITHUB_OUTPUT lines.

The issue form renders each field as '### <Label>' followed by its value,
and checkboxes as '- [x] <label>'. Prints url=, slug=, force=.
"""

import os
import re
import sys

body = os.environ.get("ISSUE_BODY", "")


def field(label):
    m = re.search(r"^### %s\s*\n+(.*?)(?=\n### |\Z)" % re.escape(label), body, re.S | re.M)
    if not m:
        return ""
    val = m.group(1).strip()
    return "" if val in ("_No response_", "") else val


url = field("Recipe URL").split()[0] if field("Recipe URL") else ""
slug = field("File name (optional)").strip().lower()
force = bool(re.search(r"^- \[x\] Overwrite", body, re.M | re.I))

if not re.match(r"^https?://[^\s]+$", url):
    print("could not find a URL in the issue body", file=sys.stderr)
    sys.exit(1)
if slug and not re.match(r"^[a-z0-9][a-z0-9-]{0,79}$", slug):
    print("invalid slug %r: use lower-case letters, digits, hyphens" % slug, file=sys.stderr)
    sys.exit(1)

print("url=%s" % url)
print("slug=%s" % slug)
print("force=%s" % ("true" if force else "false"))
