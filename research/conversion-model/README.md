# Offline conversion-model pilot

This folder is an experiment, not a deployed conversion method. Read the
[research review](../../docs/CONVERSION_RESEARCH.md) before collecting data or
interpreting metrics. No real swimmer dataset is included.

Collection, querying, evaluation and model training stay local. Generic tools and
invented fixtures are public; source-specific collectors and real datasets remain
gitignored. Operating a hosted meet-results aggregator, running a national search
service and migrating Turnmark to a cloud backend are explicit project anti-goals.
The public architecture and cost model explore what such a hypothetical service could
look like, preserving the reasoning should that boundary ever be deliberately
reconsidered. They are reference material, not deployment plans or roadmap
commitments.

The [collection objective](DIRECTORY_PLAN.md)
is a reusable national data foundation for research and a possible future
results/standards site. Keep the general archive and derive the narrow model
pilot from it. Report source, region, program, course and historical coverage
alongside the broader race-acquisition target; volume alone is not completeness.
This preserves future options without committing to a hosted product.

The [result-source review](RESULT_SOURCES.md) records confirmed acquisition
workflows, federation API limits and qualified regional archive leads. Candidate
export counts there are separate from accepted races in the frozen checkpoints.

The initial import accepts normalized CSV actual individual results with these
columns:

```csv
source,race_id,swimmer_id,meet_id,date,course,distance,stroke,category,time_cs,status,age_years
synthetic,y1,toy-1,toy-y,2026-01-01,SCY,100,freestyle,women,5832,OK,15
synthetic,m1,toy-1,toy-m,2026-01-15,LCM,100,freestyle,women,6672,OK,15
```

Those two rows are invented format examples, not observations. `source` and
`swimmer_id` together identify a swimmer within one provider; `race_id` must be
unique within the source. Do not merge different providers by name. `time_cs`
is integer centiseconds, not a decimal seconds string. Dates are ISO dates.
`age_years` may be blank; preserve the source's actual precision. Use whole ages
when only whole ages are known. No name, full birth date or location is required.
`status=OK` means a valid individual actual finish; relay/split records must be
excluded by the source adapter. SCM, non-freestyle and distances outside
50/100/200 are deliberately outside this first pilot.

Supply a dataset manifest alongside an export you can use:

```json
{
  "source_url": "source URL or local synthetic fixture description",
  "retrieved": "2026-10-19",
  "reuse_notes": "Describe the export's provenance and permitted use",
  "age_precision": "whole years at race date",
  "synthetic": true
}
```

Keep raw exports, manifests, prepared datasets and models under ignored
`target/conversion-research/` or outside the repository. Do not commit real
swimmer-level data. The importer has no network or account access.

```sh
python3 -m unittest discover -s research/conversion-model -v
python3 research/conversion-model/pipeline.py /path/to/results.csv \
  --manifest /path/to/manifest.json --output target/conversion-research/pilot
```

The importer rejects conflicting IDs and malformed eligible results, reports
exclusions and deduplicates identical records. It greedily matches nearest-date
SCY/LCM swims within 30 days, once per race. Pairing is deterministic, including
ties. It freezes a 70/15/15 swimmer-hash split; repeated races and event distances
for one swimmer cannot cross partitions. Percentages are expected proportions,
not guarantees for small datasets. It is a **swimmer holdout**, not yet the
separate future-meet evaluation required before production claims.

The report records input SHA-256, provenance, cohort sizes and
`validated_for_product: false`. A synthetic run proves plumbing only. No
accuracy claim, calibrated interval, source-specific scraper or client runtime
model follows from preparing this dataset.

## Published comparison examples

