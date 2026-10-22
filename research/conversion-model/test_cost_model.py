import unittest

from cost_model import Workload, estimate, r2_operations


class CostModelTests(unittest.TestCase):
    def test_billing_boundaries_and_query_minimum(self):
        self.assertEqual(r2_operations(10_000_000, 10_000_000, .36), 0)
        self.assertEqual(r2_operations(10_000_001, 10_000_000, .36), .36)
        result = estimate(Workload(requests=0, storage_gb=10.1,
                                   background_queries=1_001, scan_mb=0))
        self.assertAlmostEqual(result["usage"]["scanned_gb"], 10.01)
        self.assertAlmostEqual(result["monthly_usd"]["sql_scans"], .000025)
        self.assertAlmostEqual(result["monthly_usd"]["r2_storage"], .015)

    def test_one_million_uncached_gb_queries(self):
        result = estimate(Workload(cache_hit=0, scan_mb=1000,
                                   background_queries=0), "lake_every_request")
        self.assertEqual(result["usage"]["page_sql_queries"], 1_000_000)
        self.assertAlmostEqual(result["monthly_usd"]["sql_scans"], 2499.975)
        self.assertEqual(estimate(Workload(cache_hit=1), "lake_misses")
                         ["usage"]["page_sql_queries"], 0)

    def test_materialization_and_worker_allowances(self):
        result = estimate(Workload())
        self.assertAlmostEqual(result["total_usd"], 9.45)
        busy = estimate(Workload(requests=100_000_000))
        self.assertEqual(busy["monthly_usd"]["workers_requests"], 27)
        self.assertAlmostEqual(busy["monthly_usd"]["workers_cpu"], 3.4)
        kv = estimate(Workload(requests=100_000_000, cache_hit=0,
                               kv_writes=2_000_000, kv_storage_gb=3), "kv")
        self.assertEqual(kv["monthly_usd"]["kv_reads"], 45)
        self.assertEqual(kv["monthly_usd"]["kv_writes"], 5)
        self.assertEqual(kv["monthly_usd"]["kv_storage"], 1)

    def test_invalid_workloads_fail(self):
        for kwargs in ({"cache_hit": 1.1}, {"storage_gb": float("nan")},
                       {"requests": -1}, {"requests": 1.5},
                       {"requests": True}, {"scan_mb": float("inf")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Workload(**kwargs)
        with self.assertRaises(ValueError):
            estimate(Workload(), "mystery")


if __name__ == "__main__":
    unittest.main()
