from dataclasses import replace
import unittest

from production_budget import SCENARIOS, athena_billed_bytes, budget, r2_storage


class ProductionBudgetTests(unittest.TestCase):
    def test_base_retention_ingestion_and_cost_reconcile(self):
        result = budget(SCENARIOS["base"])
        self.assertEqual(result["races"], 600_000_000)
        self.assertEqual(result["storage_gb"]["r2_total"], 1660)
        self.assertEqual(result["storage_tiering"]["all_standard_monthly_usd"], 24.75)
        self.assertAlmostEqual(result["raw_ingest_gb_per_month"], 10 / 3)
        self.assertAlmostEqual(result["totals_usd"]["lakehouse"], 120.4489, places=3)
        parts = result["monthly_usd"]
        self.assertAlmostEqual(parts["common"]["raw_and_pages_storage"]
                               + parts["lakehouse"]["canonical_storage"],
                               r2_storage(1660))

    def test_old_archive_tiering_has_retrieval_cost(self):
        result = budget(SCENARIOS["base"])["storage_tiering"]
        self.assertAlmostEqual(result["storage_only_saving_usd"], 5.60)
        self.assertAlmostEqual(result["extra_retrieval_usd_if_all_old_raw_read_once"], 11.20)
        twenty = budget(replace(SCENARIOS["base"], years=20, pages_gb=100 * 2 / 3))
        self.assertEqual(twenty["races"], 400_000_000)
        self.assertAlmostEqual(twenty["storage_gb"]["r2_total"], 1660 * 2 / 3)

    def test_athena_minimum_rounding_and_single_canonical_store(self):
        self.assertEqual(athena_billed_bytes(0), 10 * 2**20)
        self.assertEqual(athena_billed_bytes(10 * 2**20), 10 * 2**20)
        self.assertEqual(athena_billed_bytes(10 * 2**20 + 1), 11 * 2**20)
        result = budget(SCENARIOS["base"])
        parts = result["monthly_usd"]
        self.assertAlmostEqual(result["totals_usd"]["athena"], 130.4741, places=3)
        self.assertAlmostEqual(parts["athena"]["s3_canonical_storage"],
                               360e9 / 2**30 * .023)
        self.assertEqual(parts["athena"]["batch_writer_allowance"],
                         parts["lakehouse"]["batch_writer_allowance"])
        self.assertAlmostEqual(result["totals_usd"]["athena"],
                               sum(parts["common"].values()) + sum(parts["athena"].values()))
        # Turning off exports removes transfer only; lake storage/scan stay put.
        no_export = budget(replace(SCENARIOS["base"], export_gb=0))
        self.assertAlmostEqual(result["totals_usd"]["athena"] - no_export["totals_usd"]["athena"],
                               25e9 / 2**30 * .09)
        self.assertEqual(result["totals_usd"]["lakehouse"], no_export["totals_usd"]["lakehouse"])

    def test_every_engine_pays_for_same_external_lake_writer_and_retention(self):
        result = budget(SCENARIOS["base"])
        costs = result["monthly_usd"]
        for engine in ("lakehouse", "athena", "bigquery", "snowflake_before_query_compute"):
            self.assertEqual(costs[engine]["batch_writer_allowance"], 60)
        self.assertAlmostEqual(costs["bigquery"]["gcs_canonical_storage"],
                               360e9 / 2**30 * .02)
        self.assertAlmostEqual(costs["bigquery"]["export_to_serving"],
                               25e9 / 2**30 * .12)
        self.assertEqual(costs["snowflake_before_query_compute"]["r2_canonical_storage"],
                         costs["lakehouse"]["canonical_storage"])
        # More history affects the same retained bytes in each object store.
        doubled = budget(replace(SCENARIOS["base"], years=60))["monthly_usd"]
        for engine, storage_key in (("athena", "s3_canonical_storage"),
                                    ("bigquery", "gcs_canonical_storage")):
            self.assertAlmostEqual(doubled[engine][storage_key], 2 * costs[engine][storage_key])
        # Query-only warehouse time is added after the external writer, once.
        fixed = sum(costs["common"].values()) + sum(costs["snowflake_before_query_compute"].values())
        self.assertEqual(result["totals_usd"]["snowflake_if_20_to_50_classic_xs_query_hours"],
                         [fixed + 40, fixed + 100])

    def test_history_and_live_workload_are_separate(self):
        scenario = SCENARIOS["base"]
        doubled_history = budget(replace(scenario, years=60))
        original = budget(scenario)
        self.assertEqual(doubled_history["new_races_per_month"], original["new_races_per_month"])
        self.assertEqual(doubled_history["monthly_usd"]["common"]["workers"],
                         original["monthly_usd"]["common"]["workers"])
        self.assertEqual(doubled_history["storage_gb"]["canonical_with_retention"],
                         2 * original["storage_gb"]["canonical_with_retention"])
        for kwargs in ({"years": 1}, {"years": 2.5}, {"api_requests": -1},
                       {"collector_budget": float("nan")}, {"export_gb": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                replace(scenario, **kwargs)


if __name__ == "__main__":
    unittest.main()
