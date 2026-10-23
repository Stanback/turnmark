"""Production planning scenarios, not cloud measurements or deployed resources.

USD, decimal GB footprints; AWS/Google billing units converted to GiB/TiB.
Rates checked 2026-10-19; see WAREHOUSE_COST_COMPARISON.md.
Collector/batch/export amounts are explicit spending allowances, not quotations.
"""

from dataclasses import asdict, dataclass
import json
import math

from cost_model import over, r2_operations


@dataclass(frozen=True)
class Scenario:
    years: int
    races_per_year: int
    api_requests: int
    ad_hoc_queries: int
    pages_gb: float
    directory_gb: float
    collector_budget: float
    lake_batch_budget: float
    r2_writes: int
    r2_reads: int
    export_gb: float

    def __post_init__(self):
        for key, value in asdict(self).items():
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
        for key in ("years", "races_per_year", "api_requests", "ad_hoc_queries",
                    "r2_writes", "r2_reads"):
            if not isinstance(getattr(self, key), int):
                raise ValueError(f"{key} must be an integer")
        if self.years < 2 or self.races_per_year == 0:
            raise ValueError("At least two history years and positive annual races required")


SCENARIOS = {
    "lean": Scenario(20, 5_000_000, 1_000_000, 100, 20, 1, 10, 20, 100_000, 1_000_000, 5),
    "base": Scenario(30, 20_000_000, 10_000_000, 1_000, 100, 3, 30, 60, 500_000, 5_000_000, 25),
    "busy": Scenario(30, 50_000_000, 100_000_000, 10_000, 300, 8, 100, 200, 2_000_000, 20_000_000, 100),
}


def r2_storage(gb):
    return over(math.ceil(gb), 10, .015)


def athena_billed_bytes(scanned_bytes):
    """Per-query MiB rounding and 10 MiB minimum; see pricing unit sources."""
    return max(10, math.ceil(scanned_bytes / 2**20)) * 2**20


