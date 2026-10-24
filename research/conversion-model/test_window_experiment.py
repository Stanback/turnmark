"""Unit tests for the pairing-window experiment's own logic, on invented rows."""

from __future__ import annotations

import math
import unittest
from dataclasses import replace

from window_experiment import abs_errors_s, probe_pair, seasonal_order


def row(src: str, dst: str, signed_gap: int, outlier: bool = False, target_cs: int = 6672):
    return replace(
        probe_pair(5832, 100, "freestyle", "women", "100-FR", src, dst),
        signed_gap_days=signed_gap,
        gap_days=abs(signed_gap),
        target_time_cs=target_cs,
        is_ratio_outlier=outlier,
    )


class SeasonalOrderTest(unittest.TestCase):
    def test_counts_each_pair_once_in_scy_to_lcm_orientation(self):
        pairs = [
            row("SCY", "LCM", 10),
            row("LCM", "SCY", -10),  # reverse of the first: ignored
            row("SCY", "LCM", -4),
            row("SCY", "LCM", 0),
            row("SCY", "LCM", 30),
            row("SCY", "LCM", 50, outlier=True),  # screened out
            row("SCY", "SCM", 20),  # other course pair
        ]
        out = seasonal_order(pairs)
        self.assertEqual(out["pairs"], 4)
        self.assertEqual(out["share_LCM_later"], 0.5)
        self.assertEqual(out["share_LCM_earlier"], 0.25)
        self.assertEqual(out["share_same_day"], 0.25)
        self.assertEqual(out["mean_signed_gap_days_LCM_minus_SCY"], 9.0)
        self.assertEqual(out["mean_abs_gap_days"], 11.0)

    def test_empty(self):
        self.assertEqual(seasonal_order([]), {"pairs": 0})


class AbsErrorsTest(unittest.TestCase):
    def test_missing_prediction_is_nan_not_scored(self):
        pairs = [row("SCY", "LCM", 1, target_cs=6672), row("SCY", "LCM", 1, target_cs=6700)]
        errs = abs_errors_s(pairs, lambda p: 6600 if p.target_time_cs == 6672 else None)
        self.assertAlmostEqual(errs[0], 0.72)
        self.assertTrue(math.isnan(errs[1]))


if __name__ == "__main__":
    unittest.main()
