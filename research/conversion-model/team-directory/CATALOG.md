# Facility and source catalog contract

This is public metadata for **local model training and evaluation**. It is reusable
research groundwork, alongside the conceptual lakehouse architecture, rather than
a plan to host swimmer profiles or meet results. The committed interchange is
CSV plus evidence manifests; DuckDB is a rebuildable query artifact. No cloud,
account, crawler or private swimmer database is needed to read these files.

## Current coverage

| Object                         | Published count | Meaning                                                                      |
| ------------------------------ | --------------: | ---------------------------------------------------------------------------- |
| Programs                       |          21,206 | Source-scoped listings, not deduplicated national teams (20,301 U.S., 900 Canadian, 5 unknown country) |
| Organizations                  |          18,531 | Separate institutional/club identities; categories can share an organization |
| Governing-body starting points |             172 | 74 without imported jurisdiction swimming lists; 98 partial imports; 11 Canadian bodies |
| Facility records               |          10,005 | Source-scoped finder locations, supplemental operator/LSC venue facts and 1,765 Canadian club-listed, approved-pool and ODRSF rows |
| Program-location links         |           8,125 | Source listing relationships (7,782 listed training locations, 343 listed club addresses); shared locations do not merge programs         |
| Separately described basins    |           1,300 | USA Swimming certified courses (948 deduplicated), LMSC (108), NVSL (102), PVS (62), HI (26), AD (20), SSL (17), PN (7), local (5), Swim Alberta approved pools (5) |
| Source access records          |             170 | Imported, discovery-only and blocked sources remain distinguishable          |
| Format contracts               |              11 | Includes explicitly unsupported candidates, not eleven implemented parsers   |

The program snapshot remains schema v2. The additive
[catalog manifest](catalog/manifest.json) is schema v1 and hashes/counts every
supplement CSV. `directory_build.py` accepts older base-only snapshots; a present
supplement must validate completely. No cross-provider names or shared pool
locations are used to merge organizations.

The separate site-access ledger currently has 16 observations across 14 origins;
these are URL/time observations, not 14 confirmed WAF deployments.

## Tables and joins

All files are UTF-8 CSV with fixed headers defined in
[directory_catalog.py](../directory_catalog.py). Blank fields mean unknown or
not supplied, never numeric zero. IDs are opaque strings; do not parse names,
courses or geography from them. Dates use ISO 8601; retrieval timestamps include
a timezone. Every evidentiary file receipt preserves its original content hash.