def budget(s):
    races = s.years * s.races_per_year
    # Explicit production headroom: 2 KB sources/race, 300 B canonical/race,
    # retained files up to twice live canonical size. Not yearly full copies.
    raw_gb = races * 2_000 / 1e9
    live_gb = races * 300 / 1e9
    warm_gb = live_gb * 2
    common_gb = raw_gb + s.pages_gb
    total_gb = common_gb + warm_gb
    workers = (5 + over(s.api_requests, 10_000_000, .30 / 1e6)
               + over(s.api_requests * 2, 30_000_000, .02 / 1e6))
    ops = (r2_operations(s.r2_writes, 1_000_000, 4.50)
           + r2_operations(s.r2_reads, 10_000_000, .36))
    common = {
        "workers": workers,
        "raw_and_pages_storage": r2_storage(common_gb),
        "r2_operations": ops,
        "directory_storage": over(s.directory_gb, 5, .75),
        "collector_allowance": s.collector_budget,
    }
    # Measured projection sizes from the frozen 607,518-race audit. They are
    # estimates, not hosted billing measurements. Daily jobs touch two seasons;
    # two monthly full-history rebuild queries are included as well.
    anchor = 607_518
    compressed = (2_080_208 / anchor, 26_310_209 / anchor)
    logical = (25_291_925 / anchor, 121_279_769 / anchor)

    def scan_bytes(projections, billed=lambda value: max(10e6, value)):
        cohort, history = projections
        recent = 2 * s.races_per_year
        return (30 * (billed(cohort * recent) + billed(history * recent))
                + billed(cohort * races) + billed(history * races)
                + s.ad_hoc_queries * billed(cohort * races * .1))

    basin_gb = scan_bytes(compressed) / 1e9
    bq_bytes = scan_bytes(logical)
    athena_bytes = scan_bytes(compressed, athena_billed_bytes)
    lake = {
        # Marginal cost consumes the shared R2 allowance exactly once.
        "canonical_storage": r2_storage(total_gb) - r2_storage(common_gb),
        "sql_scans": over(basin_gb, 10, .0025),
        "batch_writer_allowance": s.lake_batch_budget,
    }
    # Every option queries the same externally maintained Iceberg/Parquet lake.
    # BigQuery still bills logical query bytes, but storage is compressed GCS.
    bq = {
        "gcs_canonical_storage": warm_gb * 1e9 / 2**30 * .02,
        "query_scans": over(bq_bytes / 2**40, 1, 6.25),
        "batch_writer_allowance": s.lake_batch_budget,
        "gcs_catalog_and_results_allowance": 5,
        "export_to_serving": s.export_gb * 1e9 / 2**30 * .12,
    }
    snow_fixed = {
        "r2_canonical_storage": lake["canonical_storage"],
        "batch_writer_allowance": s.lake_batch_budget,
        "refresh_and_export_allowance": 5,
    }
    # Athena reads the single canonical copy in S3, not a second copy in R2.
    # Same batch allowance as the lake: scan-priced SQL does not pay the writer.
    athena = {
        "s3_canonical_storage": warm_gb * 1e9 / 2**30 * .023,
        "query_scans": athena_bytes / 2**40 * 5,
        "batch_writer_allowance": s.lake_batch_budget,
        "s3_catalog_and_results_allowance": 5,
        # Conservative export estimate: no AWS account-wide free egress applied.
        "export_to_serving": s.export_gb * 1e9 / 2**30 * .09,
    }
    # Runtime sensitivity only: these hours are NOT assigned to dataset sizes.
    warehouse_hours = (20, 50)
    shared = sum(common.values())
    cold_gb = raw_gb - 2 * s.races_per_year * 2_000 / 1e9
    tiered_storage = r2_storage(total_gb - cold_gb) + math.ceil(cold_gb) * .01
    return {
        "assumptions": asdict(s),
        "races": races,
        "new_races_per_month": s.races_per_year / 12,
        "raw_ingest_gb_per_month": s.races_per_year * 2_000 / 12 / 1e9,
        "storage_gb": {"raw": raw_gb, "canonical_live": live_gb,
                       "canonical_with_retention": warm_gb,
                       "materialized_pages": s.pages_gb, "r2_total": total_gb,
                       "athena_r2_raw_and_pages": common_gb,
                       "athena_s3_canonical_with_retention": warm_gb,
                       "bigquery_r2_raw_and_pages": common_gb,
                       "bigquery_gcs_canonical_with_retention": warm_gb,
                       "old_raw_eligible_for_ia": cold_gb},
        "monthly_scan_gb": {"basin_compressed": basin_gb,
                            "athena_compressed_billed": athena_bytes / 1e9,
                            "bigquery_logical": bq_bytes / 1e9},
        "monthly_usd": {"common": common, "lakehouse": lake, "bigquery": bq,
                        "athena": athena, "snowflake_before_query_compute": snow_fixed},
        "totals_usd": {
            "lakehouse": shared + sum(lake.values()),
            "bigquery": shared + sum(bq.values()),
            "snowflake_if_20_to_50_classic_xs_query_hours": [shared + sum(snow_fixed.values()) + h * 2 for h in warehouse_hours],
            "athena": shared + sum(athena.values()),
        },
        "storage_tiering": {
            "all_standard_monthly_usd": r2_storage(total_gb),
            "old_raw_ia_storage_only_monthly_usd": tiered_storage,
            "storage_only_saving_usd": r2_storage(total_gb) - tiered_storage,
            "extra_retrieval_usd_if_all_old_raw_read_once": math.ceil(cold_gb) * .01,
        },
        "status": "All options use external Iceberg/Parquet; hypothetical budgets, runtime/throughput and hosted bills unverified",
    }


if __name__ == "__main__":
    print(json.dumps({name: budget(s) for name, s in SCENARIOS.items()}, indent=2))
