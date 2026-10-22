"""Hypothetical monthly Cloudflare costs; no network access or cloud resources.

Rates checked 2026-10-19. See docs/LAKEHOUSE_COST_MODEL.md for sources,
allowances, architecture assumptions and costs excluded from this estimate.
Amounts use decimal GB/MB and USD. Account allowances are assumed unused.
"""

import argparse
from dataclasses import asdict, dataclass
import json
import math


@dataclass(frozen=True)
class Workload:
    requests: int = 1_000_000
    cache_hit: float = 0.95
    storage_gb: float = 100
    scan_mb: float = 250
    background_queries: int = 5_000
    worker_cpu_ms: float = 2
    r2_writes: int = 100_000
    # Includes extra metadata/range requests made by each analytical query.
    r2_reads_per_query: int = 8
    catalog_ops_per_query: int = 2
    # Optional KV variant prepopulates the exact-key serving objects.
    kv_writes: int = 100_000
    kv_storage_gb: float = 1

    def __post_init__(self):
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        for name in ("requests", "background_queries", "r2_writes",
                     "r2_reads_per_query", "catalog_ops_per_query", "kv_writes"):
            if not isinstance(getattr(self, name), int):
                raise ValueError(f"{name} must be an integer")
        if self.cache_hit > 1:
            raise ValueError("cache_hit must be between zero and one")


def over(value, allowance, rate):
    return max(0, value - allowance) * rate


def r2_operations(value, included, rate_per_million):
    # R2 rounds up to the next million-operation billing unit.
    return math.ceil(max(0, value - included) / 1_000_000) * rate_per_million


def estimate(workload, strategy="objects"):
    """Compare equal traffic/analytics; serving data is approved, prebuilt JSON.

    objects: outer Worker Cache API hit, otherwise one exact-key R2 GET.
    kv: same outer cache, otherwise one prepopulated KV key read, no R2 GET.
    lake_misses: each outer cache miss runs managed SQL.
    lake_every_request: every request runs managed SQL (no response cache).
    All strategies include the same independent background analytical queries.
    """
    if strategy not in ("objects", "kv", "lake_misses", "lake_every_request"):
        raise ValueError("unknown strategy")
    w = workload
    misses = w.requests - math.floor(w.requests * w.cache_hit)
    page_queries = (w.requests if strategy == "lake_every_request" else
                    misses if strategy == "lake_misses" else 0)
    queries = w.background_queries + page_queries
    # This assumes one uniform scan size; real mixed workloads must sum each
    # query's max(actual compressed bytes, 10 MB), not max(the average, 10 MB).
    scanned_gb = queries * max(w.scan_mb, 10) / 1000
    r2_reads = queries * w.r2_reads_per_query
    if strategy == "objects":
        r2_reads += misses
    catalog_ops = queries * w.catalog_ops_per_query
    costs = {
        "workers_base": 5.0,
        "workers_requests": over(w.requests, 10_000_000, 0.30 / 1_000_000),
        # Cache API is inside the handler: CPU is charged on EVERY invocation.
        "workers_cpu": over(w.requests * w.worker_cpu_ms, 30_000_000,
                            0.02 / 1_000_000),
        "r2_storage": over(math.ceil(w.storage_gb), 10, 0.015),
        "r2_writes": r2_operations(w.r2_writes, 1_000_000, 4.50),
        "r2_reads": r2_operations(r2_reads, 10_000_000, 0.36),
        "sql_scans": over(scanned_gb, 10, 0.0025),
        "catalog_operations": over(catalog_ops, 1_000_000, 9 / 1_000_000),
        "kv_reads": over(misses, 10_000_000, 0.50 / 1_000_000)
                    if strategy == "kv" else 0,
        "kv_writes": over(w.kv_writes, 1_000_000, 5 / 1_000_000)
                     if strategy == "kv" else 0,
        "kv_storage": over(w.kv_storage_gb, 1, 0.50)
                      if strategy == "kv" else 0,
    }
    return {"strategy": strategy, "workload": asdict(w),
            "usage": {"page_sql_queries": page_queries,
                      "total_sql_queries": queries, "scanned_gb": scanned_gb,
                      "r2_reads": r2_reads, "catalog_operations": catalog_ops},
            "monthly_usd": costs, "total_usd": sum(costs.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=1_000_000)
    parser.add_argument("--cache-hit", type=float, default=0.95)
    parser.add_argument("--storage-gb", type=float, default=100)
    parser.add_argument("--scan-mb", type=float, default=250)
    parser.add_argument("--background-queries", type=int, default=5_000)
    args = parser.parse_args()
    try:
        w = Workload(**vars(args))
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"rates_checked": "2026-10-19",
                      "hypothetical": True,
                      "estimates": [estimate(w, strategy) for strategy in
                                    ("objects", "kv", "lake_misses",
                                     "lake_every_request")]}, indent=2))


if __name__ == "__main__":
    main()
