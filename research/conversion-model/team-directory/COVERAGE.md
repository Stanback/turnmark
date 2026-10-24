# National team-directory coverage target

The target is **85–90% of eligible U.S. teams in each major segment**, with
summer-only clubs optional. This is organizational research for local model
training/evaluation and reusable public provenance, not a hosted results service.
We have **not established that percentage**. A large listing count or national
finder capture is not proof of coverage of unique, currently operating teams.

The reproducible [coverage audit](coverage-audit.json) records the actual source
universes, state/category gaps and unknown denominators. Regenerate it after
every accepted directory update:

```sh
python3 research/conversion-model/directory_coverage.py \
  --output research/conversion-model/team-directory/coverage-audit.json
```

## What counts toward the target

| Segment | Enumeration and reconciliation needed |
| --- | --- |
| Year-round youth clubs | USA Swimming national finder reconciled against all LSC directories; YMCA and independent/non-USAS programs explicitly audited |
| Masters | National USMS finder reconciled against registered clubs, workout groups and LMSC lists; independent programs tracked as a separate gap |
| Collegiate varsity | NCAA plus NAIA, NJCAA and other applicable associations; season, U.S. location and men's/women's sponsorship retained |
| Collegiate club | Current registered College Club Swimming programs; historical/unregistered listings separated |
| High schools | Sport-specific statewide lists, both categories, all sections and independent/private-school associations where applicable |
| Middle schools | Track separately where a governing body actually publishes swimming sponsorship; unknown scope stays explicit |

Do not hide weak school coverage behind stronger club coverage or average the
segments into an invented national score. Middle-school/independent denominators
may remain open; label that limitation rather than claiming “all categories.”

## Evidence needed before reporting 85–90%

1. Define the eligible universe, season and unit: institution, independent team,
   category-specific program, registered club or workout group. A co-op is not
   automatically one team per member school. Individual-only meet entries do not
   establish independent teams.
2. Obtain authoritative enumeration/counts, retain every page and document
   receipt, and account for pagination, filters and categories. A championship's
   scoring table is a partial participant universe.
3. Reconcile identities through source IDs or reviewed explicit crosswalks.
   Short codes, shared pools and similar names are candidate evidence only.
   Preserve affiliations without counting one organization twice across sources.
4. Record actual matched eligible teams over a comparable denominator. Historical,
   future-alignment and unknown-activity entries must not silently count as
   current. A non-sponsoring jurisdiction needs affirmative evidence; no import
   is a gap, not a zero.
5. Publish per-segment/state/category coverage, unresolved identities, source
   freshness and a sample of current-operation checks. Keep statistical
   confidence claims separate from enumeration percentages.

## Canada

The 85–90% target is a U.S. target. Canadian coverage is reported separately
under `canada` in the audit, with a country dimension (`countries`) so U.S. and
Canadian assertions are never summed into one figure. The unit is the same:
source-scoped listings, not unique clubs.

| Province | Provincial-section source | Provincial listings | National-list rows | Status |
| --- | --- | ---: | ---: | --- |
| AB | Swim Alberta Find a Club | 118 | 43 | partial source assertions |
| BC | Swim BC Find a Club | 77 | 40 | partial source assertions |
| MB | Swim Manitoba clubs table | 26 | 15 | partial source assertions |
| NB | Swim NB (city-labelled links, not imported) | 0 | 13 | national list only |
| NL | Swimming NL Club Contacts labels | 12 | 11 | partial source assertions |
| NS | Swim Nova Scotia clubs page | 37 | 11 | partial source assertions |
| NT | via Swim Alberta | 3 | 2 | partial source assertions (no territorial directory) |
| NU | none | 0 | 0 | no imported listing |
| ON | Swim Ontario page-data | 199 | 101 | partial source assertions |
| PE | Swim PEI (two logo links, not imported) | 0 | 3 | national list only (plus the Swim PEI section rows) |
| QC | FNQ (policy and standings pages, not imported) | 0 | 90 | national list only |
| SK | Swim Saskatchewan four pages | 36 | 14 | partial source assertions |
| YT | none | 0 | 0 | no imported listing |

Twenty-three national rows have no postal code and therefore no province. The
national list supplies no club type, so its rows stay `program_kind=unknown`;
provincial kinds come from each section's own labels. National and provincial
rows for one club are separate assertions (309 of 508 provincial listings have a
website-host or normalized-name candidate in the national list) and are not
merged. University association sites (U SPORTS, CCAA, OUA, Canada West, AUS)
answered automated fetches with HTTP 403, so university swimming came through
the browser-review lane: 25 varsity programs and one club team (Carleton)
confirmed by a person on the universities' own athletics pages on 2026-10-23
(`university-athletics:browser-review`), alongside the twelve varsity listings
from Swim Ontario, Swim Manitoba and Swim Saskatchewan (eleven overlap by
name or website host; kept separate). Exclusions: University of Alberta
(swimming discontinued after 2024–25 per its own athletics notice), Mount Royal
and UQAM (no swim program found), York (unconfirmed; its swimming URL redirected
to a general page). No association membership roll was obtained, so no
university denominator exists.

No Canadian denominator exists beyond Swim Ontario's rounded "over 140
affiliated clubs" statement, which the 144-club page-data neither confirms nor
contradicts as an enumerated universe. No provincial percentage is claimed.

## Acquisition order

First fill absent school jurisdictions and major partial ones: the remaining
California sections beyond CIF Southern Section, Hawaii beyond state championship
scoring, and the remaining unimported state associations. Review all missing
states, including independent school authorities; a state's rows alone do not
make its coverage complete. In parallel, close NJCAA and full NAIA sponsorship
beyond championship qualifiers, youth YMCA/non-USAS and Masters
parent/workout-group gaps. Keep summer-only programs as supplemental metadata.
Then pursue the smaller remaining sources and reconcile duplicated/old listings.

The [source catalog](source-catalog.csv), [governing-body index](governing-bodies.csv)
and [source assertions](snapshot/programs.csv) retain facts independently of this
coverage target. Their provenance and semantics take precedence over headline
counts. Raw swimmer records and identity keys remain local.
