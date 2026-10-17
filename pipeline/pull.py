#!/usr/bin/env python3
"""Pull the two public sources into private/cache/.

1. NPPES (CMS), the monthly full replacement file, public domain. Kept: every row with a
   dental taxonomy (1223*) whose practice state is MN. ~1.1 GB zip, ~35 s to filter.
2. Minneapolis permit register (CCS_Permits): commercial permits in the last year whose
   description names a dental office.

    python3 pipeline/pull.py [NPPES_Data_Dissemination_<Month>_<Year>_V2.zip]
"""
import json, re, subprocess, sys, urllib.request, urllib.parse
from pathlib import Path
C = Path(__file__).resolve().parent.parent / "private" / "cache"
C.mkdir(parents=True, exist_ok=True)
Z = sys.argv[1] if len(sys.argv) > 1 else None
if Z:
    names = subprocess.run(["unzip", "-Z1", Z], capture_output=True, text=True, check=True).stdout.split()
    data = next(n for n in names if n.startswith("npidata_pfile") and not n.endswith("fileheader.csv"))
    hdr = next(n for n in names if n.startswith("npidata_pfile") and n.endswith("fileheader.csv"))
    with open(C / "dent_mn.csv", "wb") as out:
        out.write(subprocess.run(["unzip", "-p", Z, hdr], capture_output=True, check=True).stdout)
        p1 = subprocess.Popen(["unzip", "-p", Z, data], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["grep", "-E", '"1223[0-9A-Z]{6}"'], stdin=p1.stdout, stdout=subprocess.PIPE, env={"LC_ALL": "C"})
        p3 = subprocess.Popen(["grep", "-E", ',"MN",'], stdin=p2.stdout, stdout=out, env={"LC_ALL": "C"})
        p3.wait()
    (C / "nppes_file.txt").write_text(Path(Z).name + " " + data + "\n")
U = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/CCS_Permits/FeatureServer/0/query"
F = "Display,APN,Latitude,Longitude,applicantName,permitNumber,permitType,occupancyType,workType,status,milestone,comments,issueDate,completeDate"
out, off = [], 0
while True:
    q = urllib.parse.urlencode(dict(where="permitType='Commercial' AND issueDate >= CURRENT_TIMESTAMP - 365", outFields=F, f="json", resultOffset=off, resultRecordCount=2000))
    d = json.load(urllib.request.urlopen(U + "?" + q)); fs = [f["attributes"] for f in d["features"]]; out += fs
    if not d.get("exceededTransferLimit") or not fs: break
    off += len(fs)
hit = [a for a in out if re.search(r"\b(dental (office|clinic)|dentist\w*|orthodont\w*|endodont\w*|oral surg\w*)\b", a["comments"] or "", re.I)]
json.dump(hit, open(C / "dental_permits.json", "w"))
print("commercial permits", len(out), "dental office permits", len(hit))
