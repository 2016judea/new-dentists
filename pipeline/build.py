#!/usr/bin/env python3
"""New Twin Cities dentists and dental practices, from NPPES. Writes private/rows.json.

A row is a dental NPI (taxonomy 1223*) enumerated in the twelve months the NPPES file
covers, practising in the seven metro counties, not deactivated. See DATA_MODEL.md.
"""
import csv, io, json, re, datetime as dt, collections, urllib.request
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "private" / "cache"
METRO = {"003": "Anoka", "019": "Carver", "037": "Dakota", "053": "Hennepin", "123": "Ramsey", "139": "Scott", "163": "Washington"}
SPEC = {"1223G0001X": "General practice", "1223P0221X": "Pediatric", "1223X0400X": "Orthodontics", "1223E0200X": "Endodontics",
        "1223P0300X": "Periodontics", "1223P0700X": "Prosthodontics", "1223S0112X": "Oral surgery", "1223D0001X": "Dental public health",
        "1223X0008X": "Oral & maxillofacial radiology", "1223P0106X": "Oral pathology", "1223D0004X": "Dentist anesthesiologist",
        "122300000X": "Dentist", "1223X2210X": "Orofacial pain"}
# Who sends a lab dentures, partials and night guards: general, prosthodontic and pediatric offices do; orthodontists rarely.
LAB_FIT = {"General practice", "Prosthodontics", "Dentist", "Pediatric", "Dental public health", "Periodontics"}

con = duckdb.connect()
con.sql(f"create table raw as select * from read_csv('{C/'dent_mn.csv'}', all_varchar=true, header=true)")
tx = ", ".join(f'"Healthcare Provider Taxonomy Code_{i}"' for i in range(1, 16))
pr = ", ".join(f'"Healthcare Provider Primary Taxonomy Switch_{i}"' for i in range(1, 16))
con.sql(f"""create table d as select NPI npi, "Entity Type Code" et,
  "Provider Organization Name (Legal Business Name)" org, "Provider Other Organization Name" dba,
  "Provider First Name" fname, "Provider Last Name (Legal Name)" lname, "Provider Credential Text" cred,
  "Provider First Line Business Practice Location Address" a1, "Provider Second Line Business Practice Location Address" a2,
  "Provider Business Practice Location Address City Name" city, left("Provider Business Practice Location Address Postal Code", 5) zip,
  "Provider Business Practice Location Address Telephone Number" phone,
  "Authorized Official First Name" ao_f, "Authorized Official Last Name" ao_l, "Authorized Official Title or Position" ao_t,
  "Authorized Official Telephone Number" ao_p,
  strptime("Provider Enumeration Date", '%m/%d/%Y')::date enumd, coalesce("NPI Deactivation Date", '') deact,
  coalesce("NPI Reactivation Date", '') react, [{tx}] tax, [{pr}] prim
  from raw where "Provider Business Practice Location Address State Name" = 'MN'""")
q = con.sql("select * from d where deact = '' or react <> ''"); cols = q.columns
active = [dict(zip(cols, t)) for t in q.fetchall()]
# The window is the twelve months the NPPES file covers: its member name ends in the cut-off date.
src = (C / "nppes_file.txt").read_text().split()
latest = dt.datetime.strptime(re.search(r"-(\d{8})\.csv", src[1]).group(1), "%Y%m%d").date()
since = latest - dt.timedelta(days=364)

