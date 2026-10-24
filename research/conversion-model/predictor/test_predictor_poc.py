"""Tests for the forward-only predictor POC. Invented records only; no real swimmer data.

Run: python -m unittest discover -s research/conversion-model/predictor -v
"""

from __future__ import annotations

import dataclasses
import json
import math
import unittest
from datetime import date, timedelta

import numpy as np

import predictor_poc as P
from evaluate_and_train import SwimRecord, swimmer_partition


def swim(sid: str, day: date, course: str, distance: int, time_cs: int, age: float | None = 13.0,
         stroke: str = "freestyle", category: str = "women", meet: str | None = None) -> SwimRecord:
    return SwimRecord(
        source="synthetic", race_id=f"{sid}-{course}-{distance}-{day.isoformat()}", swimmer_id=sid,
        meet_id=meet or f"m-{course}-{day.isoformat()}", race_date=day, course=course, distance=distance,
        stroke=stroke, category=category, time_cs=time_cs, age_years=age, region="unknown",
    )


D0 = date(2024, 1, 1)


def at(days: int) -> date:
    return D0 + timedelta(days=days)


def rows_for(ex: P.Examples, direction: str) -> list[dict]:
    m = ex.dir == P.DIRECTIONS.index(direction)
    keys = ("src_day", "tgt_day", "gap", "src_cs", "tgt_cs", "tb_cs", "tb_days", "sp_cs")
    sub = ex.subset(m)
    order = np.argsort(sub.tgt_day)
    return [{k: sub.cols[k][i] for k in keys} for i in order]


