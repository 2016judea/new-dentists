#!/usr/bin/env python3
"""Write site/index.html (free slice) and private/bundle/full.json.gz (the paid list) from
private/rows.json (pipeline/build.py). Every number on the page is computed here."""
import json, collections, datetime as dt
from sitekit import render
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "private" / "rows.json"))
rows = D["rows"]
for r in rows:
    r["county"] = r["county"]
ORDER = ["New practice", "New dentist", "Office build-out"]
PAID = ["addr", "zip", "phone", "official", "official_phone", "legal", "npi", "others", "buildout"]
n_prac = sum(r["kind"] == "New practice" for r in rows); n_dds = sum(r["kind"] == "New dentist" for r in rows)
fit = sum(r["fit"] and r["kind"] != "Office build-out" for r in rows)
through = dt.date.fromisoformat(D["through"]).strftime("%b %-d, %Y"); since = dt.date.fromisoformat(D["since"]).strftime("%b %-d, %Y")
counties = collections.Counter(r["county"] for r in rows)
# The free sample: every 13th row across the whole year, so it is a fair cut and not the newest.
sample = [r for r in rows if r["kind"] != "Office build-out"][5::13][:8]
COLS = [("kind", "Kind"), ("name", "Name"), ("legal", "Legal name"), ("spec", "Specialty"), ("enum", "NPI issued"), ("addr", "Practice address"),
        ("city", "City"), ("zip", "ZIP"), ("county", "County"), ("phone", "Practice phone"), ("official", "Owner / authorized official"),
        ("official_phone", "Official's phone"), ("others", "Other dental NPIs at this address"), ("buildout", "Build-out permit (Minneapolis)"), ("npi", "NPI")]
cfg = """{chipKey:"kind",chipOrder:%s,csv:"new-twin-cities-dentists.csv",cols:%s,
 stats:[["%d","new dental practices"],["%d","dentists new to practice"],["%d","of them in general, prosthodontic or pediatric work"]],
 legend:[["var(--hot)","New practice"],["var(--accent)","New dentist"],["var(--done)","Office build-out"]],
 dotColor:["var(--hot)","var(--accent)","var(--done)"],
 color:r=>r.kind==="New practice"?"var(--hot)":r.kind==="New dentist"?"var(--accent)":"var(--done)",
 labels:[[44.978,-93.265,"Minneapolis"],[44.946,-93.093,"St. Paul"]],
 title:r=>r.name, what:r=>r.spec+(r.kind==="Office build-out"?"":(" · "+(r.kind==="New practice"?"practice NPI":"first NPI")+" "+fmt(r.enum))),
 tag:r=>`<span class="tag ${r.kind==="New practice"?"hot":""}">${r.kind}</span>`,
 meta:r=>[r.city,r.county+" County"],
 paid:r=>[r.addr?esc(r.addr)+(r.zip?" "+esc(r.zip):""):"Address not shown (may be a home)",r.phone?`<a href="tel:${esc(r.phone)}">${esc(r.phone)}</a>`:"",r.official?`Owner: ${esc(r.official)}`:"",r.official_phone?`<a href="tel:${esc(r.official_phone)}">${esc(r.official_phone)}</a>`:"",r.others?`${r.others} other dental NPI${r.others===1?"":"s"} at this address`:"",r.buildout?esc(r.buildout):""].filter(Boolean).join(" · "),
 sorts:[["city","By city",false],["newest","Newest first",true],["size","Biggest office first",true]],
 sortFn:{city:r=>r.sort((a,b)=>a.city.localeCompare(b.city)||b.enum.localeCompare(a.enum)),newest:r=>r.sort((a,b)=>b.enum.localeCompare(a.enum)),size:r=>r.sort((a,b)=>(b.others||0)-(a.others||0)||b.enum.localeCompare(a.enum))},
 lockText:n=>`${n} more, with each office's address, phone and owner`}""" % (json.dumps(ORDER), json.dumps(COLS), n_prac, n_dds, fit)
LIGHT = '--bg:#f4f6f5;--panel:#e8edeb;--ink:#14201c;--ink2:#33433d;--muted:#5f6f69;--rule:#d0dad6;--accent:#1d6b5a;--onaccent:#f4f6f5;--hot:#b4532a;--done:#8a9692;--ghost:#c3cdc9;--water:#9fb8c4;--tagbg:#dfe7e4;--tagfg:#3d4d47;--hotbg:#f4dccf;--hotfg:#8a3815;--display:"Newsreader",Georgia,serif;--body:"Inter",system-ui,sans-serif;--h1w:600;'
DARK = '--bg:#0f1513;--panel:#17201d;--ink:#e6eeeb;--ink2:#c2cfca;--muted:#8a9a94;--rule:#2a3632;--accent:#6fc2ad;--onaccent:#0f1513;--hot:#ec8d62;--done:#6c7a75;--ghost:#33403b;--water:#3c5a68;--tagbg:#1f2a26;--tagfg:#b2c0bb;--hotbg:#45230f;--hotfg:#f5b996;'
top = ", ".join(f"{c} {n}" for c, n in counties.most_common())
counts = render(rows=rows, sample=sample, paid_fields=PAID, chip_key="kind", chip_order=ORDER, cfg_js=cfg, site="new-dentists", subs={
 "__TITLE__": "New Twin Cities Dentists",
 "__DESC__": f"{len(rows)} new dental practices and dentists new to practice in the Twin Cities metro, {since} to {through}.",
 "__FONTS__": "family=Newsreader:opsz,wght@6..72,600&family=Inter:wght@400;500;600",
 "__LIGHT__": LIGHT, "__DARK__": DARK,
 "__EYEBROW__": f"For dental labs and anyone who sells to a dental office · Twin Cities metro · federal provider records through {through}",
 "__H1__": f"{n_prac} new dental practices and {n_dds} new dentists in the Twin Cities this year",
 "__LEDE__": f"A practice that just opened, or a dentist who just started, has no lab habit yet. These are the {len(rows)} that got their first NPI, the number every dentist needs before billing a patient, between {since} and {through}. <b>{fit} work in general, prosthodontic or pediatric dentistry</b>, the offices that send out dentures, partials and night guards.",
 "__MAPLABEL__": "Map of the Twin Cities metro with each new practice and dentist as a dot",
 "__NOTE__": f"<p>Source: the National Plan and Provider Enumeration System (NPPES), the federal register of every health provider's NPI, published by CMS and in the public domain. File: {D['source']}. Practices and dentists with a dental taxonomy (1223), a first NPI dated {since} to {through}, a practice address in Anoka, Carver, Dakota, Hennepin, Ramsey, Scott or Washington County, and no deactivation. By county: {top}.</p><p>A new NPI is the best public signal of a new practice or a dentist new to practice. It is not a licence date. Office build-outs come from the Minneapolis permit register, the only one in the metro that publishes, so they cover Minneapolis only. When no other dental provider shares a dentist's listed address, the address is left out, because it may be a home.</p><p>From Aidan Jude at Brick &amp; Mortar (aidan@brickandmortar.dev).</p>"})
print("rows", len(rows), "practices", n_prac, "dentists", n_dds, "lab fit", fit, "counties", dict(counties), counts, "sample", len(sample), [s["name"] for s in sample])
