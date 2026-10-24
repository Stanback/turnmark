"""Unit tests for the equivalence model, its baselines and the evaluation pipeline."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import math
import random
import unittest
from dataclasses import replace

import numpy as np

from evaluate_and_train import (
    ROOT,
    AnchoredPercentileModel,
    DirectionalPair,
    EquivalenceModel,
    EquivalentTime,
    FlatMultiplierModel,
    Posterior,
    RepeatSwim,
    SwimRecord,
    _apply_holm_correction,
    build_directional_pairs,
    build_empirical_parity_fixture,
    canonical_event_key,
    clustered_bootstrap,
    conversion_caveat,
    deduplicate_best_of_meet,
    deming_slope,
    engine_equivalence,
    engine_equivalence_cs,
    estimate_course_noise,
    independent_swim_deciles,
    knot_map,
    leave_regions_out_splits,
    predict_colorado_cs,
    predict_ncaa_cs,
    requery,
    run_pipeline,
    shrink_toward,
    snapshot_arithmetic_properties,
    temporal_holdout_splits,
)


def latent_swims(n_swimmers: int, seed: int = 7, noise: float = 0.015, second_scy: bool = False) -> list[SwimRecord]:
    """Invented swimmers whose SCY, LCM and SCM 100 free times are noisy readings of one latent
    ability: ln SCY = 4.10 + u, ln LCM = 4.24 + 0.95 u, ln SCM = 4.22 + 0.97 u. second_scy adds a
    later SCY swim, outside the 30-day pairing window, for the independent-swim diagnostic."""
    rng = random.Random(seed)
    base = date(2025, 5, 1)
    swims: list[SwimRecord] = []
    for idx in range(n_swimmers):
        sid = f"latent-{idx}"
        u = rng.gauss(0.0, 0.18)
        races = [("SCY", 4.10, 1.0, 0), ("LCM", 4.24, 0.95, 10), ("SCM", 4.22, 0.97, 20)]
        if second_scy:
            races.append(("SCY", 4.10, 1.0, 75))
        for course, loc, scale, day in races:
            seconds = math.exp(loc + scale * u + rng.gauss(0.0, noise))
            swims.append(
                SwimRecord("syn", f"{course}-{idx}-{day}", sid, f"m-{course}-{idx}-{day}", base + timedelta(days=day),
                           course, 100, "freestyle", "women", int(seconds * 100), 15.0, "RegA")
            )
    return swims


KNOWN_MAPS = {"SCY": (4.10, 1.0), "LCM": (4.24, 0.95), "SCM": (4.22, 0.97)}


def known_pairs(
    n_swimmers: int, sd: dict[str, float], seed: int = 3, pairs_each: int = 1, event: str = "100-FR"
) -> list[DirectionalPair]:
    """Invented pairs in all three course pairs with a known equivalence: ability a (SCY log
    seconds) has ln time = loc + scale (a - 4.10) in each course (KNOWN_MAPS), and every swim adds
    independent noise with its course's sd."""
    rng = random.Random(seed)
    pairs: list[DirectionalPair] = []
    for idx in range(n_swimmers):
        a = 4.10 + rng.gauss(0.0, 0.15)
        for k in range(pairs_each):
            for src, dst in (("SCY", "LCM"), ("SCY", "SCM"), ("SCM", "LCM")):
                x, y = (KNOWN_MAPS[c][0] + KNOWN_MAPS[c][1] * (a - 4.10) + rng.gauss(0.0, sd[c]) for c in (src, dst))
                pairs.append(
                    DirectionalPair(
                        swimmer_key=f"known-{idx}", partition="train", direction=f"{src}->{dst}", event_key=event,
                        stroke="freestyle", source_course=src, target_course=dst, source_distance=100,
                        target_distance=100, category="women", source_time_cs=round(math.exp(x) * 100),
                        target_time_cs=round(math.exp(y) * 100), age_years=15.0, age_band="15-16", gap_days=10,
                        signed_gap_days=10, source_year=2025, target_year=2025, region="R",
                        source_meet_id=f"m-{idx}-{k}-{src}", target_meet_id=f"m-{idx}-{k}-{dst}", is_ratio_outlier=False,
                    )
                )
    return pairs

