# Lakehouse serving and monthly cost model

Hypothetical USD estimates, rates checked October 19, 2026. No deployment,
subscription change or public release of research data is proposed by running
this calculator. The model uses decimal GB/MB and otherwise unused account
allowances. These are workload scenarios, not measured production bills.

The [right-sized cross-vendor comparison](WAREHOUSE_COST_COMPARISON.md) uses
measured per-projection bytes and daily grouped refreshes for planning. The
250 MB/query defaults and high query counts below are stress/sensitivity cases,
not a forecast for this app. Warehouse runtime requires a hosted benchmark.

## Recommendation

Keep one authoritative Iceberg/Parquet lake in R2. Use DuckDB batch jobs to
publish versioned, bounded JSON objects for athlete histories, meet pages and
common facet counts. Serve those objects through a Worker and response cache.
KV can hold small read-heavy responses and snapshot pointers, if that helps;
it is optional when an exact-key R2 object already answers the request.

This can run without a serving SQL database for a finite set of precomputed
pages/filters. It cannot cheaply precompute every arbitrary combination of
name, age, team, stroke, course, date, region and performance. Add a small D1
directory/index if live search or flexible bounded filtering needs it. Keep
historical facts in the lake and make every serving projection rebuildable.
KV's key listing is not a substitute for an inverted/search index.

PuppyGraph is a candidate for repeated multi-hop relationship queries, such as
programs connected through organizations and meet participation. Finding a
swimmer, showing their chronological improvement, and counting ordinary facets
do not establish a graph requirement or a performance advantage over SQL.
Benchmark real queries first; graph licensing and always-on compute are not in
this model. See [the team registry](TEAM_REGISTRY.md).

## Equal-workload comparison

All four strategies include the same background analytical queries. `objects`
and `kv` serve already-built pages without per-page SQL. `lake_misses` executes
SQL on each response-cache miss. `lake_every_request` executes SQL for every
page. This last strategy is a stress comparison, not the recommendation.

| Monthly API requests | Total R2 GB | Background SQL queries at 250 MB | Prebuilt objects | SQL on 5% cache misses | SQL every request |
| -------------------- | ----------- | -------------------------------- | ---------------- | ---------------------- | ----------------- |
| 100,000              | 20          | 1,000                            | $5.75            | $8.88                  | $68.25            |
| 1,000,000            | 100         | 5,000                            | $9.45            | $40.70                 | $643.54           |
| 10,000,000           | 1,000       | 10,000                           | $26.08           | $338.75                | $6,472.82         |

Reproduce this table with the [stdlib calculator](../research/conversion-model/cost_model.py).
Each scenario assumes 2 CPU-ms on every Worker request, 95% response-cache hits,
100,000 R2 writes/month, eight R2 metadata/range reads and two catalog operations
per analytical query. R2 storage includes raw archives, live lake data, retained
snapshots, metadata and serving objects. The GB assumptions are deliberate
budget inputs, not extrapolations from two million compact race rows.

```sh
python3 research/conversion-model/cost_model.py \
  --requests 1000000 --cache-hit 0.95 --storage-gb 100 \
  --scan-mb 250 --background-queries 5000
```

The calculator prints component costs and usage for all strategies. A 100%
cache hit rate removes page-query costs but not independent background work.
Real cache ratios must be measured across locations, TTLs, cold starts and
long-tail filter combinations. The model places Cache API inside the handler:
all requests incur Worker CPU. This avoids claiming that a cache hit makes a
Worker invocation free. Database or lake latency is not included in CPU time.

## Rates and mechanics

- [Workers Paid](https://developers.cloudflare.com/workers/platform/pricing/):
  $5/month, 10m requests and 30m CPU-ms included; then $0.30/million requests
  and $0.02/million CPU-ms. Static assets are a different billing path; modeled
  requests here are dynamic API requests.
- [R2 Standard](https://developers.cloudflare.com/r2/pricing/): $0.015/GB-month,
  10 GB included. Class A $4.50/million with 1m included; Class B $0.36/million
  with 10m included. The model rounds storage up to GB and operations up to
  million-unit blocks. No R2 egress charge.
- [Basin SQL](https://developers.cloudflare.com/basin-sql/platform/pricing/):
  $0.0025/GB compressed scanned, 10 GB included, minimum 10 MB per query.
  Sum `max(actual scan, 10 MB)` for each query. An average below/above that
  threshold cannot describe a mixed workload correctly; this calculator uses
  one uniform per-query input. R2 reads and catalog operations are additional.
- [Basin Catalog](https://developers.cloudflare.com/basin-catalog/platform/pricing/):
  1m metadata operations included, then $9/million. Query metadata request
  counts here are explicit assumptions, not guaranteed engine behavior.
- [KV Paid](https://developers.cloudflare.com/kv/platform/pricing/): 10m reads,
  1m writes and 1 GB included; then $0.50/million reads, $5/million writes and
  $0.50/GB-month. Optional KV pages are prepopulated; no read-through R2 fallback
  is assumed. Deletes/listing are not used by this scenario. Version retention
  would add storage/deletes in a real publisher.

For example, ten million KV writes cost $45 beyond the included million. Avoid
rewriting every athlete page every day when only a small set changed. Immutable
snapshot-scoped keys plus a small manifest support corrections and repeatable
reads. [KV is eventually consistent](https://developers.cloudflare.com/kv/concepts/how-kv-works/),
including negative lookups; publish objects before switching the manifest, allow
old versions to coexist, and handle transient misses. Do not treat KV as an
atomic lock, transaction coordinator or authoritative result store.

[D1 Paid](https://developers.cloudflare.com/d1/platform/pricing/) can add a small
search projection without an idle database server fee: 5 GB, 25b rows read and
50m rows written included monthly; then $0.75/GB-month, $0.001/million rows read
and $1/million written. Index maintenance affects writes. A hypothetical 2 GB
directory within those allowances adds no usage charge; that is not proof a
specific query meets D1's size, latency or concurrency limits. D1 is not needed
by the four cost comparisons above.

## Exclusions and operational limits

The totals exclude the ingest/DuckDB build host, training, source acquisition,
domain, taxes, support, paid logs, queue processing, graph compute/licensing,
managed compaction, extra backups/replication and other account usage. A small
batch-compute budget must be added separately, or jobs run on the existing
machine with its own electricity/hardware costs. Local DuckDB scans have no
Basin SQL fee; hosted DuckDB still needs compute and R2/catalog operations.

These modeled query costs do not establish interactive latency. A warm query
engine is not necessarily an indexed lookup. Cap public query complexity,
avoid arbitrary SQL, track scanned bytes/rows and cache miss rates, and use
bounded background publication before exposing exploratory filtering. Free
plan daily quotas are not interchangeable with these Paid monthly allowances;
existing Turnmark Workers remain on their authorized plans.
