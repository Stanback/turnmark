"""Pairing-window experiment for the Turnmark equivalence model: which TRAINING window is best?

The shipped fit pairs swims within 30 days. `window_sensitivity_test` in evaluate_and_train.py scores
that one 30-day model on test pairs built at other windows; it cannot say which training window
fits best. This script fits one equivalence model (and one flat multiplier) per training window
(14, 30, 60, 90 days) on training-partition pairs only, with everything else as shipped: the same
swimmer-hash partitions, the same course noise from 30-day same-course repeats of training
swimmers, the same shrinkage, reconciliation and 18% ratio screen. Every model is scored on one
fixed test set (clean test-partition pairs within 14 days) and, secondarily, the 30-day test set.

Also reported: swimmer-clustered bootstrap intervals for each window's MAE difference from the
30-day model, the less-coupled independent-swim ability-decile bias, and a seasonal check (within
each training window, how often the LCM swim of an SCY-LCM pair is the later one, and how the
fitted SCY->LCM ratio at one typical time moves as the window widens).

Output is aggregate only: no swimmer-level rows, identity keys or individual times.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from evaluate_and_train import (
    ALL_DIRECTIONS,
    DirectionalPair,
    EquivalenceModel,
    FlatMultiplierModel,
    _delta_summary,
    _interval,
    ability_bias_bootstrap,
    build_directional_pairs,
    build_instrument_index,
    build_repeat_swims,
    clustered_bootstrap,
    compute_metrics,
    compute_swims_sha256,
    deduplicate_best_of_meet,
    estimate_course_noise,
    independent_swim_deciles,
    load_swims_from_duckdb,
    mapped_distance,
    measure_lakehouse_view,
    pair_counts,
    predict_ncaa_cs,
    signed_log_errors_pct,
)

TRAINING_WINDOWS = (14, 30, 60, 90)
BASELINE_WINDOW = 30
FIXED_TEST_WINDOW = 14
SECONDARY_TEST_WINDOW = 30
# Shipped repeat-swim window for the noise ratios; held fixed so only the pairing window varies.
NOISE_REPEAT_DAYS = 30
SEED = 20261023
# Typical-time probes for the SCY->LCM ratio drift (time_cs, SCY distance, stroke, category).
RATIO_PROBES = (
    ("women 100 free 58.32", 5832, 100, "freestyle", "women", "100-FR"),
    ("men 100 free 50.50", 5050, 100, "freestyle", "men", "100-FR"),
    ("women 200 free 2:05.00", 12500, 200, "freestyle", "women", "200-FR"),
)


def probe_pair(time_cs: int, distance: int, stroke: str, category: str, event_key: str, src: str = "SCY", dst: str = "LCM") -> DirectionalPair:
    """A synthetic query row (no swimmer) for asking a fitted model one conversion."""
    return DirectionalPair(
        swimmer_key="probe", partition="test", direction=f"{src}->{dst}", event_key=event_key,
        stroke=stroke, source_course=src, target_course=dst, source_distance=distance,
        target_distance=mapped_distance(src, dst, stroke, distance), category=category,
        source_time_cs=time_cs, target_time_cs=0, age_years=None, age_band="unknown", gap_days=0,
        signed_gap_days=0, source_year=2026, target_year=2026, region="probe", source_meet_id="probe",
        target_meet_id="probe", is_ratio_outlier=False,
    )


def seasonal_order(pairs: list[DirectionalPair], a: str = "SCY", b: str = "LCM") -> dict:
    """For clean a<->b pairs, counted once each in the a->b orientation: the share where the b swim
    is strictly later, strictly earlier or the same day, and the mean signed gap (b date - a date)."""
    rows = [p for p in pairs if not p.is_ratio_outlier and p.source_course == a and p.target_course == b]
    gaps = np.array([p.signed_gap_days for p in rows], dtype=np.float64)
    n = len(rows)
    if not n:
        return {"pairs": 0}
    return {
        "pairs": n,
        f"share_{b}_later": round(float((gaps > 0).mean()), 4),
        f"share_{b}_earlier": round(float((gaps < 0).mean()), 4),
        "share_same_day": round(float((gaps == 0).mean()), 4),
        f"mean_signed_gap_days_{b}_minus_{a}": round(float(gaps.mean()), 2),
        "mean_abs_gap_days": round(float(np.abs(gaps).mean()), 2),
    }


def abs_errors_s(pairs: list[DirectionalPair], fn) -> np.ndarray:
    """Absolute error in seconds per row; NaN where the method has no conversion (never silently
    replaced, so a missing prediction drops the row from that column instead of scoring it)."""
    out = np.full(len(pairs), np.nan)
    for i, p in enumerate(pairs):
        pred = fn(p)
        if pred is not None:
            out[i] = abs(pred - p.target_time_cs) / 100.0
    return out


def score(test: list[DirectionalPair], fn) -> dict:
    overall = compute_metrics(test, [fn(p) for p in test])
    by_direction = {}
    for d in ALL_DIRECTIONS:
        sub = [p for p in test if p.direction == d]
        m = compute_metrics(sub, [fn(p) for p in sub])
        by_direction[d] = {k: m.get(k) for k in ("evaluated_pairs", "mae_seconds", "signed_bias_seconds")}
    scm = [p for p in test if "SCM" in p.direction]
    m_scm = compute_metrics(scm, [fn(p) for p in scm])
    return {
        "overall": {k: overall.get(k) for k in ("evaluated_pairs", "evaluated_swimmers", "mae_seconds", "median_ae_seconds", "signed_bias_seconds", "mape_percent")},
        "by_direction": by_direction,
        "scm_involving": {k: m_scm.get(k) for k in ("evaluated_pairs", "mae_seconds", "signed_bias_seconds")},
    }


def evaluate_on(test: list[DirectionalPair], predictors: dict, instruments, n_boot: int) -> dict:
    """Score every predictor on one fixed test set, bootstrap MAE differences vs the 30-day model
    (swimmer-clustered, overall and SCM-involving), and the independent-swim decile bias."""
    out = {"test_set": pair_counts(test), "methods": {n: score(test, fn) for n, fn in predictors.items()}}
    errs = {n: abs_errors_s(test, fn) for n, fn in predictors.items()}
    clusters = [p.swimmer_key for p in test]
    base = f"equivalence_{BASELINE_WINDOW}d"
    for family, sel in (
        ("overall", np.arange(len(test))),
        ("scm_involving", np.array([i for i, p in enumerate(test) if "SCM" in p.direction])),
        *((f"dir_{d}", np.array([i for i, p in enumerate(test) if p.direction == d])) for d in ALL_DIRECTIONS),
    ):
        if not len(sel):
            continue
        cols = {f"mae|{n}": e[sel] for n, e in errs.items()}
        for n in errs:
            if n != base:
                cols[f"delta|{n}"] = errs[n][sel] - errs[base][sel]
        point, boot = clustered_bootstrap([clusters[i] for i in sel], cols, n_boot, SEED)
        out.setdefault("bootstrap_mae_swimmer_clustered", {})[family] = {
            "rows": int(len(sel)),
            "swimmers": len({clusters[i] for i in sel}),
            "replicates": n_boot,
            "mae_seconds": {n: _interval(point[f"mae|{n}"], boot[f"mae|{n}"]) for n in errs},
            f"mae_minus_{base}": {n: _delta_summary(point[f"delta|{n}"], boot[f"delta|{n}"]) for n in errs if n != base},
        }
    deciles, coverage = independent_swim_deciles(test, instruments)
    signed = {n: signed_log_errors_pct(test, fn) for n, fn in predictors.items()}
    bias = ability_bias_bootstrap(test, deciles, signed, clusters, n_boot, SEED) if coverage["rows_in_deciles"] else {}
    out["ability_bias_by_independent_swim_decile"] = {
        "coverage": coverage,
        "forward_signed_pct": {
            n: {
                **{d: b["forward"][d] for d in ("D1", "D5", "D10")},
                "tail_spread_D1_minus_D10": b["tail_spread_forward_D1_minus_D10"],
                "forward_decile_range_pct": b["forward_decile_range_pct"],
            }
            for n, b in bias.items()
        },
    }
    return out


def run(duckdb_path: Path, receipt_path: Path, n_boot: int) -> dict:
    t0 = time.monotonic()
    measured = measure_lakehouse_view(duckdb_path)
    shipped = json.loads(receipt_path.read_text(encoding="utf-8"))
    pinned = shipped["input_provenance"]
    if measured["iceberg_snapshot_id"] != pinned["iceberg_snapshot_id"]:
        raise SystemExit(f"view scans snapshot {measured['iceberg_snapshot_id']}, receipt pins {pinned['iceberg_snapshot_id']}")
    swims = load_swims_from_duckdb(duckdb_path)
    swims_sha = compute_swims_sha256(swims)
    if swims_sha != pinned["loaded_swims_sha256"]:
        raise SystemExit("loaded swims do not match the shipped receipt's loaded_swims_sha256")
    dedup, _ = deduplicate_best_of_meet(swims)
    del swims
    t_load = time.monotonic() - t0

    pairs = {w: build_directional_pairs(dedup, max_days=w) for w in TRAINING_WINDOWS}
    repeats = build_repeat_swims(dedup, max_days=NOISE_REPEAT_DAYS)
    noise = estimate_course_noise([r for r in repeats if r.partition == "train"])

    tests = {
        w: [p for p in pairs[w] if p.partition == "test" and not p.is_ratio_outlier]
        for w in (FIXED_TEST_WINDOW, SECONDARY_TEST_WINDOW)
    }
    instruments = build_instrument_index(dedup, (p for t in tests.values() for p in t))

    predictors = {"ncaa_2025_27": lambda p: predict_ncaa_cs(p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category)}
    training, seasonal, ratio_drift = {}, {}, {}
    for w in TRAINING_WINDOWS:
        train = [p for p in pairs[w] if p.partition == "train"]
        eq = EquivalenceModel()
        eq.fit(train, noise)
        flat = FlatMultiplierModel()
        flat.fit(train)
        predictors[f"equivalence_{w}d"] = eq.predict
        predictors[f"flat_multiplier_{w}d"] = flat.predict
        training[f"{w}d"] = {
            **pair_counts(train),
            "low_evidence_course_pair_cells": sum(eq.is_low_evidence(k) for k in eq.shift_post),
            "scm_course_pair_cells_low_evidence": sum(eq.is_low_evidence(k) for k in eq.shift_post if "SCM" in k[0]),
            "scm_course_pair_cells": sum(1 for k in eq.shift_post if "SCM" in k[0]),
        }
        seasonal[f"{w}d"] = seasonal_order(train)
        ratio_drift[f"{w}d"] = {}
        for label, t_cs, dist, stroke, cat, ev in RATIO_PROBES:
            pred = eq.predict(probe_pair(t_cs, dist, stroke, cat, ev))
            flat_pred = flat.predict(probe_pair(t_cs, dist, stroke, cat, ev))
            ratio_drift[f"{w}d"][label] = {
                "equivalence_lcm_seconds": pred / 100.0 if pred else None,
                "equivalence_ratio": round(pred / t_cs, 5) if pred else None,
                "flat_ratio": round(flat_pred / t_cs, 5) if flat_pred else None,
            }

    evaluations = {f"test_{w}d": evaluate_on(tests[w], predictors, instruments, n_boot) for w in tests}
    runtime = time.monotonic() - t0
    return {
        "experiment": "window-experiment-01",
        "evaluated_at": datetime.now(timezone.utc).date().isoformat(),
        "scope": "aggregate pairing-window experiment receipt; no swimmer-level records",
        "question": "Which pairing window should the equivalence model's TRAINING pairs use: 14, 30 (shipped), 60 or 90 days?",
        "design": {
            "training_windows_days": list(TRAINING_WINDOWS),
            "fixed_test": f"clean test-partition pairs within {FIXED_TEST_WINDOW} days (primary)",
            "secondary_test": f"clean test-partition pairs within {SECONDARY_TEST_WINDOW} days",
            "held_fixed": "swimmer-hash 70/15/15 partitions; course noise from 30-day same-course repeats of training swimmers; shrinkage, reconciliation and the 18% ratio screen as shipped",
            "bootstrap": f"{n_boot} swimmer-clustered replicates, seed {SEED}; fitted models held fixed inside replicates",
            "references": "NCAA 2025-27 formula; flat multiplier fitted on each window",
        },
        "input_provenance": {
            "input_label": pinned.get("input_label"),
            "iceberg_snapshot_id": measured["iceberg_snapshot_id"],
            "archive_rows": measured["rows"],
            "loaded_swims_sha256": swims_sha,
            "matches_shipped_receipt": receipt_path.name,
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "noise_repeat_swims_train": sum(1 for r in repeats if r.partition == "train"),
        "training_sets": training,
        "seasonal_scy_lcm_order_in_training": seasonal,
        "scy_to_lcm_ratio_drift": ratio_drift,
        "evaluations": evaluations,
        "runtime_seconds": {"load_and_dedup": round(t_load, 1), "total": round(runtime, 1)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--duckdb", type=Path, required=True, help="queries.duckdb of the pinned lakehouse")
    parser.add_argument("--shipped-receipt", type=Path, default=Path(__file__).resolve().parent / "evaluation-checkpoint-08.json")
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.duckdb, args.shipped_receipt, args.n_boot)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["runtime_seconds"]))


if __name__ == "__main__":
    main()