class ForwardOnlyPairingTest(unittest.TestCase):
    def setUp(self):
        self.swims = [
            swim("a", at(0), "SCY", 100, 6000),
            swim("a", at(50), "LCM", 100, 6900),
            swim("a", at(100), "SCY", 100, 5900),
            swim("a", at(120), "LCM", 100, 6800),
            swim("a", at(150), "LCM", 100, 6750),
            swim("a", at(200), "SCY", 100, 5850),
            swim("a", at(700), "LCM", 100, 6500),  # > 365 days after the last SCY swim
        ]
        self.ex = P.build_examples(self.swims)

    def test_each_target_pairs_with_most_recent_earlier_source(self):
        got = [(r["src_day"] - P.day_number(D0), r["tgt_day"] - P.day_number(D0))
               for r in rows_for(self.ex, "SCY->LCM")]
        self.assertEqual(got, [(0, 50), (100, 120), (100, 150)])
        got_rev = [(r["src_day"] - P.day_number(D0), r["tgt_day"] - P.day_number(D0))
                   for r in rows_for(self.ex, "LCM->SCY")]
        self.assertEqual(got_rev, [(50, 100), (150, 200)])

    def test_source_strictly_before_target_and_gap_capped(self):
        self.assertTrue(np.all(self.ex.src_day < self.ex.tgt_day))
        self.assertTrue(np.all((self.ex.gap >= 1) & (self.ex.gap <= P.MAX_GAP_DAYS)))
        self.assertNotIn(P.day_number(at(700)), set(self.ex.tgt_day.tolist()))

    def test_history_uses_only_swims_on_or_before_source_date(self):
        r = rows_for(self.ex, "SCY->LCM")
        # Target LCM@150 from source SCY@100: the LCM@120 swim is after the source date, so the
        # target-course history is LCM@50 only, never the target itself or anything after day 100.
        self.assertEqual(r[2]["tb_cs"], 6900)
        self.assertEqual(r[2]["tb_days"], 50)
        self.assertEqual(r[2]["sp_cs"], 6000)  # prior SCY best strictly before the source
        # First example has no earlier swims of either course.
        self.assertTrue(math.isnan(r[0]["tb_cs"]) and math.isnan(r[0]["sp_cs"]))
        rev = rows_for(self.ex, "LCM->SCY")
        # Target SCY@200 from source LCM@150: SCY history up to day 150 is SCY@0 and SCY@100.
        self.assertEqual(rev[1]["tb_cs"], 5900)
        self.assertEqual(rev[1]["sp_cs"], 6800)  # best LCM strictly before the LCM@150 source

    def test_target_only_metadata_cannot_change_features(self):
        # The source swim and everything before it stay fixed; only target-record fields that are
        # neither the label (target time) nor the user-supplied target date vary.
        variants = [
            dict(age=12.9),
            dict(age=17.0),  # implausible on purpose: a target age must not move anything
            dict(age=None),
            dict(age=12.9, meet="another-meet", region="elsewhere", race_id="other-race"),
        ]

        def feature_rows(source_age):
            history = [swim("f", at(0), "SCY", 100, 6100, age=12.4),
                       swim("f", at(20), "LCM", 100, 7000, age=12.5),
                       swim("f", at(60), "SCY", 100, 6000, age=source_age)]
            out = []
            for v in variants:
                target = swim("f", at(150), "LCM", 100, 6950, age=v["age"], meet=v.get("meet"))
                if "region" in v:
                    target = dataclasses.replace(target, region=v["region"], race_id=v["race_id"])
                ex = P.build_examples(history + [target])
                keys = sorted(k for k in ex.cols if k not in ("tgt_cs", "rid"))
                rows = [tuple("nan" if isinstance(x, float) and math.isnan(x) else x
                              for x in (ex.cols[k][i].item() for k in keys)) for i in range(len(ex))]
                out.append((keys, rows))  # build_examples orders rows by target day, swimmer, dir, event
            return out

        for source_age in (12.6, None):
            with self.subTest(source_age=source_age):
                per_variant = feature_rows(source_age)
                for got in per_variant[1:]:
                    self.assertEqual(got, per_variant[0])
        # With a recorded source age the target pair exists and carries the source swim's own age.
        keys, rows = feature_rows(12.6)[0]
        target_rows = [r for r in rows if r[keys.index("tgt_day")] == P.day_number(at(150))]
        self.assertEqual(len(target_rows), 1)
        self.assertAlmostEqual(target_rows[0][keys.index("age")], 12.6)

    def test_source_without_age_yields_no_example(self):
        ex = P.build_examples([swim("g", at(0), "SCY", 100, 6000, age=None),
                               swim("g", at(40), "LCM", 100, 6900, age=13.0)])
        self.assertEqual(len(ex), 0)
        # The dropped pair is not re-paired to an older age-known source either.
        ex = P.build_examples([swim("h", at(0), "SCY", 100, 6100, age=12.9),
                               swim("h", at(30), "SCY", 100, 6000, age=None),
                               swim("h", at(60), "LCM", 100, 6900, age=13.1)])
        self.assertEqual(len(rows_for(ex, "SCY->LCM")), 0)

    def test_nonstandard_course_distances_dropped(self):
        ex = P.build_examples([swim("b", at(0), "SCY", 400, 30000), swim("b", at(30), "LCM", 400, 29000)])
        self.assertEqual(len(ex), 0)

    def test_scy_400_im_is_kept(self):
        ex = P.build_examples([
            swim("i", at(0), "SCY", 400, 30000, stroke="individual-medley"),
            swim("i", at(30), "LCM", 400, 33500, stroke="individual-medley"),
        ])
        self.assertEqual(len(ex), 1)  # forward only: the later LCM swim is the one target
        self.assertEqual(int(ex.ev[0]), P.EVENTS.index("400-IM"))

    def test_events_and_sexes_do_not_mix(self):
        ex = P.build_examples([
            swim("c", at(0), "SCY", 100, 6000),
            swim("c", at(30), "LCM", 200, 14000),
            swim("c", at(40), "LCM", 100, 7000, stroke="backstroke"),
        ])
        self.assertEqual(len(ex), 0)


