# New Twin Cities Dentists

**Live:** https://new-dentists.vercel.app

Every dental practice and every dentist new to practice in the seven-county Twin Cities
metro in the last twelve months, from the federal provider register. Built for dental labs
and anyone else who sells to a dental office: a practice that just opened, or a dentist who
just started, has no lab habit yet.

## Free, and paid

| free, no login | $5, once |
|---|---|
| the counts: new practices, new dentists, how many do general, prosthodontic or pediatric work, by county | all 102 rows |
| eight real rows, a fair cut across the year: name, specialty, city, date | each office's street address and phone |
| every row's dot on the map | the owner or authorized official, and their phone |
| filter by kind | newest-first and biggest-office-first sorts |
| | the spreadsheet |

Why this split: the first prospect, a St. Paul lab, wrote *"Text with a brief message and
we will respond with in minutes."* The thing a lab acts on is a phone number and a name to
ask for. The counts and sample show the list is real; the contact fields are the job.

## Price

**$5, once.** Set 2026-10-17 by Aidan for this round, as a hypothesis under test. The
tenth-of-one-use rule would put it far higher: one new denture account is worth hundreds of
dollars a year to a lab. $5 tests whether anyone pays at all, not what it is worth.

## Sources

- **NPPES** (CMS), the monthly full replacement file, public domain. Dental taxonomy 1223*,
  first NPI in the twelve months the file covers, practice in Anoka, Carver, Dakota, Hennepin,
  Ramsey, Scott or Washington County (Census geocoder), not deactivated.
- **Minneapolis permit register** (CCS_Permits): commercial permits naming a dental office.
  Saint Paul's register stopped in mid-2025 and the suburbs publish none, so build-outs are
  Minneapolis only.

What each field answers, and which ones reality could only fill by proxy: `DATA_MODEL.md`.

## Run it

```
python3 pipeline/pull.py NPPES_Data_Dissemination_<Month>_<Year>_V2.zip   # from download.cms.gov/nppes/NPI_Files.html
python3 pipeline/build.py        # private/rows.json
cd scripts && python3 publish.py # site/index.html (free slice) + private/bundle/full.json.gz (paid)
VERCEL_TOKEN=... python3 scripts/deploy.py
```

## The paywall

Ported from msp-house-index via mpls-new-rentals (`scripts/sitekit.py`, `site/paywall.js`,
`site/api/`). `site/` ships only the free slice; the full rows live in `private/bundle/`
(gitignored), uploaded as `api/_full/` and served by `/api/data` to an HMAC password minted at
Stripe embedded Checkout (Brick and Mortar account). Price and copy: `site/offer.json`.

The password reaches the buyer two ways: the return page (`/api/session-status`) emails it by
Mailgun, and the Stripe invoice footer carries it. **There is no Stripe webhook**: the account
is at Stripe's cap of 16 live webhook endpoints, so a buyer who closes the tab before the
return page loads gets the password only from the invoice. `python3 scripts/fulfil.py --recent`
lists every session; `scripts/issue_password.py "comp:<label>"` makes a free one.

Funnel events (Vercel + PostHog): `preview_open`, `checkout_open`, `paid`, `unlock`,
`lock_click`, `download`, `sort`, `filter`.
