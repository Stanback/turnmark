# Local meet archive and inexpensive query architecture

Design checked October 19, 2026. This is a research prototype, not a deployed
service or a change to Turnmark's offline product. The source-specific collector,
raw files, pseudonymous race records, query databases and identity key remain
gitignored. The generic query tools and invented tests can be published under
this repository's license. No cloud resources or paid plans have been enabled.

Actual scope is local data preparation, querying, conversion-model evaluation
and training. The hosted counterparts below are a public conceptual architecture:
what a Turnmark-hosted meet-results service could look like. Building or operating
that service is an explicit project anti-goal. These notes preserve the reasoning
for interested readers and for any deliberate future reconsideration of that
boundary; they do not put a hosted service or cloud migration on the roadmap.

The [storage and serving principles](WAREHOUSE_COST_COMPARISON.md#storage-and-serving-principles)
are shared across the hypothetical backend alternatives: retain originals and
provenance, choose one canonical store, publish rebuildable versioned objects,
keep directory indexes small and serve profiles without per-page lake scans.
The comparison covers DuckDB/R2, BigQuery, Snowflake and Athena/S3; Athena keeps
the canonical lake in S3 and exports changed serving objects to the common edge.

## Recommendation

Use DuckDB as the research engine. Keep durable history in compressed Parquet,
with Iceberg metadata when versioned tables and engine interoperability are
useful. In the hypothetical hosted counterpart, use R2 for objects and D1 only for ingestion state and
small, indexed serving projections. Precompute common public pages. Start with
one D1 database; add shards after measuring its storage and query pressure.

This is a practical 2026 architecture that can grow into 2027, not a prediction
about unannounced products. The useful modern part is open table storage with
independently replaceable compute and no idle query cluster. Trino is an option
if sustained concurrency or federated joins justify operating it later.

USA Swimming does use Snowflake-backed dashboard models, according to its
[February 2026 release notes](https://www.usaswimming.org/docs/default-source/technology/technical-release-notes/technical-release-notes-february-4-2026.pdf?sfvrsn=d5d21e32_1),
pages 4–5. Its membership, identity and reporting platform has a broader workload
than this experiment. Those notes establish neither the cost of that system nor
direct public warehouse access.

## Three tiers

| Tier          | Local experiment                                                     | Possible production counterpart                                           | Purpose                                                                          |
| ------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Cold archive  | Private cached original ZIPs plus checksums and source manifests     | Private R2 objects keyed by content hash                                  | Reparse, trace corrections and recover from a source disappearing                |
| Warm analysis | Partitioned Zstandard Parquet, real Iceberg v2 snapshots, DuckDB SQL | R2 + managed Iceberg catalog; DuckDB on demand or managed scan-priced SQL | Cohort audits, race matching, baseline evaluation, later model training          |
| Hot serving   | Indexed SQLite projection checked against the snapshot               | D1 + cached versioned responses/JSON objects                              | Meet directory, bounded history lookups, ingestion status and selected summaries |

“Cold” describes its role, not necessarily the R2 Infrequent Access billing
class. Standard is the starting point: IA saves storage but adds retrieval fees,
higher operation rates, a minimum retention period and no Standard free tier.
Frequently rescanning a small archive can erase the storage saving.

The lake is the historical source of truth; serving databases are rebuildable.
Do not copy every historical fact into every layer. Some immutable meet pages
could be compressed JSON objects fetched by exact key, with only their directory
in D1. Public caches are only appropriate for data deliberately approved for
publication; the research dataset is private.

## What actually runs locally

[`lakehouse.py`](../research/conversion-model/lakehouse.py) accepts the normalized
CSV and provenance manifest. It validates actual finishes, rejects conflicting
identities and invalid values, deduplicates identical races, sorts the data and
writes an Iceberg table partitioned by year/course. It creates:

- A local PyIceberg SQLite catalog and committed Parquet/metadata files.
- A DuckDB database with an `races` view reading the exact committed Iceberg
  metadata, plus a `parquet_snapshot` reference view of that snapshot's active
  files. Full multiset equality verifies the two reads.
- A separate SQLite hot projection. Swimmer, meet and event keys are stored once
  in dimension tables, and the race table's athlete-history and meet-results
  indexes hold only integers. `lakehouse.py rebuild-hot` replaces it from the
  committed snapshot.
- A private snapshot manifest with source hash, versions and snapshot ID, written
  last. An incomplete build has no published manifest. Existing outputs are
  never overwritten.
- An aggregate-only probe that executes cohort SQL, checks indexed history
  against Iceberg, verifies the index plan and records local timings/sizes.

The snapshot is pinned through the catalog's committed metadata path. Never
guess “latest” from filenames or glob an Iceberg data directory: obsolete files
and delete semantics can make those reads wrong. A synthetic test appends a new
catalog snapshot and verifies that the frozen research view stays unchanged.

The initial measured checkpoint contained 60,962 races from 44 meets and 7,550
source-scoped swimmers, across 2024–2026. Parquet occupied 2,941,992 bytes; the
deliberately straightforward full-history SQLite projection occupied 46,747,648
bytes including indexes: about 48 versus 767 bytes/race. These are observations
of one schema and sample, not a storage guarantee. Repeated source values,
64-character keys, larger batches and different indexes change the ratio.
These first checkpoints predate the optional archive/cohort columns, which now
remain available for regional audits and provenance queries.

A second checkpoint of 106,053 races occupied 5,025,874 bytes in Parquet and
81,518,592 bytes in the same SQLite projection. It yielded 614 matched pairs
under the pilot's 30-day policy, with 57 independent test swimmers. This improves
the pilot's coverage but still does not justify a general predictive claim.

On the national checkpoint (8,506,767 races), the straightforward layout used in
those pilots took 6,915,502,080 bytes, about 813 bytes/race, because every
64-character key was repeated in the table and in each index. The current layout
takes 1,101,565,952 bytes, about 129 bytes/race; the remaining bulk is the race
ID stored once per row. Warm single-swimmer history lookups stay around 0.02 ms
locally.

The indexed query and Iceberg results agree. Millisecond local timings are
warm-cache laptop measurements, **not** D1/R2 latency, throughput or cost
benchmarks. The current importer materializes one bounded snapshot in memory
(default maximum one million unique rows); a national ingest needs streaming
batches, resource limits and incremental commits. No cloud REST catalog, R2
upload, D1 deployment, production correction workflow or trained model is wired.

## Object layout and updates

Archive originals once by SHA-256, with a separate URL/retrieval/version ledger.
Keep parser versions and each race's source linkage. A missing export is an
explicit gap, not a zero-result meet. Parse/replay cached files without
refetching, and enforce persistent per-origin pacing, byte/request budgets and
backoff.

Batch normalized output by coarse year/course partitions. Start with files in
the tens to hundreds of MB when enough data exists, then tune from scanned-byte
and file-count measurements. Do not partition by swimmer or write one tiny file
per race. Sort within batches for common date/event/athlete filters; inspect
query plans rather than assuming pruning works. Small pilot partitions are
expected to be smaller than production targets.

Corrections create a new source version and a reviewed logical-race replacement
or tombstone, then a new table snapshot. Preserve enough provenance to explain
the change. Never resolve a conflict by silently choosing the faster time. Build
serving projections with a snapshot/version marker and publish only after
verification; retries must be idempotent. Keep old metadata/data until readers
and reproducibility retention no longer need it, then expire snapshots and clean
orphans deliberately. Replicate/back up raw files separately if archival survival
matters; an inexpensive single copy is not an archival strategy by itself.

## D1 and sharding

The [current D1 limits](https://developers.cloudflare.com/d1/platform/limits/)
are 500 MB/database on Free and 10 GB/database on Paid. The national hot projection (1.10 GB) fits one Paid database. Each database processes
queries serially. Good indexes, short queries, bounded pagination and caching
come before sharding. The prototype's ordinary SQLite SQL is a portability
starting point, not proof that a D1 workload will fit its execution limits.

If a measured hot projection approaches a size/throughput budget, route athlete
history by a stable athlete-hash bucket with an explicit routing map/version.
Avoid `hash % current_shard_count` without a migration plan. Keep a small global
directory and put meet-oriented materializations in their own access path;
athlete sharding alone does not solve meet/search queries. Avoid cross-shard
fan-out for every page. Run global analytics against the lake. A narrower recent
history projection or exact-key R2 history objects may avoid sharding entirely.

For a future API, parameterize bounded queries and expose specific operations,
not arbitrary public SQL. Cache by dataset snapshot plus filter. Measure rows
read/written and queue pressure. Source corrections must invalidate the relevant
versions. Add a queue/workflow only when it earns its ingestion/retry complexity;
meet archives do not require a streaming pipeline by default.

## Costs and the managed Cloudflare option

The [adjustable cost model](LAKEHOUSE_COST_MODEL.md) compares prebuilt R2/KV
responses with per-request lake scans. A serving database is optional for a
finite set of precomputed pages; flexible search/faceting needs a bounded index
or a measured analytical-query path. KV is not a general query engine.

Cloudflare's current docs call the former R2 Data Catalog/R2 SQL products
**Basin Catalog/Basin SQL**. The catalog supports Iceberg engines including
[DuckDB](https://developers.cloudflare.com/basin-catalog/). It is a future hosted
option; local PyIceberg catalog files cannot simply be uploaded and treated as
a managed catalog migration.

The [cross-vendor review](WAREHOUSE_COST_COMPARISON.md#the-four-options-on-the-same-iceberg-workload)
now prices external Iceberg/Parquet across all four readers: Basin/R2,
Athena/S3, BigQuery/GCS and read-only Snowflake/R2. They share one workload and
the same external writer allowance. Managed-table variants change maintenance
ownership and remain outside those totals.

([MotherDuck](https://motherduck.com/product/ducklake/) is another managed
DuckDB/lakehouse option, with a managed DuckLake offering. It belongs in the same
broad alternatives discussion but is not priced, benchmarked or analyzed here.)

Rates checked October 19, 2026; allowances are shared account usage, not per
experiment. Estimates exclude taxes and the cost of the ingestion/training host.

| Component                                                                          | Current public pricing relevant here                                                                                                                                      |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [R2 Standard](https://developers.cloudflare.com/r2/pricing/)                       | $0.015/GB-month; 10 GB included; $4.50/million Class A and $0.36/million Class B, with 1m/10m included; no egress charge. Billing-unit rounding applies.                  |
| [Basin SQL](https://developers.cloudflare.com/basin-sql/platform/pricing/)         | $0.0025/GB of compressed data scanned, 10 GB/month included; minimum 10 MB/query. R2/catalog charges are additional.                                                      |
| [Basin Catalog](https://developers.cloudflare.com/basin-catalog/platform/pricing/) | 1m catalog operations included, then $9/million. Optional compaction: 10 GB and 1m objects included, then $0.005/GB and $2/million objects processed.                     |
| [D1 Paid](https://developers.cloudflare.com/d1/platform/pricing/)                  | 5 GB included, then $0.75/GB-month; 25b rows read and 50m written included/month, then $0.001/million read and $1/million written. Index maintenance also affects writes. |
| [Workers Paid](https://developers.cloudflare.com/workers/platform/pricing/)        | $5/month minimum; includes 10m requests and 30m CPU-ms. No plan change is authorized by this proposal.                                                                    |

For illustration, **100 GB total R2 storage + 1 TB of SQL scans/month + a 2 GB
D1 projection** would cost roughly **$8.83/month** including the $5 Workers
minimum, assuming all operations, D1 rows, Worker requests/CPU and catalog usage
stay within their included amounts, no paid compaction, and no other account
usage consumes allowances. Storage contributes $1.35 and scans about $2.48.
This is a workload scenario, not a quote or a measurement of future traffic.

The trap is repeated scanning, not the existence of a lakehouse: a million
uncached queries each scanning 1 GB imply roughly $2,500 in SQL scan charges
alone. A `LIMIT` on returned rows is not a scanned-byte budget. Keep analysis
off the per-page serving path, precompute common summaries, use selective
columns/partition filters, inspect `EXPLAIN`, and enforce application-level
query/rate budgets. Managed SQL is [read-only and has query limitations](https://developers.cloudflare.com/basin-sql/reference/limitations-best-practices/);
the offline writer still owns ingest and corrections.

## DuckLake, Iceberg and Trino

[DuckLake reached v1.0 in April 2026](https://duckdb.org/2026/04/13/ducklake-10).
It is a serious alternative for a DuckDB-centric pipeline: Parquet plus table
metadata in a transactional SQL catalog. Its [catalog choices](https://ducklake.select/docs/stable/duckdb/usage/choosing_a_catalog_database)
include local DuckDB/SQLite and PostgreSQL for different concurrency needs.
Shared Parquet compatibility does not make DuckLake and Iceberg catalog metadata
interchangeable or make Basin SQL query a DuckLake catalog directly.

Use Iceberg for this first experiment because it tests the managed Cloudflare
catalog/query path while retaining DuckDB locally. A DuckLake comparison is a
useful later benchmark, not a reason to maintain two authoritative lakes now.
D1's SQLite ancestry does not make its HTTP API a supported drop-in DuckLake
catalog connection. Building an adapter would add work before serving a need.

Do not run Trino continuously just to query an occasional few-GB dataset. Add
distributed compute if measured concurrent workloads exceed a bounded DuckDB
process or a managed query's capabilities. Keep queries portable where useful,
but test engine-specific functions and Iceberg features explicitly.

## Next evidence to collect

1. Broaden public meet exports across regions and levels; audit missing age,
   identity and event cells. A Pacific-heavy pilot is not nationally balanced.
2. Measure the number of independent close-date cross-course pairs, not just
   raw races. The 60,962-race checkpoint produced only 134 eligible pairs within
   30 days; it is not enough for a claimed general prediction model.
3. Test incremental corrections, replay, compaction, snapshot retention and hot
   projection recovery with invented records before any hosted service.
4. Keep the hypothetical hosted benchmark suite and its cost assumptions public
   for interested readers. This local research does not schedule R2/catalog/D1
   trials. Source-specific adapters and real data remain outside the public PR.

The broader collection target is now one to two million actual races across U.S.
regions. The [team registry experiment](TEAM_REGISTRY.md) records the directory
schema, source coverage and optional graph-layer evaluation alongside that work.