[Swimulator's four January 2018 examples](references/swimulator-2018.json) are
source-attributed comparison cases, separate from the race importer and its
held-out labels. They preserve the published outputs and missing age settings;
these outputs are not observed second swims or required results of our methods.
The [research review](../../docs/CONVERSION_RESEARCH.md#distribution-matching-prior-art)
places them beside the Vercruysse analysis and explains their limited role.

## Coverage audit

`audit.py` reports unique swimmers/meets and course, event, age, category, year
and region coverage. Zero cells stay visible. Its output contains aggregate
counts, not athlete identifiers. It can also summarize the private pairs file:

```sh
python3 research/conversion-model/audit.py /path/to/results.csv \
  --pairs target/conversion-research/pilot/pairs.json \
  --output target/conversion-research/pilot/coverage.json
```

The source-specific collector is deliberately local under ignored `local/`.
Real data belongs in ignored `data/`, `artifacts/`, `target/`, or outside this
checkout. Neither raw files nor pseudonymous per-race exports belong in commits,
CI artifacts or app bundles. A local pilot now exists; none is included here.

## Production budget and historical retention

The [production budget](../../docs/WAREHOUSE_COST_COMPARISON.md) leads with an
end-to-end 20–30-year archive scenario, ingestion, hot/warm/cold storage and
an all-Iceberg comparison of Basin/R2, Athena/S3, BigQuery external Iceberg/GCS
and read-only Snowflake/R2. Every option includes the same external writer and
retention; provider-specific scan/runtime, catalog and export charges are separate.
It states the shared
storage and serving principles: one canonical dataset, rebuildable bounded
objects, cached profile reads and a small directory index. Reproduce its line items:

```sh
python3 research/conversion-model/production_budget.py
```

Rates are public list prices. Collector/batch/export amounts are explicit
spending allowances, not measured hosted throughput or vendor quotes. The
existing `cost_model.py` remains a separate cache/scan stress comparison.

## Optional DuckDB / Iceberg experiment

See the [architecture and cost review](../../docs/MEET_LAKEHOUSE_EXPERIMENT.md).
The [monthly cost model](../../docs/LAKEHOUSE_COST_MODEL.md) compares cached
objects, KV and managed lake scans with explicit hypothetical workloads:

```sh
python3 research/conversion-model/cost_model.py --requests 1000000 --cache-hit 0.95
```

This installs only into an ignored virtual environment. Python 3.12 is the
dependency-lock/CI target; the initial local check also ran on Python 3.14.

```sh
python3.12 -m venv target/lakehouse-venv
target/lakehouse-venv/bin/pip install --require-hashes \
  -r research/conversion-model/requirements-lakehouse.lock
target/lakehouse-venv/bin/python -c \
  "import duckdb; duckdb.connect().execute('INSTALL iceberg')"
TURNMARK_LAKEHOUSE_TESTS=1 target/lakehouse-venv/bin/python \
  -m unittest discover -s research/conversion-model -v
target/lakehouse-venv/bin/python research/conversion-model/lakehouse.py build \
  /path/to/results.csv --manifest /path/to/manifest.json \
  --output target/conversion-research/lakehouse-01
target/lakehouse-venv/bin/python research/conversion-model/lakehouse.py probe \
  target/conversion-research/lakehouse-01
```

The extension download happens explicitly during setup; the tests use invented
records without fetching meet data. Default stdlib tests skip the optional
lakehouse tests unless `TURNMARK_LAKEHOUSE_TESTS=1` is set. The requirements input
pins direct dependencies and the generated lock pins/hashes transitive ones.

Open `queries.duckdb` with the same DuckDB version to use SQL directly:

```sql
LOAD iceberg;
SELECT year, course, category, count(*) AS races
FROM races
WHERE year = 2026 AND course IN ('SCY', 'LCM')
GROUP BY ALL
ORDER BY year, course, category;
```

The database views pin a committed Iceberg metadata file; the local catalog and
warehouse use absolute paths. Keep the output directory in place, or rebuild at
its new location. Creating a fresh output directory produces a new snapshot;
there is no destructive overwrite switch. The importer has a one-million-row
default memory guard. This is a functional local experiment, not a national-scale
streaming ingester or a benchmark of hosted D1/R2. No cloud configuration,
credentials, upload or paid service is used.

Optional `region`, `meet_class`, `round`, `archive_id` and `date_precision` columns
are retained in the lake. Missing context stays null; archive region is not
automatically a swimmer's home region.

The [latest acquisition receipt](acquisition-checkpoint-06.json) records
6,320,277 actual individual finishes, 213,105 source-scoped swimmers and 4,721 meets
across 13 regional and national archives (from 11 frozen export collections).
The [aggregate evaluation receipt](evaluation-checkpoint-06.json) (`evaluate_and_train.py`)
runs best-of-meet round deduplication, hygiene screening, composite sample weighting
($w_{\text{swimmer}} \cdot w_{\text{region}} \cdot w_{\text{cohort}} \cdot w_{\text{gap}}$
fitted on Train only), and directional apples-to-apples comparisons across 176,306 clean
30-day directional pairs (from 21,970 swimmers) spanning
swimmer-disjoint (70/15/15), temporal (`<= 2025` vs `2026`) and leave-regions-out holdouts;
see [REPORT.md](REPORT.md) for the full methodology and holdout tables.

## Organizational directory

The [team-registry schema](team-registry.sql) and [source/graph review](../../docs/TEAM_REGISTRY.md)
define a DuckDB directory for organizations, programs, affiliations, aliases and
evidence. Build the directory first, then grow the private race corpus toward
five million as the next checkpoint, then a coverage-led 10–30 million actual
individual races across U.S. regions and balance training
cohorts after acquisition. Track organizational and race coverage separately.
The
[public research catalog](team-directory/README.md) now publishes 20,306 source-scoped
programs at 17,697 source-scoped organizations with provenance. The
[facility/source supplement](team-directory/CATALOG.md) adds 8,240 facility records,
7,497 program-location links, 1,295 separately described competition basins and a source/format
index. It excludes contacts, rosters, raw source payloads and historical observations. Activity and national completeness are
unverified. `directory_build.py` builds a queryable local DuckDB from only the
public CSVs; raw collector payloads and all swimmer-level data remain local.

```python
from pathlib import Path
import duckdb

with duckdb.connect("target/conversion-research/registry.duckdb") as db:
    db.execute(Path("research/conversion-model/team-registry.sql").read_text())
```

Use a fresh path. Reviewed source importers populate those tables; historical
meet-file appearances remain observations until mapped. The `team_directory`
view is suitable for readable exports. `registry_vertices`/`registry_edges` are
optional graph projections, not a running PuppyGraph or DuckPGQ service. The
synthetic tests check multi-program organizations, affiliations, evidence
constraints and the difference between observations and verified entries.

## Venue and altitude cohorts

[The venue research guide](../../docs/VENUE_RESEARCH.md) describes the implemented
local `venues.py` sidecar, strict `venue-registry.sql` schema and wholly invented
fixture. Facilities, physical basins, dated SCY/SCM/LCM configurations and explicit
source/race mappings are separate. Unknown elevations stay null; adjusted or
unknown-basis clocks cannot qualify as raw same-pool pairs.

The audit annotates existing pairs and reports same-pool, same-facility/different-
pool, different-facility and unresolved cohorts without changing times or frozen
partitions. It also produces a private meet-level evidence queue. The checkpoint-03
replay has 5,687 pairs across 215 meets; with no reviewed venue mappings supplied,
all remain unresolved. That is a linkage-coverage result, not proof that venue
information is absent from the source files. No altitude model is trained.

A cache-only header pass found evidence candidates for all 215 paired meets:
28 report nonzero altitude, 186 report zero and one is blank. These are unverified
SDIF source claims, not pool measurements or training features. `sdif_venue.py`
provides the reusable B1 header projection; the private source-specific replay
and detailed queue stay ignored. No new network fetches were needed.