def norm(a):
    a = re.sub(r"[^A-Z0-9 ]", " ", (a or "").upper())
    a = re.sub(r"\b(SUITE|STE|UNIT|APT|FL|FLOOR|BLDG|#)\b.*", "", a)
    for k, v in {"STREET": "ST", "AVENUE": "AVE", "ROAD": "RD", "DRIVE": "DR", "BOULEVARD": "BLVD", "LANE": "LN", "PARKWAY": "PKWY",
                 "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "HIGHWAY": "HWY", "COURT": "CT", "CIRCLE": "CIR", "PLACE": "PL"}.items():
        a = re.sub(rf"\b{k}\b", v, a)
    return re.sub(r"\s+", " ", a).strip()

at = collections.defaultdict(set)
for r in active:
    at[(norm(r["a1"]), r["zip"])].add(r["npi"])

new = [r for r in active if r["enumd"] >= since]
# geocode (Census batch, cached by npi)
GC = C / "geocode.json"
geo = json.loads(GC.read_text()) if GC.exists() else {}
todo = [r for r in new if r["npi"] not in geo]
for i in range(0, len(todo), 500):
    buf = io.StringIO(); w = csv.writer(buf)
    for r in todo[i:i + 500]:
        w.writerow([r["npi"], r["a1"], r["city"], "MN", r["zip"]])
    body, bd = [], "----bm" + str(i)
    data = (f"--{bd}\r\nContent-Disposition: form-data; name=\"benchmark\"\r\n\r\nPublic_AR_Current\r\n"
            f"--{bd}\r\nContent-Disposition: form-data; name=\"vintage\"\r\n\r\nCurrent_Current\r\n"
            f"--{bd}\r\nContent-Disposition: form-data; name=\"addressFile\"; filename=\"a.csv\"\r\nContent-Type: text/csv\r\n\r\n{buf.getvalue()}\r\n--{bd}--\r\n").encode()
    req = urllib.request.Request("https://geocoding.geo.census.gov/geocoder/geographies/addressbatch", data=data,
                                 headers={"Content-Type": f"multipart/form-data; boundary={bd}"})
    for row in csv.reader(io.StringIO(urllib.request.urlopen(req, timeout=300).read().decode())):
        if len(row) >= 6 and row[2] == "Match":
            lon, lat = map(float, row[5].split(","))
            geo[row[0]] = {"lat": lat, "lon": lon, "county": row[9] if len(row) > 9 else ""}
        else:
            geo.setdefault(row[0], {})
    GC.write_text(json.dumps(geo))

# ZIP fallback for addresses the geocoder missed: county by the matched rows in the same ZIP
zc = collections.defaultdict(collections.Counter)
for r in new:
    g = geo.get(r["npi"]) or {}
    if g.get("county"): zc[r["zip"]][g["county"]] += 1

permits = json.load(open(C / "dental_permits.json"))
pmt = {}
for p in permits:
    if re.search(r"assistant program", p["comments"] or "", re.I):  # a school, not an office
        continue
    pmt[norm(p["Display"])] = p

KEEP = {"LLC", "PLLC", "PA", "P.A.", "DDS", "DMD", "PC", "P.C.", "MS", "MSD", "NE", "NW", "SE", "SW", "N", "S", "E", "W", "II", "III", "IV", "PLC", "LTD"}
def title(s):
    s = "" if (s or "").upper() == "<UNAVAIL>" else (s or "")
    out = []
    for w in s.split():
        u = w.upper().strip(",")
        out.append(w.upper() if u in KEEP or re.match(r"^([A-Za-z]\.)+,?$", w) or re.match(r"^\d", w) else w[:1].upper() + w[1:].lower())
    return re.sub(r"\bMc([a-z])", lambda m: "Mc" + m.group(1).upper(), " ".join(out))
phone = lambda p: f"({p[:3]}) {p[3:6]}-{p[6:10]}" if p and len(re.sub(r'\D', '', p)) >= 10 else ""

rows = []
for r in new:
    g = geo.get(r["npi"]) or {}
    county = g.get("county") or (zc[r["zip"]].most_common(1)[0][0] if zc[r["zip"]] else "")
    if county not in METRO:
        continue
    codes = [c for c in r["tax"] if c and c.startswith("1223")]
    prim = next((c for c, s in zip(r["tax"], r["prim"]) if s == "Y" and c and c.startswith("1223")), codes[0] if codes else "")
    spec = SPEC.get(prim, "Dentist")
    others = len(at[(norm(r["a1"]), r["zip"])] - {r["npi"]})
    org = r["et"] == "2"
    name = title(r["dba"] if (r["dba"] or "").upper() != "<UNAVAIL>" and r["dba"] else r["org"]) if org else " ".join(x for x in [title(r["fname"]), title(r["lname"])] if x) + (f", {r['cred'].replace('.', '').upper()}" if r["cred"] else "")
    # An individual whose practice address no other dental NPI shares may be a home address: city only.
    shared = org or others > 0
    p = pmt.get(norm(r["a1"]))
    rows.append(dict(
        npi=r["npi"], kind="New practice" if org else "New dentist", name=name, legal=title(r["org"]) if org and r["dba"] and r["dba"].upper() != "<UNAVAIL>" else "",
        spec=spec, fit=spec in LAB_FIT, enum=r["enumd"].isoformat(), city=title(r["city"]), county=METRO[county],
        addr=title(" ".join(x for x in [r["a1"], r["a2"]] if x)) if shared else "", zip=r["zip"] if shared else "",
        phone=phone(r["phone"]) if shared else "", others=others,
        official=(" ".join(x for x in [title(r["ao_f"]), title(r["ao_l"])] if x) + (f" ({title(r['ao_t'])})" if r["ao_t"] else "")) if org else "",
        official_phone=phone(r["ao_p"]) if org else "",
        buildout=(dt.datetime.utcfromtimestamp(p["issueDate"] / 1000).date().isoformat() + " " + (p["milestone"] or p["status"] or "")) if p else "",
        lat=round(g["lat"], 4) if g.get("lat") and shared else None, lon=round(g["lon"], 4) if g.get("lon") and shared else None))
# Dental offices being built out (Minneapolis only: the one register that publishes). Named from
# NPPES when a dental NPI already sits at the address; never parsed out of the permit text.
byaddr = collections.defaultdict(list)
for r in active:
    byaddr[" ".join(sorted(norm(r["a1"]).split()))].append(r)
for a, p in pmt.items():
    a = " ".join(sorted(a.split()))
    here = [x for x in byaddr.get(a, []) if x["et"] == "2"] or byaddr.get(a, [])
    h = here[0] if here else None
    when = dt.datetime.utcfromtimestamp(p["issueDate"] / 1000).date().isoformat()
    what = re.split(r"\s+-?[A-Z]{2,4}\b\s+certificate|\s+-[A-Z]{3}\b|\s{3,}", (p["comments"] or "").strip())[0].strip()
    rows.append(dict(npi="", kind="Office build-out", name=(title(h["org"]) if h and h["et"] == "2" else (f"Dental office at {title(p['Display'])}")),
        legal="", spec="Dental office", fit=True, enum=when, city="Minneapolis", county="Hennepin", addr=title(p["Display"]), zip="",
        phone=phone(h["phone"]) if h else "", others=len(byaddr.get(a, [])), official="", official_phone="",
        buildout=f"Permit {when}: {what} ({p['milestone'] or p['status']}). Contractor {title(p['applicantName'] or '')}",
        lat=round(p["Latitude"], 4) if p.get("Latitude") else None, lon=round(p["Longitude"], 4) if p.get("Longitude") else None))
rows.sort(key=lambda r: r["enum"], reverse=True)
json.dump({"through": latest.isoformat(), "since": since.isoformat(), "source": src[0], "built": dt.date.today().isoformat(), "rows": rows},
          open(ROOT / "private" / "rows.json", "w"), indent=0)
k = collections.Counter(r["kind"] for r in rows)
print("window", since, "to", latest, "| metro rows", len(rows), dict(k), "| lab fit", sum(r["fit"] for r in rows),
      "| address shown", sum(bool(r["addr"]) for r in rows), "| phone", sum(bool(r["phone"]) for r in rows),
      "| mapped", sum(r["lat"] is not None for r in rows), "| buildout", sum(bool(r["buildout"]) for r in rows))
print(collections.Counter(r["county"] for r in rows).most_common(), collections.Counter(r["spec"] for r in rows).most_common())
