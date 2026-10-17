# Data model: new Twin Cities dentists and practices

Written 2026-10-17 from the need alone (BUSINESS.md rule 5), then checked against what
can be obtained. The buyer is a dental lab, or anyone who sells to a dental office
(supply house, equipment, IT, billing). The first prospect wrote: *"Dentures, Partials
and night guards... Resonable prices with quick turn over."* A lab's next account is a
dentist who has no lab yet: a new practice, or a dentist new to practice.

## The ideal model

**Practice** (one dental office at one address)
| field | the question it answers |
|---|---|
| name | who do I ask for? |
| address, city, county | can I deliver and pick up cases there? |
| phone | how do I reach them today? |
| owner / authorized official, title | who decides which lab they use? |
| opened date | is this a new office with no lab relationship yet? |
| specialty | do they send out dentures and partials (general, prosthodontics) or not (ortho)? |
| dentists at this address | how big is the account? |
| build-out stage | are they still building, so I can be first in the door? |

**Dentist** (one licensed person)
| field | the question it answers |
|---|---|
| name, credential | who is it? |
| licence or first-practice date | are they new, so they have no lab habit yet? |
| specialty | will they ever send me a denture? |
| practice joined (→ Practice) | where do I find them, and do they choose the lab or does the owner? |

Joins: Dentist → Practice on practice address + phone. Build-out → Practice on address.

## Reality check, field by field (2026-10-17)

| field | source | filled? |
|---|---|---|
| practice name, address, phone, official + title, specialty | NPPES (CMS), public domain, October 2026 full file (to 10/11) | **yes** |
| opened date | NPPES enumeration date of the organisation NPI | **yes, as a proxy**: a practice gets an NPI when it forms, usually before it bills |
| dentist name, credential, specialty | NPPES individual NPI | **yes** |
| licence / first-practice date | MN Board of Dentistry licence date would be exact; not pulled | **proxy**: NPI enumeration date. A dentist gets an NPI on entering practice |
| practice joined | NPPES individual practice address, matched to other dental NPIs at the same address | **yes**, as "dental NPIs at this address" |
| dentists at this address | same match over every active Minnesota dental NPI | **yes** |
| build-out stage | Minneapolis permit register (CCS_Permits) | **thin**: 2 dental-office permits in 12 months; Saint Paul's register stopped 2025-06-30; suburbs publish none |
| county | Census geocoder on the practice address | **yes** |

Verdict: buildable. Build-out stage is the one weak field; it ships as a flag on the
two Minneapolis rows it fills, never as a promise of coverage.

Window: NPI enumerated 2025-10-12 to 2026-10-11 (the twelve months the October file
covers), practice in the seven metro counties, NPI not deactivated.
