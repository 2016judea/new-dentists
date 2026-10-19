"""The page prints counts straight from private/rows.json, and site/ ships only the free slice
(README "## Free, and paid"). Run from the repo root: python3 -m pytest -q tests
"""
import gzip, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "private" / "rows.json"))
ROWS = D["rows"]
PAGE = (ROOT / "site" / "index.html").read_text()
FREE = json.loads(re.search(r"\nconst FREE=(\{.*?\});\n", PAGE).group(1))
FULL = json.loads(gzip.open(ROOT / "private" / "bundle" / "full.json.gz", "rt").read())["rows"]
PAID = ["addr", "zip", "phone", "official", "official_phone", "legal", "npi", "others", "buildout"]
PHONE = re.compile(r"\(\d{3}\) \d{3}-\d{4}")


def test_rows_sit_inside_the_window_and_do_not_repeat():
    for r in ROWS:
        assert D["since"] <= r["enum"] <= D["through"], (r["name"], r["enum"])
    npis = [r["npi"] for r in ROWS if r["npi"]]
    assert len(npis) == len(set(npis))
    for r in ROWS:
        for k in ("phone", "official_phone"):
            assert not r[k] or PHONE.fullmatch(r[k]), (r["name"], r[k])
        if r["kind"] == "New dentist" and not r["addr"]:
            assert not r["phone"] and r["lat"] is None, r  # a possible home address stays private


def test_page_counts_are_the_data():
    n = len(ROWS)
    prac = sum(r["kind"] == "New practice" for r in ROWS)
    dds = sum(r["kind"] == "New dentist" for r in ROWS)
    fit = sum(r["fit"] and r["kind"] != "Office build-out" for r in ROWS)
    assert FREE["total"] == n
    assert f"<h1>{prac} new dental practices and {dds} new dentists" in PAGE
    assert f"These are the {n} that got their first NPI" in PAGE
    assert f"<b>{fit} work in general, prosthodontic or pediatric dentistry</b>" in PAGE
    assert f'stats:[["{prac}","new dental practices"],["{dds}","dentists new to practice"],["{fit}",' in PAGE
    for k, v in FREE["counts"].items():
        assert v == sum(r["kind"] == k for r in ROWS), k
    assert len(FREE["dots"]) == sum(bool(r.get("lat")) for r in ROWS)


def test_site_ships_only_the_free_slice():
    assert len(FREE["rows"]) == 8 and len(FULL) == len(ROWS)
    keys = {k for r in FREE["rows"] for k in r}
    assert not keys & set(PAID), keys & set(PAID)
    for r in FREE["rows"]:
        assert any(f["name"] == r["name"] and f["enum"] == r["enum"] and f["city"] == r["city"] for f in FULL), r["name"]
    assert not list((ROOT / "site").rglob("*.gz")) and not (ROOT / "site" / "api" / "_full").exists()
    assert "_vercel/insights/script.js" in PAGE and "posthog" in PAGE
