"""Unit tests for offline conversion-model hygiene, balancing, and evaluation."""

from __future__ import annotations

from datetime import date, timedelta
import unittest

from evaluate_and_train import (
    BoundedHistogramGBM,
    EmpiricalQuantileModel,
    HuberPaceModel,
    SplitConformalCalibrator,
    SwimRecord,
    augment_sparse_training_pairs,
    build_directional_pairs,
    compute_training_weights,
    deduplicate_best_of_meet,
    predict_colorado_cs,
    predict_ncaa_cs,
    run_pipeline,
)


class EvaluateAndTrainTests(unittest.TestCase):
    def test_ncaa_and_colorado_formulas_match_core_tables(self):
        # 100 Free Women SCY 50.00 (5000 cs) -> LCM: 50.00 / 0.874 = 57.2082... -> 5720 cs
        self.assertEqual(
            predict_ncaa_cs(5000, "SCY", "LCM", "freestyle", 100, "women"),
            5720,
        )
        # 100 Free Women LCM 57.20 -> SCY: 57.20 * 0.874 = 49.9928 -> 4999 cs
        self.assertEqual(
            predict_ncaa_cs(5720, "LCM", "SCY", "freestyle", 100, "women"),
            4999,
        )
        # 500 Free Men SCY 4:30.00 (27000 cs) -> 400 LCM: 270.00 / 1.105 = 244.3438... -> 24434 cs
        self.assertEqual(
            predict_ncaa_cs(27000, "SCY", "LCM", "freestyle", 500, "men"),
            24434,
        )
        # Colorado 100 Free SCY 50.00 -> LCM: 50.00 * 1.11 + 1.6 = 57.10 -> 5710 cs
        self.assertEqual(
            predict_colorado_cs(5000, "SCY", "LCM", "freestyle", 100),
            5710,
        )
        # Colorado 500 Free SCY 300.00 -> 400 LCM: 300.00 * 0.8925 = 267.75 -> 26775 cs
        self.assertEqual(
            predict_colorado_cs(30000, "SCY", "LCM", "freestyle", 500),
            26775,
        )

    def test_best_of_meet_and_hygiene_filtering(self):
        records = [
            # Same meet prelim + final -> only fastest (5200) survives
            SwimRecord("src", "r1", "s1", "m1", date(2025, 3, 1), "SCY", 100, "freestyle", "women", 5310, 15.0, "RegA"),
            SwimRecord("src", "r2", "s1", "m1", date(2025, 3, 1), "SCY", 100, "freestyle", "women", 5200, 15.0, "RegA"),
            # Implausible world-record violation (10.00s for 100 Free) -> excluded
            SwimRecord("src", "r3", "s2", "m1", date(2025, 3, 1), "SCY", 100, "freestyle", "women", 1000, 15.0, "RegA"),
            # Non-NCAA 50 Backstroke -> excluded
            SwimRecord("src", "r4", "s3", "m1", date(2025, 3, 1), "SCY", 50, "backstroke", "women", 2800, 12.0, "RegA"),
        ]
        dedup, stats = deduplicate_best_of_meet(records)
        self.assertEqual(len(dedup), 1)
        self.assertEqual(dedup[0].race_id, "r2")
        self.assertEqual(stats["same_meet_slower_rounds_collapsed"], 1)
        self.assertEqual(stats["excluded_implausible_time"], 1)
        self.assertEqual(stats["excluded_non_ncaa_event"], 1)

    def test_swimmer_disjoint_and_directional_models_improve_over_fixed_factor(self):
        # Generate synthetic swimmers where LCM = SCY / 0.874 + 60cs + pace_effect
        swims: list[SwimRecord] = []
        base_date = date(2025, 5, 1)
        for idx in range(180):
            sid = f"swimmer-{idx}"
            scy_cs = 4800 + (idx % 30) * 60
            # True non-linear target: NCAA + 55cs + slower-swimmer extra turn loss
            ncaa_lcm = predict_ncaa_cs(scy_cs, "SCY", "LCM", "freestyle", 100, "women")
            assert ncaa_lcm is not None
            lcm_cs = ncaa_lcm + 55 + int(((scy_cs - 5500) / 500.0) * 35)
            age = 11.0 + (idx % 8)
            reg = "RegA" if idx % 3 else "Southeastern Swimming"
            year_offset = 365 if idx % 5 == 0 else 0
            d1 = base_date + timedelta(days=year_offset)
            d2 = d1 + timedelta(days=10)
            swims.append(
                SwimRecord("syn", f"scy-{idx}", sid, f"m-scy-{idx}", d1, "SCY", 100, "freestyle", "women", scy_cs, age, reg)
            )
            swims.append(
                SwimRecord("syn", f"lcm-{idx}", sid, f"m-lcm-{idx}", d2, "LCM", 100, "freestyle", "women", lcm_cs, age, reg)
            )

        dedup, _ = deduplicate_best_of_meet(swims)
        pairs = build_directional_pairs(dedup, max_days=30)
        # Forward and reverse pairs for any swimmer must share the exact same partition
        by_swimmer_parts = {}
        for p in pairs:
            by_swimmer_parts.setdefault(p.swimmer_key, set()).add(p.partition)
        self.assertTrue(all(len(parts) == 1 for parts in by_swimmer_parts.values()))

        train_p = [p for p in pairs if p.partition == "train"]
        val_p = [p for p in pairs if p.partition == "validation"]
        test_p = [p for p in pairs if p.partition == "test"]
        weights = compute_training_weights(train_p)
        self.assertEqual(len(weights), len(train_p))

        huber = HuberPaceModel(include_age=False)
        huber.fit(train_p, weights)
        gbm = BoundedHistogramGBM(include_age=True, max_trees=15)
        gbm.fit(train_p, weights, val_p)
        q_model = EmpiricalQuantileModel()
        q_model.fit(train_p)

        report = run_pipeline(swims, input_label="synthetic-test", max_days=30, venues_csv=None)
        clean_metrics = report["swimmer_disjoint_holdout"]["clean_test"]
        self.assertLess(
            clean_metrics["tier1_huber_pace_core"]["mae_seconds"],
            clean_metrics["ncaa_2025_27"]["mae_seconds"],
        )
        self.assertIn("100-FR", report["swimmer_disjoint_holdout"]["by_event"])
        boot = report["swimmer_disjoint_holdout"]["bootstrap_significance"]["overall_clean_test"]
        self.assertLess(
            boot["comparisons_vs_ncaa"]["tier1_huber_pace_core"]["ci95_high_seconds"],
            0.0,
        )
        conf = report["swimmer_disjoint_holdout"]["conformal_prediction_intervals"]["tier1_huber_pace_core"]
        self.assertGreaterEqual(
            conf["overall_clean_test"]["nominal_90pct"]["empirical_coverage_pct"],
            75.0,
        )
        self.assertFalse(report["validated_for_product"])

    def test_sparse_training_augmentation_preserves_partition_disjointness(self):
        base = date(2025, 6, 1)
        swims = [
            SwimRecord("syn", "s1-y", "s1", "m1", base, "SCY", 1000, "freestyle", "women", 60000, 16.0, "RegA"),
            SwimRecord("syn", "s1-m", "s1", "m2", base + timedelta(days=45), "LCM", 800, "freestyle", "women", 54500, 16.0, "RegA"),
        ]
        dedup, _ = deduplicate_best_of_meet(swims)
        p30 = build_directional_pairs(dedup, max_days=30)
        p60 = build_directional_pairs(dedup, max_days=60)
        self.assertEqual(len(p30), 0)
        self.assertEqual(len(p60), 2)
        aug, counts = augment_sparse_training_pairs(
            [p for p in p30 if p.partition == "train"],
            [p for p in p60 if p.partition == "train"],
        )
        if p60[0].partition == "train":
            self.assertEqual(len(aug), 2)
            self.assertEqual(counts.get("800-FR"), 2)
        else:
            self.assertEqual(len(aug), 0)


if __name__ == "__main__":
    unittest.main()
