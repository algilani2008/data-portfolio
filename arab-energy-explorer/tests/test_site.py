"""Static checks on the website: the page parses, local files exist, and the data is sane."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1] / "site"
VOID = {"meta", "link", "input", "br", "img", "hr"}


class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.refs, self.ids, self.t_keys, self.errors = [], [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.stack.append(tag)
        for key in ("src", "href"):
            if key in a:
                self.refs.append(a[key])
        if "id" in a:
            self.ids.append(a["id"])
        if "data-t" in a:
            self.t_keys.append(a["data-t"])

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.errors.append(f"unbalanced </{tag}> at {self.getpos()}")


@pytest.fixture(scope="module")
def page():
    checker = Checker()
    checker.feed((SITE / "index.html").read_text(encoding="utf-8"))
    return checker


@pytest.fixture(scope="module")
def data():
    text = (SITE / "data.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("window.AEE_DATA=") + len("window.AEE_DATA="):].rstrip().rstrip(";"))


def test_index_parses_with_balanced_tags(page):
    assert page.errors == []
    assert page.stack == []


def test_every_local_reference_exists(page):
    local = [r for r in page.refs if not r.startswith(("http://", "https://", "#"))]
    assert local, "expected local references"
    for ref in local:
        assert (SITE / ref).is_file(), ref


def test_page_loads_nothing_from_other_hosts(page):
    assert [r for r in page.refs if r.startswith(("http://", "https://"))] == []
    js = (SITE / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"fetch\(|XMLHttpRequest|localStorage|sendBeacon", js)


def test_ids_used_by_app_exist_in_page(page):
    js = (SITE / "app.js").read_text(encoding="utf-8")
    used = set(re.findall(r"\$\('([\w-]+)'\)", js))
    assert used - set(page.ids) == set()


def test_ids_are_unique(page):
    assert len(page.ids) == len(set(page.ids))


def test_every_text_key_exists_in_both_languages(page):
    js = (SITE / "app.js").read_text(encoding="utf-8")
    blocks = re.split(r"\n    en: \{", js[js.index("var T = {"):js.index("var TERMS")])
    assert len(blocks) == 2
    for key in set(page.t_keys):
        for block in blocks:
            assert re.search(rf"\b{key}:", block), key


def test_data_shape(data):
    n = len(data["years"])
    assert len(data["countries"]) == 22
    assert set(data["values"]) == {c["code"] for c in data["countries"]} | {"WLD"}
    for row in data["values"].values():
        for key, values in row.items():
            if key == "mix":
                assert all(len(v) == n for v in values.values())
            else:
                assert len(values) == n


def test_shares_are_percentages(data):
    for row in data["values"].values():
        for key, values in row.items():
            if key.endswith("_share_elec"):
                assert all(v is None or -0.01 <= v <= 100.01 for v in values), key


def test_sources_never_exceed_generation_by_more_than_rounding(data):
    for code, row in data["values"].items():
        for i, gen in enumerate(row["electricity_generation"]):
            if gen:
                total = sum(v[i] or 0 for v in row["mix"].values())
                assert total <= gen * 1.02 + 0.02, (code, data["years"][i])