def synthetic_examples(n_swimmers: int = 1500, seed: int = 1) -> P.Examples:
    """Invented examples with a known process: log(target/source) = NCAA + 0.04
    + progression(age) * gap + personal offset + noise, where young swimmers improve fastest and
    the personal offset is visible in their earlier target-course best."""
    rng = np.random.default_rng(seed)
    ncaa = P.ncaa_log_factor_table()
    cols = {k: [] for k in ("swimmer", "part", "dir", "ev", "sex", "src_cs", "tgt_cs", "src_day", "tgt_day",
                            "gap", "age", "tgt_month", "tb_cs", "tb_days", "sp_cs")}
    for s in range(n_swimmers):
        age = float(rng.integers(9, 22))
        personal = rng.normal(0, 0.015)
        sex = int(rng.integers(0, 2))
        part = P.PARTITIONS.index(swimmer_partition("synthetic", f"s{s}"))
        for _ in range(8):
            d = int(rng.integers(0, 2))
            ev = int(rng.integers(0, 3))
            cell = P.cell_index(d, ev, sex)
            gap = int(rng.integers(1, 366))
            src = float(rng.uniform(3000, 9000) * (1 + 0.5 * ev))
            prog = -0.06 * max(0.0, 18 - age) / 9 * gap / 365
            y = ncaa[cell] + 0.04 + prog + personal + rng.normal(0, 0.01)
            tgt_day = int(rng.integers(P.day_number(date(2024, 1, 1)), P.day_number(date(2026, 9, 1))))
            has_hist = rng.random() < 0.7
            tb = src * math.exp(ncaa[cell] + 0.04 + personal + rng.normal(0, 0.005)) if has_hist else np.nan
            for k, v in (("swimmer", s), ("part", part), ("dir", d), ("ev", ev), ("sex", sex), ("src_cs", src),
                         ("tgt_cs", src * math.exp(y)), ("src_day", tgt_day - gap), ("tgt_day", tgt_day),
                         ("gap", gap), ("age", age), ("tgt_month", 6), ("tb_cs", tb),
                         ("tb_days", 100.0 if has_hist else np.nan), ("sp_cs", np.nan)):
                cols[k].append(v)
    out = {k: np.array(v, dtype=float if k in ("src_cs", "tgt_cs", "age", "tb_cs", "tb_days", "sp_cs")
                       else np.int64) for k, v in cols.items()}
    out["cell"] = P.cell_index(out["dir"], out["ev"], out["sex"])
    return P.Examples(out)


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ex = synthetic_examples()
        sp = P.temporal_splits(cls.ex, calibration_start=date(2024, 1, 1))
        cls.splits = sp
        cls.train, cls.calib, cls.test = (cls.ex.subset(sp[k]) for k in ("train", "calibration", "test"))
        cls.fp = P.fit_predictor(cls.train, cls.calib, ridge=10.0)

    def mae(self, pred):
        return float(np.mean(np.abs(pred - self.test.tgt_cs)))

    def test_splits_are_temporal_and_swimmer_disjoint(self):
        c = P.day_number(P.CUTOFF)
        self.assertTrue(np.all(self.train.tgt_day < c) and np.all(self.calib.tgt_day < c))
        self.assertTrue(np.all(self.test.tgt_day >= c))
        tr, ca, te = (set(x.swimmer.tolist()) for x in (self.train, self.calib, self.test))
        self.assertFalse(tr & te or tr & ca or ca & te)
        nd = P.temporal_splits(self.ex, disjoint=False)
        self.assertTrue(np.array_equal(nd["test"], self.splits["test"]))
        self.assertTrue(np.all(self.ex.tgt_day[nd["train"]] < c))
        self.assertTrue(set(self.ex.swimmer[nd["train"]].tolist()) & te)

    def test_models_rank_as_the_generating_process_implies(self):
        ncaa = self.mae(P.predict_ncaa(self.test))
        flat = self.mae(self.fp.flat.predict(self.test))
        pooled = self.mae(self.fp.pooled.predict(self.test))
        hist = self.mae(self.fp.history.predict(self.test))
        self.assertLess(flat, ncaa)
        self.assertLess(pooled, 0.9 * flat)
        self.assertLess(hist, 0.9 * pooled)

    def test_progression_is_faster_for_younger_swimmers(self):
        young = P.synthetic_example("SCY->LCM", "100-FR", "women", 6500, age=10, gap_days=300)
        young0 = P.synthetic_example("SCY->LCM", "100-FR", "women", 6500, age=10, gap_days=1)
        adult = P.synthetic_example("SCY->LCM", "100-FR", "women", 6500, age=20, gap_days=300)
        adult0 = P.synthetic_example("SCY->LCM", "100-FR", "women", 6500, age=20, gap_days=1)
        drop_young = self.fp.pooled.predict(young0)[0] - self.fp.pooled.predict(young)[0]
        drop_adult = self.fp.pooled.predict(adult0)[0] - self.fp.pooled.predict(adult)[0]
        self.assertGreater(drop_young, 100)  # > 1 s faster after a 300-day gap
        self.assertLess(abs(drop_adult), 0.5 * drop_young)

    def test_intervals_are_calibrated_and_ordered(self):
        pred, lo, hi = self.fp.predict_with_interval(self.test, "history")
        self.assertTrue(np.all(lo <= pred) and np.all(pred <= hi))
        cov = P.coverage_summary(self.test, lo, hi)["coverage"]
        self.assertAlmostEqual(cov, P.INTERVAL_LEVEL, delta=0.05)

    def test_interval_fallback_covers_unseen_buckets(self):
        ex1 = P.synthetic_example("SCY->LCM", "100-FR", "women", 6500, age=float("nan"), gap_days=200)
        _, lo, hi = self.fp.predict_with_interval(ex1, "history")
        self.assertTrue(np.isfinite(lo[0]) and np.isfinite(hi[0]) and lo[0] < hi[0])

    def test_clustered_bootstrap_brackets_point_and_is_reproducible(self):
        preds = {"flat": self.fp.flat.predict(self.test), "pooled": self.fp.pooled.predict(self.test)}
        a = P.clustered_bootstrap(self.test, preds, [("pooled", "flat")], reps=200)
        b = P.clustered_bootstrap(self.test, preds, [("pooled", "flat")], reps=200)
        self.assertEqual(a, b)
        lo, hi = a["mae_ci95_s"]["pooled"]
        self.assertLessEqual(lo, self.mae(preds["pooled"]) / 100.0)
        self.assertGreaterEqual(hi, self.mae(preds["pooled"]) / 100.0)
        d = a["mae_difference_ci95_s"]["pooled - flat"]
        self.assertLess(d["ci95"][1], 0)

    def test_small_groups_are_suppressed(self):
        labels = np.array(["big"] * (len(self.test) - 5) + ["tiny"] * 5)
        out = P.grouped(self.test, labels, lambda sub, m: {"rows": int(m.sum())})
        self.assertEqual(out["tiny"], {"rows": 5, "suppressed": True})
        self.assertNotIn("suppressed", out["big"])


class EndToEndTest(unittest.TestCase):
    def test_receipt_carries_aggregates_only(self):
        rng = np.random.default_rng(3)
        swims = []
        for s in range(260):
            sid = f"secret-swimmer-{s:04d}"
            base = rng.uniform(5500, 8000)
            age0 = float(rng.integers(10, 17))
            for season in range(3):
                for k, (course, start) in enumerate((("SCY", date(2023 + season, 11, 1)),
                                                     ("LCM", date(2024 + season, 6, 1)))):
                    for meet in range(3):
                        day = start + timedelta(days=21 * meet + int(rng.integers(0, 5)))
                        t = base * (0.97 ** season) * (1.12 if course == "LCM" else 1.0) * rng.normal(1, 0.01)
                        swims.append(swim(sid, day, course, 100, int(t), age=age0 + season))
        receipt = P.evaluate_swims(swims, bootstrap_reps=50)
        text = json.dumps(receipt)
        self.assertNotIn("secret-swimmer", text)
        self.assertIn("swimmer_disjoint_test", receipt)
        self.assertGreater(receipt["examples"]["test"]["rows"], 0)
        for case in receipt["worked_examples_synthetic"]:
            self.assertIn("likely", case["history"])


if __name__ == "__main__":
    unittest.main()
