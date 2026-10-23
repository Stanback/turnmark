# United States swim-team registry experiment

Build out the source-backed organizational directory first, then grow the private
dataset toward **five million deduplicated actual individual races across U.S.
regions**, with cohort balancing after acquisition. The directory targets
age-group, masters, college varsity, college club, high-school, summer-league
and other swimming programs. This is local research, not a public results
service. Full national team coverage has not been achieved or verified.

## Format and identity

The executable [DuckDB schema](../research/conversion-model/team-registry.sql)
keeps organizations, programs, affiliations, aliases, evidence and source
observations separate. Create a fresh local database with that SQL, import
reviewed source records, and query `team_directory`. Export each table as
Parquet or JSONL for versioned interchange. Generate the human-readable
directory from `team_directory`; do not maintain a giant hand-edited Markdown
list independently of its data.

A school may operate women's and men's varsity programs plus a separate college
club. A club can offer youth and masters programs. YMCA is an affiliation, not a
mutually exclusive age category. Governing-body codes are namespaced and may
change or be reused over time. Use stable internal IDs with source-ID mappings,
effective dates and evidence. Do not automatically merge similar names, the same
short abbreviation or teams sharing a pool.

`team_observations` retains team names/codes found in historical result exports.
These are candidates, not proof of current membership, location or an active
program. Only a reviewed mapping connects an observation to a canonical program.
Preserve unknowns, inactive programs, renames and aliases. Unattached swimmers,
all-star selections and temporary composite teams must not silently become
ordinary permanent clubs. No athlete/coach roster, personal contact directory
or full birth date belongs in these organizational tables.

The schema records source URLs, retrieval timestamps, content hashes and reuse
notes. `last_verified` and effective dates are different: seeing a team name in
a 2024 result in 2026 does not establish that the team is active in 2026.

## Source map and completeness

| Segment                               | Starting authoritative sources                                                                                                                     | Coverage cautions                                                                                            |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Age-group clubs                       | [USA Swimming team services](https://www.usaswimming.org/coaches/popular-resources/team-services), Find-a-Team and individual LSC club directories | Confirm official codes and seasons; club directories do not cover every summer league or independent program |
| Masters                               | [USMS Club Central](https://www.usms.org/club-central) and [Club Finder](https://lanemate.usms.org/clubfinder)                                     | Member/affiliate clubs and workout groups differ; several practice locations need not mean several clubs     |
| College varsity                       | [NCAA directory](https://www.ncaa.org/about-us/membership-directory/), plus NAIA/NJCAA and school athletics sources                                | Institution membership does not prove swimming sponsorship; verify program, category, division and season    |
| College club                          | College Club Swimming and school recreation/club directories                                                                                       | Keep separate from varsity and USMS affiliations even when the parent school matches                         |
| High school                           | [NFHS state-association directory](https://nfhs.org/about/state-association-directory), state athletic associations and school athletics sites     | There is no verified single complete swimming-team export here; school membership alone is insufficient      |
| Summer leagues / independent programs | Official league/team directories and host result archives                                                                                          | Track the league and season; do not infer USA Swimming membership from attendance at a meet                  |

No source adapter or public directory is asserted complete merely because its
first page was imported. Maintain a coverage ledger by segment, state/LSC,
season, expected-source universe where known, fetched pages, verified programs,
unmapped observations and freshness. Unsupported access or missing exports are
visible gaps. Raw source payloads and swimmer-level records stay local. The [public directory snapshot](../research/conversion-model/team-directory/README.md)
publishes a reviewed projection of organizational facts from 142 directory
sources (`15,073` program listings across `12,906` source-scoped organizations and
`16,431` affiliations), alongside `7,597` facility rows and `997` separately described
competition basins, with attribution and
explicit unknown activity status. It excludes raw payloads, contacts, rosters
and historical meet-file observations.

The current private race pilot began with Pacific Swimming. Reviewed public ZIP
sources in Potomac Valley and Midwestern Swimming also parse through the SDIF
adapter, and regional collection is being expanded. Region in these initial
exports identifies the **archive source**, not every swimmer's home location.
Check geographic breadth independently before claiming a national sample.

For the five-million-race target, count actual individual rounds once by logical race
identity. Do not count raw URLs, duplicate exports, seeds, relay splits or
invalid finishes as races. Count unique swimmers/meets and useful nearby-date
cross-course pairs too. Report performance/age/category/course/season coverage;
large championships alone would create a biased dataset. A large count is a
collection milestone, not model validation.

## Optional graph layer

The public directory snapshot exports `15,073` program listings across `12,906`
source-scoped organizations and `16,431` affiliations from `142` governing-body
sources as CSV with source hashes, URLs and listing dates. Separate
`organizations.csv`, `programs.csv` and `affiliations.csv` files, plus companion
facility and source-catalog tables under `catalog/`, rebuild a local queryable
DuckDB via `directory_build.py`, with file hashes, unique identities and
references checked. Shared website URLs are review candidates, not entity
merges. It does not include raw snapshots or historical meet-file observations.
Activity statuses remain unknown unless explicitly stated by the source; no
complete national census is claimed. The
[directory expansion plan](../research/conversion-model/DIRECTORY_PLAN.md)
tracks remaining segments and the later private race-collection phase.

The schema includes `registry_vertices` and `registry_edges` views over the same
tables. Useful graph questions might concern programs sharing organizations,
affiliations across time, common meet participation and gaps in regional
coverage. Most initial directory filters and joins remain ordinary SQL.

[PuppyGraph supports a persistent DuckDB file](https://docs.puppygraph.com/connecting/connecting-to-duckdb/),
but its JDBC driver must match the file version, and another process cannot
write that file while it is being read. Give a future graph experiment an
immutable snapshot, not the collector's live database. Its [free Developer
Edition](https://www.puppygraph.com/pricing) is a single-node Docker prototype;
production licensing/hosting is a separate decision. None is installed or
deployed by this experiment.

[DuckPGQ](https://duckdb.org/docs/current/guides/sql_features/graph_queries)
offers SQL/PGQ, but the current docs require DuckDB 1.4.4 and explicitly warn that
it is unavailable for 1.5.x. The lakehouse is pinned to 1.5.6. Benchmark it in a
separate environment if needed; do not downgrade the working lakehouse or imply
the extension already runs here. Compare a few real queries against SQL first.
Keep graph projections disposable and the organizational tables authoritative.
