# Production budget: query engines over an Iceberg swim archive

**Public architecture reference, not a Turnmark deployment plan.** This document
explores how a hypothetical Turnmark-hosted meet-results service could store,
query and serve historical races. Building or operating that service is an
explicit project anti-goal.

The architecture and cost model are published for curious readers and to preserve
the reasoning should that scope boundary ever be deliberately reconsidered. They
are not a roadmap commitment. Turnmark's actual research stays local, focused on
conversion-model evaluation and training.

**For 30 years of history, 600m races, 20m new races/year and 10m API requests/month,
the worked Iceberg cases are about $120–225/month.** A $100–250/month planning
budget remains a useful starting allowance, subject to measured throughput.
The preferred R2/Basin case is about $120, including a $60 writer allowance;
its retained storage is about $25/month. Prices checked October 19, 2026.

## The four options, on the same Iceberg workload

Keep the same Iceberg v2 dataset, Parquet schema/layout, selected columns,
filters, results, retention, ingestion cadence and cached serving behavior.
Use each engine's supported regional object storage and catalog. This is an
architecture-equivalent comparison; native billing meters and actual performance
still differ. No hosted workload has been benchmarked or deployed.

| Query engine and canonical lake                        | Worked monthly whole-service amount | What remains conditional                                                            |
| ------------------------------------------------------ | ----------------------------------: | ----------------------------------------------------------------------------------- |
| Basin SQL + R2, with a DuckDB writer                   |                      **about $120** | Compressed scans; includes $60 batch writing, unmeasured throughput                 |
| Athena SQL + S3 Standard                               |                      **about $130** | Compressed scans, S3 operations/results and bounded exports                         |
| BigQuery on-demand + external Iceberg in Cloud Storage |                      **about $139** | Logical query-byte estimate, GCS operations/catalog and bounded exports             |
| Snowflake Standard reading R2/Basin Iceberg            |                  **about $165–225** | External writer plus 20–50 XS-equivalent billed **query** hours; runtime unmeasured |

