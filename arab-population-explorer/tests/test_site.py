"""Static checks for the website: HTML parses, local files exist, embedded data is sane."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import build_data as b

SITE = Path(__file__).resolve().parents[1] / "site"


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.stack, self.errors = [], set(), [], []

    VOID = {"meta", "link", "input", "br", "img", "hr"}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("src", "href"):
            if a.get(key):
                self.refs.append(a[key])
        if "id" in a:
            self.ids.add(a["id"])
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}>")
        else:
            self.stack.pop()


def parse():
    p = Refs()
    p.feed((SITE / "index.html").read_text(encoding="utf-8"))
    return p


def test_html_is_well_formed_and_local_refs_exist():
    p = parse()
    assert not p.errors and not p.stack
    local = [r for r in p.refs if not re.match(r"^(https?:|mailto:|#)", r)]
    assert local, "expected local scripts/styles"
    for ref in local:
        assert (SITE / ref).is_file(), ref


def test_no_external_scripts_or_trackers():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script[^>]+src=\"https?:", html)
    js = (SITE / "app.js").read_text(encoding="utf-8")
    assert "fetch(" not in js and "XMLHttpRequest" not in js


def test_every_id_used_by_app_js_exists():
    ids = parse().ids
    used = set(re.findall(r'\$\("([A-Za-z]+)"\)', (SITE / "app.js").read_text(encoding="utf-8")))
    assert used and used <= ids, used - ids


def test_embedded_data():
    text = (SITE / "data.js").read_text(encoding="utf-8")
    data = json.loads(text[text.index("=") + 1:].strip().rstrip(";"))
    years = data["years"]
    assert years == list(range(years[0], years[-1] + 1)) and years[0] == b.FIRST_YEAR
    series = data["series"]
    assert sum(1 for s in series.values() if s["country"]) == 22
    for code, s in series.items():
        assert len(s["v"]) == len(years), code
        assert s["v"][-1] is not None and s["v"][-1] > 0, code
    # GCC column equals the sum of its members wherever present
    gcc = [c for c, s in series.items() if s["gcc"]]
    assert len(gcc) == 6
    i = years.index(2000)
    assert series["GCC"]["v"][i] == sum(series[c]["v"][i] for c in gcc)
