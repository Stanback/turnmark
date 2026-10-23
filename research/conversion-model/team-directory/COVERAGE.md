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