([MotherDuck](https://motherduck.com/product/ducklake/) is another managed
DuckDB/lakehouse option in this design space; it is not priced, benchmarked or
analyzed here.)

All four include the same external writer/compaction allowance. The earlier
$82 BigQuery and $107–167 Snowflake examples used native warehouse tables and
are superseded for this comparison. BigQuery external tables need the external
writer; Snowflake's query-hour allowance no longer includes that writer's work.
The changed figures reflect a consistent ownership boundary, not new vendor rates.

The common mature subtotal is **$54.35**: raw archives/materialized pages $19.35,
edge $5 and collector allowance $30. Add the chosen canonical storage, query
engine, writer and auxiliary/export costs exactly once:

| Analytical component                        |       R2/Basin | S3/Athena | GCS/BigQuery |         R2/Snowflake |
| ------------------------------------------- | -------------: | --------: | -----------: | -------------------: |
| Canonical files and bounded retention       |          $5.40 |     $7.71 |        $6.71 |                $5.40 |
| Analytical queries                          |          $0.70 |     $1.32 |       $10.42 |    $40–100 allowance |
| External writer/compaction/materialization  |            $60 |       $60 |          $60 |                  $60 |
| Auxiliary catalog/results/refresh allowance | Included usage |        $5 |           $5 | $5 including exports |
| Export to common serving layer              |             $0 |     $2.10 |        $2.79 |   In allowance above |

These are budget cases, not an equal-performance ranking. Validate billed bytes,
charged credits, cold starts, p95 latency and freshness against the same suite.
Snowflake's 20–50 hours and all writer/auxiliary amounts are unmeasured spending
allowances. Dataset size alone does not establish those runtimes.

## Storage and serving principles

- **Retain originals and provenance.** Content-addressed exports, checksums and
  source manifests support replay and corrections. Real research files and
  identity keys stay private and gitignored.
- **Keep one authoritative canonical lake.** Use partitioned Parquet with
  Iceberg snapshots and one catalog/commit authority. Each alternative chooses
  R2, S3 or GCS for that lake; it does not add a duplicate canonical lake in R2.
- **Make serving projections rebuildable.** Prepare bounded swimmer/year and
  meet objects plus common summaries. Profile reads use cached objects; misses
  fetch those objects by key. Ordinary page requests do not run lake queries.
  Sort/filter/chart bounded histories in the client where useful.
- **Keep hot indexes small.** Use indexed directory/search rows when needed;
  KV can hold small version pointers or exact-key caches. Keep the full race
  archive in the analytical tier. Rebuild indexes and caches from the lake.
- **Refresh affected views in background jobs.** Publish consistent versions
  after new results or corrections; expire obsolete outputs and never expose
  partial builds. Bound analytical scans and concurrency separately from traffic.
- **Tier by access and recovery needs.** Start with standard object storage;
  move rarely reread originals colder only when the saving is worthwhile. Keep
  canonical history queryable and cap old snapshots/soft-deleted file retention.

These principles describe a hypothetical service; they do not add hosted
profiles or accounts to Turnmark's local research scope.

## Same files and jobs, provider-specific connections

The base has 1,300 decimal GB of originals/serving pages in R2 and 360 GB of
canonical files plus retention in the selected lake store. R2/Basin and
R2/Snowflake therefore use 1,660 GB total R2; Athena uses R2 + S3 and BigQuery
uses R2 + GCS. Each alternative pays for the same intended canonical footprint.
Temporary query-result staging is bounded within its auxiliary allowance.

[Basin SQL](https://developers.cloudflare.com/basin-sql/) and
[Athena](https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html) query
Iceberg through their supported catalogs. Cloudflare documents a
[read-only Snowflake connection to R2/Basin](https://developers.cloudflare.com/basin-catalog/config-examples/snowflake/).
That keeps the R2 lake and writer while substituting Snowflake query compute;
it does not imply Snowflake writes to that catalog.

Naming checked October 19, 2026: Cloudflare's public docs use **Basin SQL**
(formerly R2 SQL) and **Basin Catalog** (formerly R2 Data Catalog). These are
public product names, not internal shorthand.

[BigQuery external Iceberg](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables)
uses a supported catalog or explicit snapshot metadata pointer. For a metadata
file connection, the refresh job must advance that pointer after a commit.
This case colocates GCS Standard with BigQuery in Iowa/us-central1; it does not
assume a direct R2 connection or incur cross-region lake reads. BigQuery charges
external Parquet queries by selected-column **logical BigQuery type bytes**,
not by the compressed file chunks. The local logical-byte estimate remains
unverified against hosted metering.

The external writer handles normalization, corrections, compaction and output
materialization in every case. Keep the same $60 base allowance and test its
throughput; a cheap scan charge does not pay for these jobs. S3 and GCS writer
compute should run near their canonical storage. Monthly changed-page exports
are bounded inputs of **5/25/100 decimal GB** across lean/base/busy scenarios,
not a full copy of every retained page each day. The Athena/GCS totals charge
those exports at $0.09/$0.12 per GiB before account-wide free transfer. R2 reads
have no R2 egress fee; Snowflake results/refresh use the stated $5 allowance.

Managed-table variants, including
[BigQuery managed Iceberg](https://docs.cloud.google.com/bigquery/docs/biglake-iceberg-tables-in-bigquery)
and [Snowflake-managed Iceberg](https://docs.snowflake.com/en/user-guide/tables-iceberg),
remain outside these totals. They change who owns maintenance and can add
management/load/export charges. Price a managed variant by replacing the work
it takes over, not adding it on top of a full external writer allowance.

## Twenty to thirty years, ingestion and traffic

|                                 | Lean archive | Mature planning baseline | Busy service |
| ------------------------------- | -----------: | -----------------------: | -----------: |
| History retained                |     20 years |                 30 years |     30 years |
| Actual races added/year         |           5m |                      20m |          50m |
| Historical race rows            |         100m |                     600m |         1.5b |
| New races ingested/month        |         417k |                    1.67m |        4.17m |
| New races/day, annual average   |        13.7k |                    54.8k |         137k |
| API requests/month              |           1m |                      10m |         100m |
| Retained objects/tables/pages   |       280 GB |                  1.66 TB |       4.2 TB |
| R2/Basin worked total/month     |      **$39** |                 **$120** |     **$422** |
| S3/Athena worked total/month    |      **$45** |                 **$130** |     **$452** |
| GCS/BigQuery worked total/month |      **$45** |                 **$139** |     **$783** |

Snowflake remains a runtime sensitivity, not a throughput forecast assigned to
these sizes. The busy case has 10,000 ad hoc queries/month over larger cohorts;
BigQuery's logical-byte query bill grows more than the compressed-scan bill.
Measure pruning and mixed workloads before drawing a vendor ranking.

Annual race volumes are assumptions, not verified U.S. market totals. These are
cached serving workloads: daily ingestion, two grouped daily refresh families
over the latest two years, one monthly full-history pass for each family, and
100/1,000/10,000 ad hoc queries/month assuming 10% historical row pruning.
They exclude staff time, source-data fees, account/claim verification, tax,
large model training, media and a separately replicated disaster-recovery copy.
Daily figures divide annual volume by 365; weekend and seasonal peaks are not
modeled by that average.

Reproduce all line items with the [calculator](../research/conversion-model/production_budget.py):

```sh
python3 research/conversion-model/production_budget.py
```

## Cold, warm and hot retention

| Tier                | Contents                                                              | Mature footprint / starting choice                                                |
| ------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Cold originals      | Original exports, checksums, source provenance; occasional replay     | 1.2 TB R2 Standard                                                                |
| Warm canonical lake | All 30 years of Parquet/Iceberg, partitioned by date/course           | 180 GB live, up to 360 GB with retained files; selected provider's Standard class |
| Hot serving         | Versioned bounded histories/meet pages, directory and small manifests | 100 GB R2 pages + 3 GB D1 + small KV                                              |

Budget originals at 2 KB/race and live enriched canonical files at 300 compressed
bytes/race, with retained canonical files capped at 2× live size. These generous
schema inputs differ from the lean measured snapshot; source formats and richer
fields can change them. Snapshots share unchanged files: do not keep a complete
new archive copy every day. Include provider soft-delete/versioning retention
inside the headroom or price it separately.

At 20m new races/year, extending 20 years to 30 adds about 553 GB of retained
objects/pages. In the R2 case, that is about **$8/month** additional storage;
old-history scans can grow as well. New ingestion and traffic stay independent.
Moving only originals older than two years to R2 IA saves about **$5.60/month**
in the mature case; rereading that cold archive once adds about **$11.20** of
retrieval charges plus operations. Start with Standard rather than making every
historical query pay a retrieval fee.

## Capacity and backfill remain measurements

XS is a candidate for filtered, low-concurrency Snowflake queries, not a proven
capacity requirement for 600m rows. The external writer is separately priced.
20 classic XS query hours, 10 Small hours or 5 Medium hours each use 20 credits;
they do not necessarily finish the same work. Larger joins or full-history
passes can need larger compute. Include resume minimums and compare billed
credits, spills, queueing and freshness for the actual jobs.

Initial acquisition/backfill is separate: the mature inputs imply 1.2 TB of
originals and 600m parsed races. A $100–500 initial compute allowance is a
placeholder, not a quote for acquiring data or fixing historical identifiers.
Availability, provenance, duplicates and parser work can dominate labor and
elapsed time. The bounded local importer is not a national production writer.

The $60 mature writer allowance and $5 auxiliary allowances are spending inputs,
not evidence of capacity or a cost ceiling. Before treating them as sufficient:

- Measure object and catalog requests per job, including manifest reads, Parquet
  footers/range reads, retries, writes and result cleanup. Price each provider's
  operation classes separately; $5 is not a universal count of GET requests.
  At 10,000 ad hoc queries/month, even hundreds of reads per query accumulate
  into millions of requests before ingestion and compaction are counted.
- Batch small writes and compact affected partitions and metadata when measured
  file counts warrant it. Do not rewrite all retained history for every ingest.
  Track file sizes, row-group pruning and requests alongside scanned bytes.
  The query minimum applies per query, not per file; fragmentation adds metadata
  work, request overhead and potentially unnecessary reads.
- Bound DuckDB memory, threads and local temporary-disk use. Measure peak memory,
  spill bytes, scratch capacity, runtime and recovery for full-history joins and
  compaction. [DuckDB supports disk spilling](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads#larger-than-memory-workloads-out-of-core-processing),
  but some query shapes can still run out of memory. Remote source storage does
  not supply local scratch space. The full-history scan-byte proxy does not
  measure pairing-join cost or intermediate cardinality.

These are acceptance conditions for the hypothetical service, not scheduled
cloud trials. They do not change the worked totals until measurements justify
replacing the assumptions.

Open table formats and storage/compute separation have investment from
[Snowflake](https://docs.snowflake.com/en/user-guide/tables-iceberg) and
[Google](https://docs.cloud.google.com/bigquery/docs/iceberg-external-tables).
That supports exploring interchangeable readers; it is not an adoption study or
a claim that every team should operate its own DuckDB pipeline. Our actual
choice stays local DuckDB for offline research and portable data.

<details>
<summary>Technical evidence, query-only sensitivities and primary pricing sources</summary>

## Technical evidence and pricing appendix

The measurements and rate references below support the assumptions. The earlier
2m/20m/100m table is a core-query sensitivity, not the whole-service budget above.
The production calculator combines it with the explicit history, ingestion,
retention and serving inputs instead of requiring the reader to add them up.

## Common product and workload

Keep the same architecture for every backend: cache/materialize swimmer histories,
meet pages and common facets. API page views do not become warehouse queries.
Use a small search index for interactive name lookup. Keep the analytical engine
behind bounded background jobs and explicitly requested exploration.

A first sizing workload is:

- One daily grouped cohort/facet refresh: 30 queries/month. Group all supported
  dimensions together rather than rerunning the full scan for every facet value.
- One daily pairing refresh: 30 queries/month. This conservatively scans history;
  a correct incremental implementation could read less.
- An independent allowance of 100 / 1,000 / 10,000 ad hoc queries/month, each
  pruning to 10% of the cohort projection. That pruning is a design assumption
  requiring an appropriate partition/cluster layout and query-plan verification.
- The same retained history, correction/freshness policy, query results and
  latency target for each backend. No cached query results are assumed within
  the analytical query allowance. Public page response caching remains shared.

Three dataset scenarios contain 2m, 20m and 100m actual race rows. These are
sizing inputs, not claims about the size of the U.S. results universe.

## Measured byte anchor

The private frozen checkpoint contains 607,518 usable races. Its entire Parquet
snapshot is 27,631,299 bytes. A column audit produced:

| Common projection                                                                         | Logical bytes | Compressed Parquet column-chunk bytes |
| ----------------------------------------------------------------------------------------- | ------------: | ------------------------------------: |
| Cohort: course, category, distance, stroke, age, time                                     |    25,291,925 |                             2,080,208 |
| Pairing: source, swimmer ID, race ID, date, course, distance, stroke, category, time, age |   121,279,769 |                            26,310,209 |

Logical values count UTF-8 string bytes and eight bytes per non-null numerical/date
value, following the proposed BigQuery type mapping. Parquet column chunks are
measured with PyArrow metadata across the pinned Iceberg snapshot's active files.
These are byte estimates for the proposed queries, **not actual BigQuery/Basin/
Athena metered bills**. Footers, catalog/metadata work, engine pruning and billing-unit
rounding still matter. Hash identities, schema choices and dictionary repetition
also differ from a production dataset with names/search fields.

Extrapolate each projection separately by `scenario_rows / 607518`, rather than
multiplying the whole compressed file by a universal compression ratio. That
assumes similar distributions, row-group layout and compression at larger scale;
benchmark new snapshots before trusting it. The pairing projection serves as a
common ten-column analytical core for storage sizing; provenance and raw archives
remain separate retained objects available to every option.

## Query-cost scenario, not total service cost

Apply the per-query 10 MB floor in the lake model. For the one-table BigQuery
projection, apply its query/table minimum as well. Convert decimal bytes to TiB
before applying BigQuery's rate. Included allowances are otherwise unused.

| Race rows | Ad hoc queries/month | Lake compressed scans/month | BigQuery logical scans/month | Lake SQL scan fee | BigQuery on-demand scan fee | Athena SQL scan fee |
| --------- | -------------------: | --------------------------: | ---------------------------: | ----------------: | --------------------------: | ------------------: |
| 2m        |                  100 |                     3.90 GB |                     15.48 GB |             $0.00 |                       $0.00 |               $0.02 |
| 20m       |                1,000 |                    38.04 GB |                    228.02 GB |             $0.07 |                       $0.00 |               $0.18 |
| 100m      |               10,000 |                   482.61 GB |                  4,886.95 GB |             $1.18 |                      $21.53 |               $2.21 |

Athena uses the same compressed projections with a separate per-query 10 MiB
minimum and MiB rounding, resulting in about 3.97 / 38.58 / 486.27 decimal GB
billed. AWS pricing calls the binary TB a TB; the calculator converts bytes to
2^40-byte units before applying $5/TB. No temporary promotional query credit is
assumed. These scan-only figures exclude the S3/catalog/writer/export components
included in the whole-service budget.

This changes the earlier impression substantially: **BigQuery could be nearly
free for these smaller analytical workloads.** It is not inherently an expensive
choice for a modest app. Arbitrarily frequent broad scans were driving the old
large bill. Actual scanned bytes, cache reuse and query complexity determine
whether this right-sized scenario holds.

The core storage extrapolates to approximately 0.087 / 0.866 / 4.331 decimal GB
compressed and 0.399 / 3.993 / 19.963 GB logical. At this footprint storage charges
are small on every option. Raw ZIPs, full provenance, retained snapshots, search
indexes, materialized pages and extra copies need their own measured budget;
count those bytes equally rather than hide them on one side. Shared account
allowances must be consumed once, not once per table or component.

## Snowflake: measure time instead of inventing throughput

Snowflake does not bill these ordinary queries using the preceding scan-price formula.
We cannot honestly infer charged compute hours or required capacity from row
counts, API traffic or DuckDB laptop timings.

| Configuration in AWS N. Virginia    | Compute formula                  | 10 charged hours | 100 charged hours | 730 charged hours |
| ----------------------------------- | -------------------------------- | ---------------: | ----------------: | ----------------: |
| Snowflake Standard, classic X-Small | $2 × classic XS-equivalent hours |              $20 |              $200 |            $1,460 |

These are **runtime sensitivities**, not costs assigned to the three dataset
scales above. Equal hours or capacity names do not imply equal throughput.
Classic Snowflake has a 60-second resume minimum. Metered hours must include
resume effects, idle tails and resizing. Batching can be much cheaper than
separately waking a warehouse for every tiny query. Larger generations and
configurations change the rates/capacity; the table does not prove a
configuration can meet the workload or p95 latency requirement.

For example, 1,000 separate warehouse resumes imply at least 16.7 billed hours
before extra runtime or idle tails. That floor depends on the actual resume
pattern; it does not establish that resume minimums dominate the workload.

Break-even compute hours can help plan a trial: divide the alternative's
**comparable query-compute cost** by $2 for classic Snowflake XS. Add provider-specific
storage/operations and equal ingestion/export costs before comparing totals.
When a free tier makes the alternative's query fee zero, there is no positive
compute-only break-even; operator time and product requirements may dominate.

## Current primary pricing sources

- [Cloudflare Basin SQL](https://developers.cloudflare.com/basin-sql/platform/pricing/):
  $0.0025 per compressed decimal GB, 10 GB/month included, 10 MB/query minimum.
  [R2](https://developers.cloudflare.com/r2/pricing/) storage and operations and
  [catalog operations](https://developers.cloudflare.com/basin-catalog/platform/pricing/)
  are additional. R2 Standard is $0.015/GB-month with 10 GB included; its allowance
  is shared with the retained archives and serving objects, not independently
  available again for the core table.
- [BigQuery US pricing](https://cloud.google.com/bigquery/pricing): $6.25/TiB
  processed, first 1 TiB/month included. [Query charges use logical bytes](https://docs.cloud.google.com/bigquery/docs/best-practices-costs)
  for external Parquet after conversion to BigQuery types. Storage is the
  compressed GCS footprint in the main comparison. Capacity pricing and cached
  results are different cases, not applied here.
- [Snowflake's October 15, 2026 table](https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf),
  tables 1(a), 2(a), 3(a): classic XS is 1 credit/hour; Standard in N. Virginia
  is $2/credit. Native Snowflake storage is not charged for the external R2
  canonical copy; R2/catalog costs and the external writer remain. Gen 2 and
  Interactive warehouse consumption differs.
- [Athena SQL pricing](https://aws.amazon.com/athena/pricing/): $5/TB scanned,
  rounded up to a megabyte with a 10 MB/query minimum; column selection and
  compression reduce scans. AWS's [Athena cost example](https://aws.amazon.com/healthomics/pricing/)
  converts GB to TB using 1,024. The calculator uses binary MiB/TiB billing
  units, separately from decimal footprint reporting. Actual query metering
  must be checked against the estimates.
- [S3 pricing](https://aws.amazon.com/s3/pricing/): N. Virginia Standard storage
  is $0.023/GB-month for the first 50 TB, with binary GB/TB as documented on
  that page; use $0.09/GB internet export before any account-wide allowance.
  Operations and result storage are additional; the calculator reserves $5
  rather than claiming measured request counts. These are ordinary S3 buckets,
  not the separately priced S3 Tables service.
- [Glue Data Catalog pricing](https://aws.amazon.com/glue/pricing/): first 1m
  metadata objects and 1m metadata requests/month included, then $1/100k objects
  and $1/million requests. Extra managed compaction/statistics/crawlers have
  separate compute charges. The base uses the existing writer allowance for
  compaction and explicitly registered tables.
- [GCS Standard pricing](https://cloud.google.com/storage/pricing): Iowa's
  regional rate is about $0.02/GiB-month ($0.000027397/GiB-hour). The model uses
  the monthly budget rate and $0.12/GiB general internet export, with no
  free storage/egress deduction. Operations, catalog access and staging have a
  separate $5 allowance. Co-locate the GCS lake and BigQuery dataset; no
  multi-region replication, managed optimizers or Rapid Cache are included.

## Acceptance before a vendor ranking

Run equivalent snapshots and the same query suite with the same freshness,
concurrency, returned rows and p95 latency target. Include history/search/facet
serving as separate cached/indexed paths. Record billing bytes, charged
warehouse hours, cold starts, query-cache behavior, corrections/rebuilds,
metadata/operations and storage growth. Verify results before comparing speed.

Keep common edge serving/search and raw archive retention in a separate line
shared across options. Then add ingestion/writer compute, materialization/export,
backups/replication, cross-cloud egress, paid features, tax and staff time.
All four cases keep the external DuckDB writer; Snowflake hours cover the
query reader. SQL scan charges do not include external table maintenance. This
local experiment has not provisioned paid trials or benchmarked those hosted
backends. The $100–250 mature planning budget is headroom for the hypothetical
whole service, not a measured bill.

</details>