| File                                                     | Identity and references                                                  | Facts / interpretation                                                                                                       |
| -------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| [evidence_sources.csv](catalog/evidence_sources.csv)     | `evidence_id`; `catalog_source_id` → source catalog                      | Exact source URL, retrieval time, original SHA-256, projected scope and reuse context                                        |
| [facilities.csv](catalog/facilities.csv)                 | `facility_id`; unique `(authority, authority_id)`; evidence reference    | Source name, visitor-address claim, city/state/raw state/postcode/country, nullable coordinates and location evidence status |
| [program_facilities.csv](catalog/program_facilities.csv) | `relation_id`; program → base snapshot; facility and evidence references | Source listing key, relationship (`listed_training_location` where the source names a training pool; `listed_club_address` where it only gives the club's listed address), unknown activity, nullable effective dates |
| [pool_basins.csv](catalog/pool_basins.csv)               | `pool_id`; facility and evidence references                              | Distinct named basin, nullable dimensions, geometry notes, nullable elevation/uncertainty and explicit elevation basis       |
| [source_access.csv](catalog/source_access.csv)           | `access_id`; source-catalog reference                                    | Human entry point, observed data URL where known, HTTP method, access status, request-contract limits and collection policy  |
| [formats.csv](catalog/formats.csv)                       | `format_id`                                                              | Packaging, exact public adapter/scope where implemented, limitations and specification link where reviewed                   |
| [source_formats.csv](catalog/source_formats.csv)         | unique `(access_id, format_id)`                                          | Observed packaging versus discovery-only claims; does not imply parser support or successful collection                      |

Source URLs and hashes identify what supported the assertion. They do not grant
redistribution rights to raw source databases. Third-party material retains its
own rights and attribution; the repository's code license does not relicense it.
Public accessibility alone does not establish a training-data license.

### Location quality and publication review

The national finder cache has 4,956 facility IDs across 5,430 listings at 2,558
source organization IDs. Repeated records for each facility ID agreed on the
projected location fields; that is consistency within one response, not external
verification. This publication:

- Excludes one residential-looking facility and its listing relation.
- Withholds 35 mailing-style street/address2 values and their coordinates. Coarse
  locality/postcode remains a source assertion; it is not a pool geolocation.
- Leaves 85 unusable source coordinate pairs unknown, before overlapping mailing
  exclusions. Missing/nonfinite/out-of-range pairs and the 0/0 sentinel are not
  valid coordinates. These categories can overlap and must not be added together.
- Preserves raw state labels while normalizing `Pa` to `PA` and `Illinois (IL)`
  to `IL`. Source keys remain unchanged.
- Omits contacts, phone numbers, emails, staff/athlete rosters, raw payloads and
  private race identifiers. The address checks are a conservative publication
  screen, not a complete independent facility audit.

`source_reported_unverified` means exactly that. `mailing_address_withheld`
prevents a mailing address being mistaken for a pool, and the validator refuses
a `listed_training_location` edge onto such a facility; the 37 USA Swimming
finder edges to withheld addresses are `listed_club_address`. `operator_published` means
a facility operator supplied the fact; it does not mean Turnmark surveyed it or
that public access is available. Street-only directions are not complete postal
addresses. Keep geography unknown when the captured evidence does not establish
it, and distinguish a listed training location from a basin used for racing.

Operator facts may describe several basins at one facility. A source dimension
in yards can be represented in meters using exactly 0.9144 m/yd, with the
original measurement explained in geometry notes. Basin geometry does not
establish a historical race's course or bulkhead configuration. No basin has an
assigned elevation or dated race configuration in this supplement. Source-
specific details remain in the catalog records and evidence receipts.

The USMS nationwide supplement adds 1,528 location rows from 1,533 returned
locations, excluding five residential-looking entries. These rows have no source
facility IDs: their identities explicitly include the document hash, source club
GUID and row position. Several rows can describe one physical place; no address-
based identity merge or basin/configuration inference is performed. Its source
state labels `California`, `Colorado`, `Florida` and `Indiana` normalize to postal
codes while the original state remains in `state_raw`. The finder abbreviation
is separately preserved in affiliations and is not a unique identity key.

### Canadian locations

Canada pass 01 adds 1,765 facility rows with `country=CA` and the same evidence
discipline (see the `canada` block of the [catalog manifest](catalog/manifest.json)):

- **Swimming Canada club list** (`swimming-canada:club-list-row`, 306 rows): the
  club's listed street address, named `<club> (Swimming Canada listed address)`
  because the source has no facility name, linked to the club as
  `listed_club_address`, never as a training location. The 45 PO-box/mailing
  rows get no facility row and no edge: nothing locatable remains once the
  address is withheld, and the postal-derived province already sits on the
  organization. 21 coordinate pairs outside Canada are blanked (a 22nd belonged
  to a row without an address); province comes from the postal code, city is
  not separated from the address string.
- **Swim Ontario primary pools** (`swim-ontario:primary-pool`, 144): pool name,
  street, city and postal code; the source states "the address shown is the
  location of their primary pool"; no coordinates.
- **Swim Alberta training facilities** (`swim-alberta:training-facility`, 91)
  and **Swim Manitoba club facilities** (`swim-manitoba:club-facility`, 31):
  club-listed training locations; Alberta names carry no address or city,
  Manitoba blocks carry facility, street and city.
- **Swim Alberta approved competition pools**
  (`swim-alberta:approved-competition-pool`, 90, `operator_published` as for
  LSC venue directories): city, facility and the source's facility-rule note
  (kept in the name); 5 `pool_basins` rows only where a note names a 25 m or
  50 m course, with no lane, width or bulkhead facts.
- **Statistics Canada ODRSF v1.0** (`statcan:odrsf-v1.0`, 1,103): every record
  typed `pool` across ON, QC, MB, AB, BC and NB, including wading pools and
  water-play sites (the source facility type is kept in the name); 67 rows have
  no usable coordinates; names and cities keep the source's casing. Attribution:
  "Contains information licensed under the Open Government Licence – Canada."

### Sources, formats and reproducibility

The source atlas includes the national/LSC club discovery layers, USMS/LMSCs,
NCAA/CCS and school authorities, known local result archives and explicit gaps
such as NAIA/NJCAA and masters workout-group directories. Summer-league discovery
is optional supplemental coverage, not a priority or completeness requirement. The
[governing-body manifest](governing-bodies.manifest.json) and
[source catalog](source-catalog.csv) retain the larger coverage checklist.
A discovered source or advertised format is not an imported dataset.

The national finder's observed POST endpoint is recorded, but its exact request
body was not retained as a reviewed public replay contract. Use the public
finder UI; do not invent an API schema or promise endpoint stability. NCAA's two
category-specific response URLs and source hashes are preserved in the program
snapshot manifest. A frontend endpoint is not necessarily a supported public API.

Reusable public readers currently handle explicit CSV/TSV columns, JSON field
pointers, embedded literal JSON after one exact marker, JSONP (one exact callback
around one literal), repeated HTML elements with explicit fields/counts, ordinary
HTML tables and strict layout-text rows. SDIF's public helper
projects only the B1 venue/altitude header; the private finish collector is not
part of this public catalog. ZIP is a container, not a result schema. LENEX and
proprietary HY-TEK exports are recorded as future adapter/review work, and XLSX
as a discovered source, without claiming an implemented importer.

Source-specific collectors remain local. A contributor should be able to trace a
published fact through its source key, evidence URL/time/hash and reviewed field
mapping, without needing any swimmer data. Regenerating from the public CSVs is
fully supported; reacquiring a source still requires its own reviewed access
route, source terms and mapping. This repository does not yet provide a one-step
national harvest command.

## Query locally

```sh
python3 research/conversion-model/directory_catalog.py validate \
  research/conversion-model/team-directory/catalog

target/lakehouse-venv/bin/python research/conversion-model/directory_build.py \
  --output target/swim-directory.duckdb
```

The builder verifies schemas, hashes, counts, unique IDs, evidence and foreign
keys before publishing a fresh database. Tables are loaded as strings to preserve
source IDs and unknowns; cast numeric facts explicitly when analyzing them.
Useful queries in DuckDB opened on that output:

```sql
-- Source-backed team → training-location listings, without swimmer tables.
SELECT organization_name, facility_name, city, state, location_status
FROM program_locations
WHERE program_kind = 'masters' AND state = 'CO'
ORDER BY organization_name, facility_name;

-- Access barriers and missing adapters stay visible.
SELECT catalog_source_id, access_status, format_name, public_adapter
FROM source_format_access ORDER BY catalog_source_id, format_name;

-- A physical basin is a separate evidence layer.
SELECT f.name AS facility, b.name AS basin, b.length_m, b.width_m,
       b.elevation_m, b.elevation_basis, e.source_url
FROM pool_basins b JOIN facilities f USING (facility_id)
JOIN evidence_sources e ON b.evidence_id=e.evidence_id;
```

`program_location_coverage` counts each source-scoped program once and exposes
missing location links, even when one club has many finder listings.
`facility_coverage` summarizes source-scoped location/coordinate coverage. Counts
are not a national facility denominator. `program_locations` can contain several
source listing assertions for the same program/facility; retain the underlying
relation IDs instead of assuming every row is a unique physical place.

## Contribute and evaluate

Start with the official program/operator/league source and record its URL,
retrieval date, content SHA-256, geographic/seasonal scope and reuse context.
Project only the fixed metadata columns. Keep street directions, mailing
addresses, source-reported coordinates and independently reviewed coordinates
distinct. Do not merge names or short codes; propose cross-source equivalences
with specific evidence. A facility may host many clubs and multiple basins.

For the normalized supplement, `directory_catalog.py export facts.json --output
<fresh-directory>` accepts a JSON object with exactly `tables` and `review` keys.
`tables` contains all seven fixed-schema arrays (empty where appropriate); every
row includes every declared column as a string, using `""` for unknown. The
exporter validates the allowlist and references, sorts deterministically, writes
CSV/hash receipts and verifies its output. It rejects unexpected contact columns,
invalid geometry/coordinates and missing evidence. The base directory builder
also checks program/source references across the two snapshots. Add invented
fixtures for a new format or contract and preserve source attribution.

For training, use this catalog to prioritize missing regions/programs/archives
and review candidate venues. A program's listed pool does **not** establish
where its swimmers raced. A raw same-pool cohort still needs an explicit meet
and basin/configuration mapping, dates, course and clock basis through the
[venue sidecar](../../../docs/VENUE_RESEARCH.md). Do not derive altitude from a
city centroid or apply an official adjustment to raw training labels silently.
Five million races, thousands of facilities or a complete source response does
not establish balanced labels or national coverage.

The next acquisition priorities remain sport-specific school participation
in remaining unimported state jurisdictions, reconciliation of nationwide masters listings
with registered clubs/workout groups, NJCAA and full NAIA membership directories, YMCA/independent programs and
middle-school leagues where published. Summer leagues are opportunistic extras.
Record published denominators and unresolved rows per jurisdiction/season before
claiming completeness. Expand the private race corpus after that source mapping,
then create balanced training views with swimmer-disjoint and later-season
holdouts. This pass adds metadata, not races or a trained model.

## Access observations

The separate [site-access ledger](site-access-reviews.csv) is additive, not a
replacement for authority-homepage transport or swimming-directory coverage. Its
[manifest](site-access-reviews.manifest.json) hashes/counts the fixed CSV fields
validated by [access_signals.py](../access_signals.py). The public DuckDB adds
`site_access_reviews` when this manifest is present; older snapshots remain
readable. It records origin, exact reviewed public URL, observed time/status,
fixed evidence codes, unknown versus observed provider/challenge state, evidence
kind, nullable original body hash and separate browser-review disposition.
Historical status-only receipts cannot establish a provider or body hash.

The classifier accepts only minimal response signals and never publishes header
values, cookies or page text. Cloudflare's
[documented challenge header](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/)
is a challenge observation, not proof of a particular WAF rule or product. CDN
presence, 403 status, observed challenges and verified browser access remain
separate facts. Protection can vary by URL and time; no “WAF absent” claim is made.