class EvaluateAndTrainTests(unittest.TestCase):
    def test_ncaa_and_colorado_formulas_match_core_tables(self):
        # 100 Free Women SCY 50.00 -> LCM: 50.00 / 0.874 = 57.2082... -> 57.20
        self.assertEqual(predict_ncaa_cs(5000, "SCY", "LCM", "freestyle", 100, "women"), 5720)
        # 100 Free Women LCM 57.20 -> SCY: 57.20 * 0.874 = 49.9928 -> 49.99
        self.assertEqual(predict_ncaa_cs(5720, "LCM", "SCY", "freestyle", 100, "women"), 4999)
        # 500 Free Men SCY 4:30.00 -> 400 LCM: 270.00 / 1.105 = 244.3438... -> 4:04.34
        self.assertEqual(predict_ncaa_cs(27000, "SCY", "LCM", "freestyle", 500, "men"), 24434)
        # Colorado 100 Free SCY 50.00 -> LCM: 50.00 * 1.11 + 1.6 = 57.10
        self.assertEqual(predict_colorado_cs(5000, "SCY", "LCM", "freestyle", 100), 5710)
        # Colorado 500 Free SCY 300.00 -> 400 LCM: 300.00 * 0.8925 = 267.75
        self.assertEqual(predict_colorado_cs(30000, "SCY", "LCM", "freestyle", 500), 26775)

    def test_best_of_meet_and_hygiene_filtering(self):
        records = [
            # Same meet prelim + final -> only fastest (52.00) survives
            SwimRecord("src", "r1", "s1", "m1", date(2025, 3, 1), "SCY", 100, "freestyle", "women", 5310, 15.0, "RegA"),
            SwimRecord("src", "r2", "s1", "m1", date(2025, 3, 1), "SCY", 100, "freestyle", "women", 5200, 15.0, "RegA"),
            # Implausible 10.00 s 100 free -> excluded
            SwimRecord("src", "r3", "s2", "m1", date(2025, 3, 1), "SCY", 100, "freestyle", "women", 1000, 15.0, "RegA"),
            # Non-canonical 50 back -> excluded
            SwimRecord("src", "r4", "s3", "m1", date(2025, 3, 1), "SCY", 50, "backstroke", "women", 2800, 12.0, "RegA"),
        ]
        dedup, stats = deduplicate_best_of_meet(records)
        self.assertEqual([r.race_id for r in dedup], ["r2"])
        self.assertEqual(stats["same_meet_slower_rounds_collapsed"], 1)
        self.assertEqual(stats["excluded_implausible_time"], 1)
        self.assertEqual(stats["excluded_non_ncaa_event"], 1)

    def test_yard_400_free_is_not_the_500_free_bucket_and_400_im_is_kept(self):
        # A 400 yd freestyle swim passes the plausibility floor shared with the 400 yd IM, but it is
        # not the 500 yd / 400 m event and must not pair with a 400 m free.
        self.assertIsNone(canonical_event_key("SCY", "freestyle", 400))
        self.assertIsNone(canonical_event_key("SCY", "freestyle", 800))
        self.assertIsNone(canonical_event_key("SCY", "freestyle", 1500))
        self.assertEqual(canonical_event_key("SCY", "freestyle", 500), "400-FR")
        self.assertEqual(canonical_event_key("SCY", "individual-medley", 400), "400-IM")
        self.assertEqual(canonical_event_key("LCM", "freestyle", 400), "400-FR")
        day = date(2025, 6, 1)
        swims = [
            SwimRecord("src", "y400", "s1", "m1", day, "SCY", 400, "freestyle", "women", 26000, 16.0, "RegA"),
            SwimRecord("src", "l400", "s1", "m2", day + timedelta(days=5), "LCM", 400, "freestyle", "women", 29000, 16.0, "RegA"),
            SwimRecord("src", "yim", "s1", "m1", day, "SCY", 400, "individual-medley", "women", 29000, 16.0, "RegA"),
            SwimRecord("src", "lim", "s1", "m2", day + timedelta(days=5), "LCM", 400, "individual-medley", "women", 32500, 16.0, "RegA"),
        ]
        dedup, stats = deduplicate_best_of_meet(swims)
        self.assertEqual(sorted(r.race_id for r in dedup), ["l400", "lim", "yim"])
        self.assertEqual(stats["excluded_non_ncaa_event"], 1)
        # Pairing guards the same way even when handed swims that skipped deduplication.
        pairs = build_directional_pairs(swims, max_days=30)
        self.assertEqual({(p.event_key, p.direction) for p in pairs}, {("400-IM", "SCY->LCM"), ("400-IM", "LCM->SCY")})

    def test_deming_slope_matches_known_cases(self):
        # Noise-free line y = 0.9 x: any error ratio recovers the slope exactly.
        x = np.array([1.0, 2.0, 3.0, 4.0])
        y = 0.9 * x
        sxx, syy, sxy = float(np.var(x)), float(np.var(y)), float(np.mean((x - x.mean()) * (y - y.mean())))
        for delta in (0.25, 1.0, 4.0):
            self.assertAlmostEqual(deming_slope(sxx, syy, sxy, delta), 0.9, places=12)
        # Noisy y and x: delta -> infinity approaches OLS (sxy/sxx), delta -> 0 approaches syy/sxy.
        sxx, syy, sxy = 1.0, 1.2, 0.9
        self.assertAlmostEqual(deming_slope(sxx, syy, sxy, 1e9), sxy / sxx, places=5)
        self.assertAlmostEqual(deming_slope(sxx, syy, sxy, 1e-9), syy / sxy, places=5)

    def test_shrinkage_moves_thin_cells_further_toward_their_prior(self):
        priors = {k: Posterior(0.0, 0.0, 0.0) for k in ("dense", "thin", "missing", "a", "b")}
        estimates = {"dense": (0.02, 1e-6), "thin": (0.02, 1e-3), "a": (-0.01, 1e-6), "b": (0.005, 1e-6)}
        post, tau2 = shrink_toward(estimates, priors)
        self.assertGreater(tau2, 0.0)
        self.assertGreater(post["dense"].own_share, post["thin"].own_share)
        self.assertGreater(abs(post["dense"].value), abs(post["thin"].value))
        self.assertEqual(post["missing"].value, 0.0)
        self.assertEqual(post["missing"].own_share, 0.0)

    def test_repeat_noise_pools_courses_without_enough_repeats(self):
        rng = random.Random(3)
        repeats = [RepeatSwim(f"s{i}", "train", "SCY", "100-FR", "R", 2025, rng.gauss(0, 0.03)) for i in range(400)]
        repeats += [RepeatSwim(f"s{i}", "train", "LCM", "100-FR", "R", 2025, rng.gauss(0, 0.02)) for i in range(400)]
        # 300 SCM repeats from only ten swimmers: too few swimmers to measure SCM on its own.
        repeats += [RepeatSwim(f"s{i % 10}", "train", "SCM", "100-FR", "R", 2025, 0.5) for i in range(300)]
        noise = estimate_course_noise(repeats)
        self.assertAlmostEqual(noise[("SCY", "100-FR")], 0.03**2 / 2, delta=0.0001)
        self.assertAlmostEqual(noise[("LCM", "100-FR")], 0.02**2 / 2, delta=0.0001)
        self.assertAlmostEqual(noise[("SCM", "100-FR")], (noise[("SCY", "100-FR")] + noise[("LCM", "100-FR")]) / 2)

    def test_equivalence_model_recovers_latent_scales_and_is_consistent(self):
        swims = latent_swims(1500)
        dedup, _ = deduplicate_best_of_meet(swims)
        pairs = build_directional_pairs(dedup, max_days=30)
        noise = {(c, "100-FR"): 0.015**2 for c in ("SCY", "SCM", "LCM")}
        model = EquivalenceModel()
        model.fit([p for p in pairs if p.partition == "train"], noise)
        cell = model.linear[("100-FR", "women")]
        self.assertEqual(cell["SCY"][1], 1.0)
        self.assertAlmostEqual(cell["LCM"][1], 0.95, delta=0.015)
        self.assertAlmostEqual(cell["SCM"][1], 0.97, delta=0.015)
        # At the SCY anchor, each course sits at its latent location.
        anchor = cell["SCY"][0]
        self.assertAlmostEqual(cell["LCM"][0], 4.24 + 0.95 * (anchor - 4.10), delta=0.004)
        self.assertAlmostEqual(cell["SCM"][0], 4.22 + 0.97 * (anchor - 4.10), delta=0.004)
        # The exported maps invert and compose exactly before truncation, inside and beyond the data.
        tables = model.tables[("100-FR", "women")]
        self.assertEqual(tables["SCY"][0][0], tables["SCY"][0][1])
        for seconds in (30.0, 55.0, 80.0):
            x = math.log(seconds)
            latent = knot_map(tables["SCY"], x, inverse=True)
            to_lcm = knot_map(tables["LCM"], latent, inverse=False)
            self.assertAlmostEqual(knot_map(tables["SCY"], knot_map(tables["LCM"], to_lcm, inverse=True), inverse=False), x, places=12)
            via_scm = knot_map(tables["LCM"], knot_map(tables["SCM"], knot_map(tables["SCM"], latent, inverse=False), inverse=True), inverse=False)
            self.assertAlmostEqual(via_scm, to_lcm, places=12)
        # The exported map is the reconciled linear map at the edges of the training support.
        for u, v in tables["LCM"]:
            self.assertAlmostEqual(v, cell["LCM"][0] + cell["LCM"][1] * (u - anchor), delta=2e-6)
        # Every exported direction lists low evidence for thin cells only (unpaired events here).
        low = model.low_evidence_cells()
        self.assertNotIn("SCY->LCM|100-FR|women", low)
        self.assertIn("SCY->LCM|200-FR|women", low)

    def test_knot_maps_invert_exactly_and_hold_the_edge_ratio_beyond_the_data(self):
        knots = [(4.0, 4.1), (4.2, 4.33), (4.5, 4.6)]
        for u in (3.7, 4.0, 4.05, 4.2, 4.37, 4.5, 4.9):
            v = knot_map(knots, u, inverse=False)
            self.assertAlmostEqual(knot_map(knots, v, inverse=True), u, places=12)
        # Slope 1 in log time beyond the outer knots: the time ratio at the edge is held constant.
        self.assertAlmostEqual(knot_map(knots, 3.5, inverse=False), 4.1 - 0.5, places=12)
        self.assertAlmostEqual(knot_map(knots, 5.0, inverse=False), 4.6 + 0.5, places=12)
        self.assertAlmostEqual(knot_map(knots, 4.1, inverse=False), 4.1 + 0.1 * (0.23 / 0.2), places=12)

    def test_engine_arithmetic_truncates_the_equivalent_time_once(self):
        identity = [(math.log(10.0), math.log(10.0)), (math.log(200.0), math.log(200.0))]

        def ratio(r):
            return [(u, v + math.log(r)) for u, v in identity]

        # 50.00 * 1.1 = 55.0000...: truncation must not lose the hundredth at an exact value.
        self.assertEqual(engine_equivalence_cs(identity, ratio(1.1), 5000), 5500)
        # 50.01 * 1.1 = 55.011 -> 55.01
        self.assertEqual(engine_equivalence_cs(identity, ratio(1.1), 5001), 5501)
        # Converting back uses the same maps: 55.01 / 1.1 = 50.009... -> 50.00
        self.assertEqual(engine_equivalence_cs(ratio(1.1), identity, 5501), 5000)
        # Inside and outside the joint support.
        self.assertFalse(engine_equivalence(identity, ratio(1.1), 5000).out_of_range)
        self.assertTrue(engine_equivalence(identity, ratio(1.1), 500).out_of_range)
        # A result that truncates to zero is rejected like the engine's unsafe-result outcome.
        self.assertIsNone(engine_equivalence_cs(identity, ratio(0.5), 1))

    def test_out_of_range_beats_low_evidence_and_precision_ranges_apply_at_the_entered_time(self):
        inside = EquivalentTime(5000, 4.0, False)
        self.assertIsNone(conversion_caveat(inside, "k", set(), (3.9, 4.1)))
        self.assertEqual(conversion_caveat(inside, "k", {"k"}, (3.9, 4.1)), "empirical-low-evidence")
        self.assertEqual(conversion_caveat(inside, "k", set(), (4.05, 4.1)), "empirical-low-evidence")
        self.assertEqual(conversion_caveat(inside, "k", set(), None), "empirical-low-evidence")
        self.assertEqual(conversion_caveat(EquivalentTime(5000, 4.0, True), "k", {"k"}, None), "empirical-out-of-range")

    def test_pairs_share_one_outlier_screen_in_both_directions(self):
        day = date(2025, 6, 1)
        # Near the 18% geometry screen the forward and reverse ratios differ; one screen per pair.
        for lcm_cs in range(7700, 8400, 25):
            swims = [
                SwimRecord("src", "y", "s1", "m1", day, "SCY", 100, "freestyle", "women", 6000, 15.0, "R"),
                SwimRecord("src", "l", "s1", "m2", day + timedelta(days=3), "LCM", 100, "freestyle", "women", lcm_cs, 15.0, "R"),
            ]
            pairs = build_directional_pairs(swims, max_days=30)
            self.assertEqual(len(pairs), 2)
            self.assertEqual(pairs[0].is_ratio_outlier, pairs[1].is_ratio_outlier, lcm_cs)

    def test_anchored_percentile_baseline_inverts_and_composes(self):
        swims = latent_swims(800, seed=5)
        dedup, _ = deduplicate_best_of_meet(swims)
        pairs = build_directional_pairs(dedup, max_days=30)
        model = AnchoredPercentileModel(age_aware=False)
        model.fit([p for p in pairs if p.partition == "train"])
        # Exact inverse and composition before truncation (tied quantile knots can stretch a
        # truncation after it, which the receipt reports).
        for p in [p for p in pairs if p.partition == "test"][:200]:
            x = math.log(p.source_time_cs)
            latent = model._to_latent(p, p.source_course, x)
            y = model._from_latent(p, p.target_course, latent)
            self.assertAlmostEqual(model._to_latent(p, p.source_course, model._from_latent(p, p.source_course, model._to_latent(p, p.target_course, y))), latent, places=9)
            self.assertAlmostEqual(model._from_latent(p, p.source_course, model._to_latent(p, p.target_course, y)), x, places=9)

    def test_parity_fixture_covers_every_cell_and_direction_with_entered_distances(self):
        def course(loc, scale):
            return {"knots": [[6.8, loc + scale * (6.8 - 6.9)], [7.0, loc + scale * 0.1]]}

        snapshot = {
            "source": {"sha256": "abc"},
            "lowEvidenceCells": ["SCY->LCM|1500-FR|men", "LCM->SCY|1500-FR|men"],
            "preciseLatentRanges": {"SCY->SCM|1500-FR|men": [6.8, 7.0]},
            "cells": {
                "1500-FR|men": {"SCY": course(6.9, 1.0), "SCM": course(6.91, 0.98), "LCM": course(6.93, 0.98)},
                "100-BK|women": {"SCY": course(4.1, 1.0), "SCM": course(4.2, 0.99), "LCM": course(4.25, 0.95)},
            },
        }
        fixture = build_empirical_parity_fixture(snapshot)
        self.assertEqual(fixture["cellsSha256"], "abc")
        self.assertEqual(len(fixture["cases"]), 2 * 6 * 6)
        mile_from_yards = [c for c in fixture["cases"] if c["cell"].startswith("SCY->") and "1500-FR" in c["cell"]]
        self.assertTrue(all(c["event"] == {"distance": 1650, "stroke": "freestyle", "course": "SCY"} for c in mile_from_yards))
        caveats = {c.get("expectedCaveat") for c in fixture["cases"] if "expectedHundredths" in c}
        # Probes beyond the support are out of range; unlisted precision makes the rest low-evidence;
        # SCY->SCM 1500 men inside its precise range carries no caveat.
        self.assertEqual(caveats, {"empirical-out-of-range", "empirical-low-evidence", None})
        for case in fixture["cases"]:
            event_key, category = case["cell"].split("|", 1)[1].split("|")
            src, dst = case["cell"].split("|")[0].split("->")
            courses = snapshot["cells"][f"{event_key}|{category}"]
            minutes, _, rest = case["time"].rpartition(":")
            entered = (int(minutes) * 6000 if minutes else 0) + int(round(float(rest) * 100))
            expected = engine_equivalence_cs(courses[src]["knots"], courses[dst]["knots"], entered)
            self.assertEqual(case.get("expectedHundredths"), expected)
            self.assertEqual(case.get("expectedStatus") == "invalid", expected is None)

    def test_shipped_snapshot_inverts_and_composes_at_every_plausible_hundredth(self):
        snapshot = json.loads((ROOT / "data/empirical.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["schemaVersion"], 3)
        self.assertEqual(len(snapshot["cells"]), 28)
        for cell_key, courses in snapshot["cells"].items():
            for course, table in courses.items():
                knots = table["knots"]
                self.assertGreaterEqual(len(knots), 2, f"{cell_key} {course}")
                # Strictly increasing in both coordinates: the map is monotone and invertible.
                for a, b in zip(knots, knots[1:]):
                    self.assertGreater(b[0], a[0], f"{cell_key} {course}")
                    self.assertGreater(b[1], a[1], f"{cell_key} {course}")
        props = snapshot_arithmetic_properties(snapshot)
        self.assertLess(props["unrounded_roundtrip_max_abs_log_error"], 1e-12)
        self.assertLessEqual(props["roundtrip_max_error_hundredths"], 5)
        self.assertLessEqual(props["transitivity_max_difference_hundredths"], 5)
        self.assertEqual(props["monotonicity_violations"], 0)

    def test_shipped_snapshot_and_evaluation_receipt_provenance_match(self):
        ev = json.loads((ROOT / "research/conversion-model/evaluation-checkpoint-08.json").read_text(encoding="utf-8"))
        emp = json.loads((ROOT / "data/empirical.json").read_text(encoding="utf-8"))
        script_sha = hashlib.sha256((ROOT / "research/conversion-model/evaluate_and_train.py").read_bytes()).hexdigest()
        self.assertEqual(ev["model_metadata"]["evaluator_script_sha256"], script_sha)
        self.assertEqual(emp["source"]["evaluator_sha256"], script_sha)
        payload = {k: emp[k] for k in ("schemaVersion", "cells", "lowEvidenceCells", "preciseLatentRanges")}
        cells_sha = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(ev["model_metadata"]["exported_empirical_cells_sha256"], cells_sha)
        self.assertEqual(emp["source"]["sha256"], cells_sha)
        for key in ("loaded_swims_sha256", "iceberg_snapshot_id", "lakehouse_input_sha256"):
            self.assertIsNotNone(ev["input_provenance"][key])
            self.assertEqual(emp["source"][key], ev["input_provenance"][key])
        self.assertTrue(ev["exported_to_engine"])
        # The snapshot flags exactly the cells the receipt counts as low-evidence, in both directions.
        support = ev["model_metadata"]["cell_support"]
        flagged = {k for k, v in support["cells"].items() if v["low_evidence"]}
        self.assertEqual(len(flagged), support["cells_low_evidence"])
        self.assertEqual(len(emp["lowEvidenceCells"]), 2 * len(flagged))
        for key in flagged:
            src_dst, ev_key, cat = key.split("|")
            src, dst = src_dst.split("->")
            self.assertIn(f"{dst}->{src}|{ev_key}|{cat}", emp["lowEvidenceCells"])
        # The receipt states what its intervals do not cover.
        self.assertIn("model-selection", ev["interval_disclosure"])

    def test_linear_map_recovers_a_known_equivalence_under_unequal_course_noise(self):
        # Estimator correctness under the model's own assumptions: independent per-swim noise, the
        # true noise variances supplied, every course pair observed and many swimmers. Where the
        # pair-mean diagnostic trends even for the true map (unequal course noise: a ratio of 1.28
        # between LCM and SCY, and a stress case of 16), the fit must still recover the conversion.
        # It does not test swimmer-specific course aptitude, which repeat swims cannot measure.
        for sd in ({"SCY": 0.020, "LCM": 0.020 * math.sqrt(1.28), "SCM": 0.018}, {"SCY": 0.008, "LCM": 0.032, "SCM": 0.016}):
            model = EquivalenceModel()
            model.fit(known_pairs(20000, sd), {(c, "100-FR"): v * v for c, v in sd.items()})
            tables = model.tables[("100-FR", "women")]
            for src, dst in (("SCY", "LCM"), ("LCM", "SCY"), ("SCY", "SCM"), ("SCM", "LCM")):
                for seconds in (50.0, 60.0, 70.0, 80.0):
                    a = math.log(seconds) if src == "SCY" else 4.10 + (math.log(seconds) - KNOWN_MAPS[src][0]) / KNOWN_MAPS[src][1]
                    x = KNOWN_MAPS[src][0] + KNOWN_MAPS[src][1] * (a - 4.10)
                    true = KNOWN_MAPS[dst][0] + KNOWN_MAPS[dst][1] * (a - 4.10)
                    fitted = knot_map(tables[dst], knot_map(tables[src], x, inverse=True), inverse=False)
                    # 0.15% of the time: under a tenth of a second at a minute.
                    self.assertLess(abs(fitted - true), 0.0015, f"{sd} {src}->{dst} at {seconds}s")

    def test_repeated_rows_add_no_evidence_influence_or_confidence(self):
        noise = {(c, "100-FR"): 0.02**2 for c in ("SCY", "LCM", "SCM")}
        base = known_pairs(400, {"SCY": 0.02, "LCM": 0.02, "SCM": 0.02}, seed=5, pairs_each=2)
        # Every row of a quarter of the swimmers, repeated five times over.
        tripled = base + [p for p in base if int(p.swimmer_key.split("-")[1]) % 4 == 0] * 4
        fitted = []
        for pairs in (base, tripled):
            model = EquivalenceModel()
            model.fit(pairs, noise)
            fitted.append(model)
        key = ("SCY->LCM", "100-FR", "women")
        a, b = fitted
        for field in ("center", "shift", "shift_var", "log_slope", "log_slope_var", "effective_swimmers"):
            self.assertAlmostEqual(getattr(a.lines[key], field), getattr(b.lines[key], field), places=12, msg=field)
        self.assertEqual(a.lines[key].swimmers, b.lines[key].swimmers)
        for post in ("shift_post", "slope_post", "event_shift_post"):
            for k, v in getattr(a, post).items():
                self.assertAlmostEqual(v.value, getattr(b, post)[k].value, places=12, msg=f"{post} {k}")
                self.assertAlmostEqual(v.own_share, getattr(b, post)[k].own_share, places=12, msg=f"{post} {k}")
        self.assertEqual(a.tables, b.tables)
        # The repeat-swim noise estimate and the flat baseline weigh swimmers the same way.
        rng = random.Random(4)
        repeats = [RepeatSwim(f"r{i}", "train", c, "100-FR", "R", 2025, rng.gauss(0, 0.02)) for c in ("SCY", "LCM") for i in range(250)]
        extra = [r for r in repeats if int(r.swimmer_key[1:]) % 4 == 0] * 9
        self.assertEqual(estimate_course_noise(repeats), estimate_course_noise(repeats + extra))
        flats = []
        for pairs in (base, tripled):
            flat = FlatMultiplierModel()
            flat.fit(pairs)
            flats.append(flat.factors)
        self.assertEqual(flats[0], flats[1])
        # Ten swimmers stay ten, and stay low-evidence, however often their rows repeat.
        few = known_pairs(10, {"SCY": 0.02, "LCM": 0.02, "SCM": 0.02}, seed=9)
        for copies in (1, 20):
            model = EquivalenceModel()
            model.fit(few * copies, noise)
            self.assertAlmostEqual(model.lines[key].effective_swimmers, 10.0, places=9)
            self.assertTrue(model.is_low_evidence(key))

    def test_independent_swim_is_a_month_from_both_pair_swims(self):
        # A Jan 1 SCY / Jan 31 LCM pair: a Feb 1 SCY swim is 31 days from the SCY swim but one day from
        # the LCM swim, so it is not separate; a Mar 3 SCY swim is (61 and 31 days).
        pair = known_pairs(1, {"SCY": 0.0, "LCM": 0.0, "SCM": 0.0})[0]
        pair = replace(pair, source_date=date(2026, 1, 1), target_date=date(2026, 1, 31))
        key = (pair.swimmer_key, "SCY", "100-FR", "women")
        for later, expected in ((date(2026, 2, 1), 0), (date(2026, 3, 3), 1)):
            _, coverage = independent_swim_deciles([pair], {key: [(later, "m-other", 4.0)]}, min_pairs=1)
            self.assertEqual(coverage["rows_with_independent_swim"], expected, later)

    def test_flat_multiplier_baseline_is_directional_and_shrunk(self):
        swims = latent_swims(300)
        dedup, _ = deduplicate_best_of_meet(swims)
        pairs = build_directional_pairs(dedup, max_days=30)
        flat = FlatMultiplierModel()
        flat.fit([p for p in pairs if p.partition == "train"])
        # Fitted cells use the data; unseen events fall back toward pool geometry.
        self.assertAlmostEqual(flat.factors[("SCY->LCM", "100-FR", "women")], math.exp(0.14), delta=0.02)
        self.assertIn(("LCM->SCY", "200-BK", "men"), flat.factors)

    def test_pipeline_receipt_reports_equivalence_properties(self):
        swims = latent_swims(900, seed=11, second_scy=True)
        report = run_pipeline(swims, input_label="synthetic-test", max_days=30, venues_csv=None, n_boot=100, precision_boot=20)
        holdout = report["swimmer_disjoint_holdout"]
        self.assertIn("turnmark_equivalence", holdout["clean_test"])
        self.assertLess(holdout["clean_test"]["turnmark_equivalence"]["mae_seconds"], holdout["clean_test"]["ncaa_2025_27"]["mae_seconds"])
        closure = holdout["roundtrip_and_transitivity_on_test_swims"]["turnmark_equivalence"]
        self.assertLessEqual(closure["roundtrip_closure"]["max_abs_seconds"], 0.05)
        self.assertLessEqual(closure["transitivity_via_third_course"]["max_abs_seconds"], 0.05)
        bias = holdout["ability_bias_by_pair_mean_decile"]["swimmer_clustered"]["turnmark_equivalence"]
        spread = bias["tail_spread_forward_D1_minus_D10"]
        self.assertLess(spread["ci95_low"], 0.0 + 0.6)
        self.assertGreater(spread["ci95_high"], 0.0 - 0.6)
        self.assertIn("percentile_same_input", holdout["percentile_preservation"])
        self.assertIn("comparisons_vs_ncaa_2025_27", holdout["bootstrap_mae"]["swimmer_clustered"]["overall_clean_test"])
        self.assertIn("clusters", holdout["bootstrap_mae"]["meet_clustered_overall"])
        self.assertIn("converted", holdout["fast_swimmer_example"])
        self.assertLessEqual(report["snapshot_arithmetic"]["roundtrip_max_error_hundredths"], 5)
        curvature = report["model_metadata"]["validation_curvature"]
        self.assertIn("turnmark_equivalence", curvature["ability_bias_by_independent_swim_decile"])
        self.assertGreater(curvature["ability_bias_by_independent_swim_decile"]["coverage"]["rows_in_deciles"], 0)
        self.assertIn("ability_bias_by_independent_swim_decile", holdout)
        self.assertFalse(report["exported_to_engine"])

    def test_temporal_and_region_holdouts_share_no_swimmers_with_training(self):
        base = date(2025, 6, 1)
        swims: list[SwimRecord] = []
        regions = ["Pacific Swimming", "Southeastern Swimming"]
        for idx in range(240):
            sid = f"sw-{idx}"
            for year_offset in (0, 365):
                day = base + timedelta(days=year_offset)
                # Some swimmers race in both a held-out and a training region
                region_a = regions[idx % 2]
                region_b = regions[(idx // 2) % 2]
                swims.append(SwimRecord("src", f"y-{idx}-{year_offset}", sid, f"ma-{idx}-{year_offset}", day, "SCY", 100, "freestyle", "women", 5400 + idx, 15.0, region_a))
                swims.append(SwimRecord("src", f"l-{idx}-{year_offset}", sid, f"mb-{idx}-{year_offset}", day + timedelta(days=10), "LCM", 100, "freestyle", "women", 6150 + idx, 15.0, region_b))
        dedup, _ = deduplicate_best_of_meet(swims)
        pairs = build_directional_pairs(dedup, max_days=30)
        repeats = [
            RepeatSwim(f"src|sw-{i}", p, "SCY", "100-FR", r, y, 0.0)
            for i, (p, r, y) in enumerate([("train", "Pacific Swimming", 2025), ("test", "Pacific Swimming", 2026), ("train", "Southeastern Swimming", 2025)])
        ]

        train, test, fit_repeats = temporal_holdout_splits(pairs, repeats)
        self.assertTrue(test)
        self.assertTrue(all(p.source_year >= 2026 for p in test))
        self.assertTrue(all(p.target_year <= 2025 for p in train))
        self.assertFalse({p.swimmer_key for p in test} & {p.swimmer_key for p in train})
        self.assertTrue(all(r.partition == "train" and r.year <= 2025 for r in fit_repeats))

        train, test, fit_repeats = leave_regions_out_splits(pairs, repeats)
        self.assertTrue(test and train)
        self.assertTrue(all(p.region == "Southeastern Swimming" for p in test))
        self.assertFalse({p.swimmer_key for p in test} & {p.swimmer_key for p in train})
        self.assertTrue(all(r.region != "Southeastern Swimming" for r in fit_repeats))

    def test_clustered_bootstrap_resamples_whole_clusters(self):
        clusters = ["a", "a", "b", "b", "c"]
        values = np.array([1.0, 1.0, 3.0, 3.0, np.nan])
        point, boot = clustered_bootstrap(clusters, {"v": values}, n_boot=500, seed=1)
        self.assertAlmostEqual(point["v"], 2.0)
        reps = boot["v"][~np.isnan(boot["v"])]
        # Every replicate is a mix of whole clusters a (1.0) and b (3.0).
        self.assertTrue(np.all((reps >= 1.0) & (reps <= 3.0)))
        self.assertTrue(np.any(reps == 1.0) and np.any(reps == 3.0))

    def test_holm_correction_adjusts_across_families(self):
        def fam(p_value):
            return {"comparisons_vs_ncaa": {"m": {"p_value": p_value}}}

        results = {"a": fam(0.01), "b": fam(0.02), "c": fam(0.04)}
        _apply_holm_correction(results)
        # Holm: 3 * 0.01 = 0.03, max(0.03, 2 * 0.02) = 0.04, max(0.04, 1 * 0.04) = 0.04
        self.assertAlmostEqual(results["a"]["comparisons_vs_ncaa"]["m"]["holm_p_value"], 0.03)
        self.assertAlmostEqual(results["b"]["comparisons_vs_ncaa"]["m"]["holm_p_value"], 0.04)
        self.assertAlmostEqual(results["c"]["comparisons_vs_ncaa"]["m"]["holm_p_value"], 0.04)
        self.assertTrue(results["c"]["comparisons_vs_ncaa"]["m"]["significant_after_holm_0_05"])


if __name__ == "__main__":
    unittest.main()
