"""Offline conversion-model hygiene, balancing, training and apples-to-apples evaluation.

Compares Turnmark's shipped NCAA (2025-27) and Colorado Timing (2026) formulas against:
1. Empirical distribution/percentile equivalence (fitted on Train only),
2. Weighted Huber pace-curve regression (Tier 1 Core: exact NCAA/Colorado input parity),
3. Context-aware Huber + age spline regression (Tier 2: adds optional whole-year age),
4. Bounded histogram gradient-boosted residual trees (Tier 1 Core & Tier 2 Context,
   with explicit missing-value routing and validation early stopping).

All direction pairs (e.g., SCY->LCM and LCM->SCY) are trained as separate directional
models; a fitted model is never inverted. Evaluation covers:
- Swimmer-disjoint 70/15/15 holdout (micro, swimmer-equalized, and macro-cohort averages),
- Later-season temporal holdout (Train/Val <= 2025, Test >= 2026),
- Leave-One-Region-Out (LORO) geographic holdout,
- Speed deciles, age bands, and matching-window sensitivity (14 / 30 / 60 days).

No swimmer-level records or identity keys are written to public artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent.parent
CONVERSIONS_JSON = ROOT / "data/conversions.json"
COLORADO_JSON = ROOT / "data/colorado.json"
DEFAULT_VENUES_CSV = ROOT / "research/conversion-model/data/national-checkpoint-15/meet_venues.csv"

CANONICAL_EVENT_ORDER = (
    "50-FR",
    "100-FR",
    "200-FR",
    "400-FR",
    "800-FR",
    "1500-FR",
    "100-BK",
    "200-BK",
    "100-BR",
    "200-BR",
    "100-FL",
    "200-FL",
    "200-IM",
    "400-IM",
)

EVENT_DISPLAY_LABELS = {
    "50-FR": "50 Free (50Y / 50M)",
    "100-FR": "100 Free (100Y / 100M)",
    "200-FR": "200 Free (200Y / 200M)",
    "400-FR": "500Y / 400M Free",
    "800-FR": "1000Y / 800M Free",
    "1500-FR": "1650Y / 1500M Free",
    "100-BK": "100 Back (100Y / 100M)",
    "200-BK": "200 Back (200Y / 200M)",
    "100-BR": "100 Breast (100Y / 100M)",
    "200-BR": "200 Breast (200Y / 200M)",
    "100-FL": "100 Fly (100Y / 100M)",
    "200-FL": "200 Fly (200Y / 200M)",
    "200-IM": "200 IM (200Y / 200M)",
    "400-IM": "400 IM (400Y / 400M)",
}

SPARSE_AUGMENT_EVENTS = {
    "400-FR",
    "800-FR",
    "1500-FR",
    "200-BK",
    "200-BR",
    "200-FL",
    "400-IM",
}

STROKE_CODE = {
    "freestyle": "FR",
    "backstroke": "BK",
    "breaststroke": "BR",
    "butterfly": "FL",
    "individual-medley": "IM",
}

# Standard events published in both NCAA and Colorado conversion tables.
# (source_course, target_course, stroke, source_distance) -> target_distance
def mapped_distance(source_course: str, target_course: str, stroke: str, distance: int) -> int | None:
    if stroke not in STROKE_CODE:
        return None
    if stroke == "individual-medley":
        if distance in (200, 400):
            return distance
        return None
    if stroke in ("backstroke", "breaststroke", "butterfly"):
        if distance in (50, 100, 200):
            return distance
        return None
    if stroke == "freestyle":
        if distance in (50, 100, 200):
            return distance
        if source_course == "SCY" and target_course in ("LCM", "SCM"):
            return {500: 400, 1000: 800, 1650: 1500}.get(distance)
        if source_course in ("LCM", "SCM") and target_course == "SCY":
            return {400: 500, 800: 1000, 1500: 1650}.get(distance)
        if source_course in ("LCM", "SCM") and target_course in ("LCM", "SCM"):
            if distance in (400, 800, 1500):
                return distance
    return None


# Conservative physical floor (0.95x approximate world bests in centiseconds)
# and ceiling (slowest plausible competitive age-group completion in centiseconds)
# to screen obvious data-entry / distance-mislabeling typos before pairing.
MIN_PLAUSIBLE_CS = {
    ("SCY", 50): 1650,
    ("SCY", 100): 3700,
    ("SCY", 200): 8200,
    ("SCY", 400): 19500,
    ("SCY", 500): 23000,
    ("SCY", 1000): 49000,
    ("SCY", 1650): 82000,
    ("LCM", 50): 1900,
    ("LCM", 100): 4300,
    ("LCM", 200): 9500,
    ("LCM", 400): 21000,
    ("LCM", 800): 43000,
    ("LCM", 1500): 82000,
    ("SCM", 50): 1850,
    ("SCM", 100): 4200,
    ("SCM", 200): 9200,
    ("SCM", 400): 20500,
    ("SCM", 800): 42000,
    ("SCM", 1500): 80000,
}

MAX_PLAUSIBLE_CS = {
    50: 12000,      # 2:00.00
    100: 24000,     # 4:00.00
    200: 48000,     # 8:00.00
    400: 96000,     # 16:00.00
    500: 108000,    # 18:00.00
    800: 180000,    # 30:00.00
    1000: 210000,   # 35:00.00
    1500: 330000,   # 55:00.00
    1650: 360000,   # 60:00.00
}


def load_engine_tables():
    conv = json.loads(CONVERSIONS_JSON.read_text(encoding="utf-8"))
    colo = json.loads(COLORADO_JSON.read_text(encoding="utf-8"))
    return conv, colo


CONV_TABLE, COLO_TABLE = load_engine_tables()


def truncate_cs(seconds: float) -> int:
    """Match crates/turnmark-core/src/engine.rs truncate() -> integer centiseconds."""
    return int(math.floor(seconds * 100.0 + 1e-8))


def ncaa_Factor(course: str, canonical_lcm_dist: int, stroke: str, category: str) -> float | None:
    if course == "SCY":
        return 1.0
    if course == "SCM":
        if stroke == "freestyle":
            val = CONV_TABLE["shortCourseFactors"]["freestyle"].get(str(canonical_lcm_dist))
            if val is not None:
                return float(val)
        return float(CONV_TABLE["shortCourseFactors"]["default"])
    if course == "LCM":
        key = f"{canonical_lcm_dist}-{STROKE_CODE[stroke]}"
        val = CONV_TABLE["longCourseFactors"].get(category, {}).get(key)
        return float(val) if val is not None else None
    return None


def canonical_metric_distance(course: str, stroke: str, distance: int) -> int:
    if course == "SCY" and stroke == "freestyle":
        return {500: 400, 1000: 800, 1650: 1500}.get(distance, distance)
    return distance


def predict_ncaa_cs(
    time_cs: int,
    source_course: str,
    target_course: str,
    stroke: str,
    source_distance: int,
    category: str,
) -> int | None:
    if source_course == target_course:
        return time_cs
    metric_dist = canonical_metric_distance(source_course, stroke, source_distance)
    f_src = ncaa_Factor(source_course, metric_dist, stroke, category)
    f_dst = ncaa_Factor(target_course, metric_dist, stroke, category)
    if f_src is None or f_dst is None:
        return None
    seconds = (time_cs / 100.0) * (f_src / f_dst)
    return truncate_cs(seconds)


def predict_colorado_cs(
    time_cs: int,
    source_course: str,
    target_course: str,
    stroke: str,
    source_distance: int,
) -> int | None:
    if source_course == target_course:
        return time_cs
    metric_dist = canonical_metric_distance(source_course, stroke, source_distance)
    if stroke == "individual-medley" and metric_dist == 100:
        return None
    short = float(COLO_TABLE["shortCourseMultiplier"])
    long_free = stroke == "freestyle" and metric_dist >= 400
    if long_free:
        lf = COLO_TABLE["longFreestyleMultipliers"].get(str(metric_dist))
        inc = COLO_TABLE["longFreestyleMetricOffsets"].get(str(metric_dist))
        if lf is None or inc is None:
            return None
        long_factor = float(lf)
        increment = float(inc)
    else:
        long_factor = short
        per50 = COLO_TABLE["per50Seconds"].get(STROKE_CODE[stroke])
        if per50 is None:
            return None
        increment = float(per50) * float(metric_dist) / 50.0
    yards_increment = 0.0 if long_free else increment
    pair = (source_course, target_course)
    if pair == ("SCY", "SCM"):
        factor, offset = short, 0.0
    elif pair == ("SCM", "SCY"):
        factor, offset = 1.0 / short, 0.0
    elif pair == ("SCY", "LCM"):
        factor, offset = long_factor, yards_increment
    elif pair == ("LCM", "SCY"):
        factor, offset = 1.0 / long_factor, -yards_increment / long_factor
    elif pair == ("SCM", "LCM"):
        factor, offset = 1.0, increment
    elif pair == ("LCM", "SCM"):
        factor, offset = 1.0, -increment
    else:
        return None
    seconds = (time_cs / 100.0) * factor + offset
    if seconds <= 0.0:
        return None
    return truncate_cs(seconds)


def swimmer_partition(source: str, swimmer_id: str) -> str:
    """Deterministic 70/15/15 split by swimmer identity."""
    payload = json.dumps([source, swimmer_id]).encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def age_band_label(age: float | None) -> str:
    if age is None or not math.isfinite(age):
        return "unknown"
    a = int(age)
    if a <= 10:
        return "10u"
    if a <= 12:
        return "11-12"
    if a <= 14:
        return "13-14"
    if a <= 16:
        return "15-16"
    if a <= 18:
        return "17-18"
    return "19+"


@dataclass(frozen=True)
class SwimRecord:
    source: str
    race_id: str
    swimmer_id: str
    meet_id: str
    race_date: date
    course: str
    distance: int
    stroke: str
    category: str
    time_cs: int
    age_years: float | None
    region: str


@dataclass(frozen=True)
class DirectionalPair:
    swimmer_key: str
    partition: str
    direction: str          # e.g., "SCY->LCM" or "LCM->SCY"
    event_key: str          # e.g., "100-FR" or "400-FR" (canonical metric distance + stroke code)
    stroke: str
    source_course: str
    target_course: str
    source_distance: int
    target_distance: int
    category: str
    source_time_cs: int
    target_time_cs: int
    age_years: float | None
    age_band: str
    gap_days: int           # abs(target_date - source_date)
    signed_gap_days: int    # (target_date - source_date).days
    source_year: int
    target_year: int
    region: str
    source_meet_id: str
    target_meet_id: str
    is_ratio_outlier: bool


def is_plausible_swim(course: str, distance: int, time_cs: int) -> bool:
    lo = MIN_PLAUSIBLE_CS.get((course, distance))
    hi = MAX_PLAUSIBLE_CS.get(distance)
    if lo is None or hi is None:
        return False
    return lo <= time_cs <= hi


def is_pair_ratio_outlier(
    source_course: str,
    target_course: str,
    stroke: str,
    source_distance: int,
    source_time_cs: int,
    target_time_cs: int,
    category: str,
) -> bool:
    """Flag extreme non-physiological ratio anomalies (>18% off NCAA baseline)."""
    ncaa_pred = predict_ncaa_cs(
        source_time_cs, source_course, target_course, stroke, source_distance, category
    )
    if ncaa_pred is None or ncaa_pred <= 0:
        return True
    rel_diff = abs(target_time_cs - ncaa_pred) / float(ncaa_pred)
    # Also enforce physical course ordering for same-distance SCY vs LCM (LCM must not be faster than SCY)
    if source_distance == mapped_distance(source_course, target_course, stroke, source_distance):
        if source_course == "SCY" and target_course == "LCM" and target_time_cs < source_time_cs:
            return True
        if source_course == "LCM" and target_course == "SCY" and target_time_cs > source_time_cs:
            return True
    return rel_diff > 0.18


def deduplicate_best_of_meet(records: Iterable[SwimRecord]) -> tuple[list[SwimRecord], dict[str, int]]:
    """Keep best valid swim per (source, swimmer_id, meet_id, course, distance, stroke, category)."""
    stats = Counter()
    best: dict[tuple, SwimRecord] = {}
    for rec in records:
        stats["input_records"] += 1
        if rec.stroke not in STROKE_CODE or rec.category not in ("women", "men"):
            stats["excluded_unsupported_event"] += 1
            continue
        # Exclude 50 BK/BR/FL and 100 IM that are not in NCAA conversion tables
        metric_dist = canonical_metric_distance(rec.course, rec.stroke, rec.distance)
        if ncaa_Factor("LCM", metric_dist, rec.stroke, rec.category) is None:
            stats["excluded_non_ncaa_event"] += 1
            continue
        if not is_plausible_swim(rec.course, rec.distance, rec.time_cs):
            stats["excluded_implausible_time"] += 1
            continue
        key = (
            rec.source,
            rec.swimmer_id,
            rec.meet_id,
            rec.course,
            rec.distance,
            rec.stroke,
            rec.category,
        )
        prev = best.get(key)
        if prev is None or (rec.time_cs, rec.race_date, rec.race_id) < (prev.time_cs, prev.race_date, prev.race_id):
            if prev is not None:
                stats["same_meet_slower_rounds_collapsed"] += 1
            best[key] = rec
        else:
            stats["same_meet_slower_rounds_collapsed"] += 1
    stats["best_of_meet_swims"] = len(best)
    return list(best.values()), dict(stats)


def build_directional_pairs(
    swims: list[SwimRecord],
    max_days: int = 30,
    course_pairs: tuple[tuple[str, str], ...] = (("SCY", "LCM"), ("SCY", "SCM"), ("SCM", "LCM")),
) -> list[DirectionalPair]:
    """Greedy nearest-date one-to-one matching per swimmer and canonical event."""
    by_athlete_event: dict[tuple[str, str, str, int, str], list[SwimRecord]] = defaultdict(list)
    for s in swims:
        metric_dist = canonical_metric_distance(s.course, s.stroke, s.distance)
        by_athlete_event[(s.source, s.swimmer_id, s.stroke, metric_dist, s.category)].append(s)

    directional_pairs: list[DirectionalPair] = []
    for (source, swimmer_id, stroke, metric_dist, category), group in sorted(by_athlete_event.items()):
        part = swimmer_partition(source, swimmer_id)
        swimmer_key = f"{source}|{swimmer_id}"
        event_key = f"{metric_dist}-{STROKE_CODE[stroke]}"
        for c_a, c_b in course_pairs:
            swims_a = [x for x in group if x.course == c_a]
            swims_b = [x for x in group if x.course == c_b]
            if not swims_a or not swims_b:
                continue
            candidates = []
            for a in swims_a:
                for b in swims_b:
                    gap = abs((b.race_date - a.race_date).days)
                    if gap <= max_days:
                        candidates.append((gap, a.race_date, b.race_date, a.race_id, b.race_id, a, b))
            if not candidates:
                continue
            candidates.sort(key=lambda t: t[:5])
            used_a = set()
            used_b = set()
            for gap, _, _, _, _, a, b in candidates:
                if a.race_id in used_a or b.race_id in used_b:
                    continue
                used_a.add(a.race_id)
                used_b.add(b.race_id)
                # Emit forward (c_a -> c_b) and reverse (c_b -> c_a) in the SAME swimmer partition
                for src, dst in ((a, b), (b, a)):
                    age = src.age_years if src.age_years is not None else dst.age_years
                    outlier = is_pair_ratio_outlier(
                        src.course, dst.course, stroke, src.distance, src.time_cs, dst.time_cs, category
                    )
                    directional_pairs.append(
                        DirectionalPair(
                            swimmer_key=swimmer_key,
                            partition=part,
                            direction=f"{src.course}->{dst.course}",
                            event_key=event_key,
                            stroke=stroke,
                            source_course=src.course,
                            target_course=dst.course,
                            source_distance=src.distance,
                            target_distance=dst.distance,
                            category=category,
                            source_time_cs=src.time_cs,
                            target_time_cs=dst.time_cs,
                            age_years=age,
                            age_band=age_band_label(age),
                            gap_days=gap,
                            signed_gap_days=(dst.race_date - src.race_date).days,
                            source_year=src.race_date.year,
                            target_year=dst.race_date.year,
                            region=src.region or dst.region or "unknown",
                            source_meet_id=src.meet_id,
                            target_meet_id=dst.meet_id,
                            is_ratio_outlier=outlier,
                        )
                    )
    return directional_pairs


def compute_training_weights(train_pairs: list[DirectionalPair]) -> list[float]:
    """Composite sample weight w_i = w_swimmer * w_region * w_cohort * w_gap fitted on Train only."""
    if not train_pairs:
        return []
    swimmer_event_counts = Counter((p.swimmer_key, p.direction, p.event_key) for p in train_pairs)
    region_counts = Counter((p.direction, p.region) for p in train_pairs)
    cohort_counts = Counter((p.direction, p.event_key, p.category, p.age_band) for p in train_pairs)

    raw_weights = []
    for p in train_pairs:
        w_swimmer = 1.0 / math.sqrt(max(1, swimmer_event_counts[(p.swimmer_key, p.direction, p.event_key)]))
        w_region = max(1, region_counts[(p.direction, p.region)]) ** (-0.30)
        w_cohort = max(1, cohort_counts[(p.direction, p.event_key, p.category, p.age_band)]) ** (-0.25)
        w_gap = math.exp(-float(p.gap_days) / 21.0)
        raw_weights.append(w_swimmer * w_region * w_cohort * w_gap)

    mean_w = sum(raw_weights) / len(raw_weights)
    return [w / mean_w for w in raw_weights]


def solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting for small dense systems."""
    n = len(b)
    mat = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(mat[r][col]))
        mat[col], mat[pivot] = mat[pivot], mat[col]
        denom = mat[col][col]
        if abs(denom) < 1e-12:
            continue
        for j in range(col, n + 1):
            mat[col][j] /= denom
        for r in range(n):
            if r != col and abs(mat[r][col]) > 0.0:
                factor = mat[r][col]
                for j in range(col, n + 1):
                    mat[r][j] -= factor * mat[col][j]
    return [mat[i][n] for i in range(n)]


def fit_weighted_huber_linear(
    features: list[list[float]],
    targets: list[float],
    weights: list[float],
    delta: float = 80.0,
    ridge: float = 1e-3,
    iterations: int = 8,
) -> list[float]:
    """Iteratively Reweighted Least Squares (IRLS) with Huber loss and L2 regularization."""
    if not features:
        return []
    dim = len(features[0])
    beta = [0.0] * dim
    for _ in range(iterations):
        xtx = [[0.0] * dim for _ in range(dim)]
        xty = [0.0] * dim
        for x, y, w in zip(features, targets, weights):
            pred = sum(beta[j] * x[j] for j in range(dim))
            res = abs(y - pred)
            huber_w = 1.0 if res <= delta else (delta / res)
            eff_w = w * huber_w
            for j in range(dim):
                xty[j] += eff_w * x[j] * y
                for k in range(j, dim):
                    xtx[j][k] += eff_w * x[j] * x[k]
        for j in range(dim):
            for k in range(j):
                xtx[j][k] = xtx[k][j]
            if j > 0:  # Do not regularize intercept
                xtx[j][j] += ridge
        beta = solve_linear_system(xtx, xty)
    return beta


class EmpiricalQuantileModel:
    """Distribution-matching baseline fitted on Train only."""

    def __init__(self, knots: int = 101):
        self.knots = knots
        self.tables: dict[tuple, tuple[list[float], list[float]]] = {}

    @staticmethod
    def _quantiles(sorted_vals: list[int], knots: int) -> list[float]:
        n = len(sorted_vals)
        if n == 1:
            return [float(sorted_vals[0])] * knots
        out = []
        for i in range(knots):
            pos = (i / (knots - 1)) * (n - 1)
            lo = int(math.floor(pos))
            hi = min(n - 1, lo + 1)
            frac = pos - lo
            out.append(sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac)
        return out

    def fit(self, train_pairs: list[DirectionalPair]) -> None:
        by_cell: dict[tuple, list[DirectionalPair]] = defaultdict(list)
        by_open: dict[tuple, list[DirectionalPair]] = defaultdict(list)
        for p in train_pairs:
            if p.is_ratio_outlier:
                continue
            by_cell[(p.direction, p.event_key, p.category, p.age_band)].append(p)
            by_open[(p.direction, p.event_key, p.category, "all")].append(p)

        for key, group in (*by_cell.items(), *by_open.items()):
            if len(group) < 25:
                continue
            src_sorted = sorted(p.source_time_cs for p in group)
            dst_sorted = sorted(p.target_time_cs for p in group)
            self.tables[key] = (
                self._quantiles(src_sorted, self.knots),
                self._quantiles(dst_sorted, self.knots),
            )

    def predict(self, p: DirectionalPair) -> int | None:
        table = self.tables.get((p.direction, p.event_key, p.category, p.age_band))
        if table is None:
            table = self.tables.get((p.direction, p.event_key, p.category, "all"))
        if table is None:
            return predict_ncaa_cs(
                p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
            )
        src_q, dst_q = table
        x = float(p.source_time_cs)
        if x <= src_q[0]:
            ratio = dst_q[0] / max(1.0, src_q[0])
            return max(1, int(round(x * ratio)))
        if x >= src_q[-1]:
            ratio = dst_q[-1] / max(1.0, src_q[-1])
            return max(1, int(round(x * ratio)))
        # Binary search percentile interval
        lo, hi = 0, len(src_q) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if src_q[mid] <= x:
                lo = mid
            else:
                hi = mid
        span = src_q[hi] - src_q[lo]
        frac = 0.0 if span <= 1e-9 else (x - src_q[lo]) / span
        pred = dst_q[lo] + frac * (dst_q[hi] - dst_q[lo])
        return max(1, int(round(pred)))


class HuberPaceModel:
    """Per-(direction, event, category) weighted Huber residual model over NCAA baseline.

    Tier 1 (include_age=False): Uses ONLY (source_time_cs, direction, event, category) —
    exact input parity with NCAA and Colorado Timing.
    Tier 2 (include_age=True): Adds smooth whole-year age basis with explicit missing indicator.
    """

    def __init__(self, include_age: bool = False):
        self.include_age = include_age
        self.models: dict[tuple[str, str, str], tuple[float, float, list[float]]] = {}
        self.cell_counts: dict[tuple[str, str, str], int] = {}
        self.fallback_bias: dict[tuple[str, str], float] = {}

    def _featurize(self, p: DirectionalPair, ref_cs: float, scale_cs: float) -> list[float]:
        z = (p.source_time_cs - ref_cs) / scale_cs
        z_clamped = max(-3.0, min(3.0, z))
        feats = [1.0, z_clamped, z_clamped * z_clamped]
        if self.include_age:
            if p.age_years is None or not math.isfinite(p.age_years):
                feats.extend([0.0, 0.0, 1.0])
            else:
                age_z = (max(8.0, min(22.0, float(p.age_years))) - 14.0) / 4.0
                feats.extend([age_z, max(0.0, 13.0 - float(p.age_years)) / 4.0, 0.0])
        return feats

    def fit(self, train_pairs: list[DirectionalPair], weights: list[float]) -> None:
        clean_pairs = []
        clean_weights = []
        for p, w in zip(train_pairs, weights):
            if not p.is_ratio_outlier:
                clean_pairs.append(p)
                clean_weights.append(w)

        by_cell: dict[tuple[str, str, str], list[tuple[DirectionalPair, float]]] = defaultdict(list)
        by_dir_event: dict[tuple[str, str], list[float]] = defaultdict(list)
        for p, w in zip(clean_pairs, clean_weights):
            ncaa = predict_ncaa_cs(
                p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
            )
            if ncaa is None:
                continue
            by_cell[(p.direction, p.event_key, p.category)].append((p, w))
            by_dir_event[(p.direction, p.event_key)].append(float(p.target_time_cs - ncaa))

        for k, diffs in by_dir_event.items():
            self.fallback_bias[k] = statistics.median(diffs) if diffs else 0.0

        for key, items in by_cell.items():
            if len(items) < 8:
                continue
            times = [p.source_time_cs for p, _ in items]
            ref_cs = float(statistics.median(times))
            scale_cs = max(100.0, float(statistics.pstdev(times) if len(times) > 1 else ref_cs * 0.1))
            feats = []
            targets = []
            ws = []
            for p, w in items:
                ncaa = predict_ncaa_cs(
                    p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
                )
                assert ncaa is not None
                feats.append(self._featurize(p, ref_cs, scale_cs))
                targets.append(float(p.target_time_cs - ncaa))
                ws.append(w)
            delta = max(30.0, ref_cs * 0.02)
            ridge = 0.05 + (1.5 / max(1, len(items)))
            beta = fit_weighted_huber_linear(feats, targets, ws, delta=delta, ridge=ridge)
            # Empirical-Bayes shrinkage toward pooled (direction, event) median residual for smaller cells
            shrink = len(items) / (len(items) + 20.0)
            prior_bias = self.fallback_bias.get((key[0], key[1]), 0.0)
            beta[0] = shrink * beta[0] + (1.0 - shrink) * prior_bias
            for j in range(1, len(beta)):
                beta[j] *= shrink
            # Enforce strict monotonicity over z in [-3, 3]: |b1| + 6*|b2| <= 0.35 * scale_cs * 0.85
            if len(beta) >= 3:
                max_slope_budget = 0.30 * scale_cs
                slope_used = abs(beta[1]) + 6.0 * abs(beta[2])
                if slope_used > max_slope_budget and slope_used > 1e-9:
                    scale_factor = max_slope_budget / slope_used
                    beta[1] *= scale_factor
                    beta[2] *= scale_factor
            self.models[key] = (ref_cs, scale_cs, beta)
            self.cell_counts[key] = len(items)

    def export_snapshot_dict(self, revision: str, evaluated_at: str) -> dict:
        """Export compact deterministic JSON snapshot for crates/turnmark-core (data/empirical.json).

        Each cell stores [refSeconds, scaleSeconds, b0, b1, b2] to keep the embedded
        focused Wasm binary well within the <50% widget size budget.
        """
        if self.include_age:
            raise ValueError("Only Tier 1 Core (include_age=False) can be exported to stateless engine snapshot")
        cells = {}
        for (direction, event_key, category), (ref_cs, scale_cs, beta) in sorted(self.models.items()):
            cells[f"{direction}|{event_key}|{category}"] = [
                round(ref_cs / 100.0, 4),
                round(scale_cs / 100.0, 4),
                *[round(b / 100.0, 5) for b in beta[:3]],
            ]
        fallback = {
            f"{direction}|{event_key}": round(bias_cs / 100.0, 4)
            for (direction, event_key), bias_cs in sorted(self.fallback_bias.items())
            if f"{direction}|{event_key}|men" not in cells or f"{direction}|{event_key}|women" not in cells
        }
        payload = {
            "cells": cells,
            "fallbackOffsetSeconds": fallback,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return {
            "source": {
                "id": "turnmark-empirical-2026",
                "title": "Turnmark Empirical Pace-Curve Model (2010–2026 US Competition Swims)",
                "url": "https://github.com/Stanback/turnmark/blob/main/research/conversion-model/REPORT.md",
                "revision": revision,
                "verified": evaluated_at,
                "sha256": digest,
            },
            **payload,
        }

    def predict_float(self, p: DirectionalPair) -> float | None:
        ncaa = predict_ncaa_cs(
            p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
        )
        if ncaa is None:
            return None
        entry = self.models.get((p.direction, p.event_key, p.category))
        if entry is None:
            bias = self.fallback_bias.get((p.direction, p.event_key), 0.0)
            return float(ncaa) + bias
        ref_cs, scale_cs, beta = entry
        x = self._featurize(p, ref_cs, scale_cs)
        adj = sum(b * f for b, f in zip(beta, x))
        return max(1.0, float(ncaa) + adj)

    def predict(self, p: DirectionalPair) -> int | None:
        val = self.predict_float(p)
        return max(1, int(round(val))) if val is not None else None


class BoundedHistogramGBM:
    """Bounded-depth gradient boosted regression trees over HuberPaceModel base predictions.

    Supports explicit missing-value routing (nan_go_left), L2 leaf regularization,
    and validation early stopping.
    """

    def __init__(
        self,
        include_age: bool = False,
        max_trees: int = 40,
        max_depth: int = 3,
        learning_rate: float = 0.08,
        l2_reg: float = 10.0,
        min_child_weight: float = 25.0,
    ):
        self.include_age = include_age
        self.max_trees = max_trees
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.l2_reg = l2_reg
        self.min_child_weight = min_child_weight
        self.base_model = HuberPaceModel(include_age=include_age)
        self.trees_by_dir: dict[str, list[dict]] = {}
        self.best_tree_count: dict[str, int] = {}
        self.event_codes: dict[str, int] = {}

    def _extract_features(self, p: DirectionalPair) -> list[float | None]:
        ncaa = predict_ncaa_cs(
            p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
        ) or p.source_time_cs
        pace_per_100 = p.source_time_cs * (100.0 / max(25.0, float(p.source_distance)))
        ev_code = float(self.event_codes.get(p.event_key, 0))
        stroke_id = float(["freestyle", "backstroke", "breaststroke", "butterfly", "individual-medley"].index(p.stroke))
        cat_id = 1.0 if p.category == "men" else 0.0
        feats: list[float | None] = [
            float(p.source_time_cs),
            float(ncaa),
            pace_per_100,
            float(p.source_distance),
            stroke_id,
            cat_id,
            ev_code,
        ]
        if self.include_age:
            feats.append(float(p.age_years) if p.age_years is not None else None)
        return feats

    def _build_tree(
        self,
        xs: list[list[float | None]],
        grads: list[float],
        weights: list[float],
        indices: list[int],
        depth: int,
        thresholds: list[list[float]],
    ) -> dict:
        sum_g = sum(grads[i] for i in indices)
        sum_w = sum(weights[i] for i in indices)
        leaf_val = -sum_g / (sum_w + self.l2_reg)
        if depth >= self.max_depth or sum_w < 2.0 * self.min_child_weight or len(indices) < 40:
            return {"leaf": leaf_val}

        base_score = (sum_g * sum_g) / (sum_w + self.l2_reg)
        best_gain = 0.0
        best_split = None
        n_features = len(xs[0])

        for f_idx in range(n_features):
            cand_thresh = thresholds[f_idx]
            if not cand_thresh:
                continue
            for thr in cand_thresh:
                for nan_left in (True, False):
                    g_l = w_l = 0.0
                    for i in indices:
                        v = xs[i][f_idx]
                        go_left = nan_left if v is None else (v <= thr)
                        if go_left:
                            g_l += grads[i]
                            w_l += weights[i]
                    w_r = sum_w - w_l
                    if w_l < self.min_child_weight or w_r < self.min_child_weight:
                        continue
                    g_r = sum_g - g_l
                    gain = (g_l * g_l) / (w_l + self.l2_reg) + (g_r * g_r) / (w_r + self.l2_reg) - base_score
                    if gain > best_gain + 1e-6:
                        best_gain = gain
                        best_split = (f_idx, thr, nan_left)
                    if not self.include_age or f_idx < n_features - 1:
                        break  # Non-missing features only need one nan_left check

        if best_split is None:
            return {"leaf": leaf_val}

        f_idx, thr, nan_left = best_split
        left_idx = []
        right_idx = []
        for i in indices:
            v = xs[i][f_idx]
            go_left = nan_left if v is None else (v <= thr)
            if go_left:
                left_idx.append(i)
            else:
                right_idx.append(i)

        return {
            "feature": f_idx,
            "threshold": thr,
            "nan_left": nan_left,
            "left": self._build_tree(xs, grads, weights, left_idx, depth + 1, thresholds),
            "right": self._build_tree(xs, grads, weights, right_idx, depth + 1, thresholds),
        }

    @staticmethod
    def _eval_tree(node: dict, x: list[float | None]) -> float:
        while "leaf" not in node:
            v = x[node["feature"]]
            go_left = node["nan_left"] if v is None else (v <= node["threshold"])
            node = node["left"] if go_left else node["right"]
        return float(node["leaf"])

    def fit(
        self,
        train_pairs: list[DirectionalPair],
        weights: list[float],
        val_pairs: list[DirectionalPair],
    ) -> None:
        self.base_model.fit(train_pairs, weights)
        all_events = sorted({p.event_key for p in train_pairs})
        self.event_codes = {ev: idx for idx, ev in enumerate(all_events)}

        by_dir_train: dict[str, list[tuple[DirectionalPair, float]]] = defaultdict(list)
        for p, w in zip(train_pairs, weights):
            if not p.is_ratio_outlier:
                by_dir_train[p.direction].append((p, w))

        by_dir_val: dict[str, list[DirectionalPair]] = defaultdict(list)
        for p in val_pairs:
            if not p.is_ratio_outlier:
                by_dir_val[p.direction].append(p)

        for direction, items in sorted(by_dir_train.items()):
            if len(items) < 80:
                continue
            xs = [self._extract_features(p) for p, _ in items]
            ws = [w for _, w in items]
            preds = [self.base_model.predict_float(p) or float(p.source_time_cs) for p, _ in items]
            targets = [float(p.target_time_cs) for p, _ in items]

            # Precompute histogram candidate thresholds (up to 16 quantiles per feature)
            n_features = len(xs[0])
            thresholds: list[list[float]] = []
            for f_idx in range(n_features):
                vals = sorted({x[f_idx] for x in xs if x[f_idx] is not None})
                if len(vals) <= 16:
                    thresholds.append([float(v) for v in vals[:-1]])
                else:
                    step = max(1, len(vals) // 16)
                    thresholds.append([float(vals[idx]) for idx in range(step, len(vals), step)])

            val_items = by_dir_val.get(direction, [])
            val_xs = [self._extract_features(p) for p in val_items]
            val_preds = [self.base_model.predict_float(p) or float(p.source_time_cs) for p in val_items]
            val_targets = [float(p.target_time_cs) for p in val_items]

            best_val_mae = (
                sum(abs(vp - vt) for vp, vt in zip(val_preds, val_targets)) / len(val_targets)
                if val_targets
                else float("inf")
            )
            best_k = 0
            trees: list[dict] = []
            all_idx = list(range(len(items)))

            for t_idx in range(self.max_trees):
                # Huber-clipped gradient (delta = 80 cs)
                grads = []
                for pred, y, w in zip(preds, targets, ws):
                    err = pred - y
                    clipped = max(-80.0, min(80.0, err))
                    grads.append(w * clipped)
                tree = self._build_tree(xs, grads, ws, all_idx, 0, thresholds)
                trees.append(tree)
                for i, x in enumerate(xs):
                    preds[i] += self.learning_rate * self._eval_tree(tree, x)
                if val_targets:
                    for i, vx in enumerate(val_xs):
                        val_preds[i] += self.learning_rate * self._eval_tree(tree, vx)
                    val_mae = sum(abs(vp - vt) for vp, vt in zip(val_preds, val_targets)) / len(val_targets)
                    if val_mae < best_val_mae - 1e-4:
                        best_val_mae = val_mae
                        best_k = t_idx + 1

            self.trees_by_dir[direction] = trees[:best_k] if val_targets else trees
            self.best_tree_count[direction] = len(self.trees_by_dir[direction])

    def predict(self, p: DirectionalPair) -> int | None:
        base = self.base_model.predict_float(p)
        if base is None:
            return None
        trees = self.trees_by_dir.get(p.direction, [])
        if not trees:
            return max(1, int(round(base)))
        x = self._extract_features(p)
        val = base + sum(self.learning_rate * self._eval_tree(t, x) for t in trees)
        return max(1, int(round(val)))


def compute_metrics(pairs: list[DirectionalPair], preds: list[int | None]) -> dict:
    """Compute micro, swimmer-equalized, and macro-cohort metrics in seconds and relative %."""
    abs_errs_sec: list[float] = []
    sq_errs_sec: list[float] = []
    signed_errs_sec: list[float] = []
    rel_abs_errs: list[float] = []
    within_05pct = 0
    within_10pct = 0
    within_20pct = 0
    by_swimmer: dict[str, list[float]] = defaultdict(list)
    by_cohort: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for p, pred in zip(pairs, preds):
        if pred is None:
            continue
        err_cs = pred - p.target_time_cs
        abs_sec = abs(err_cs) / 100.0
        signed_sec = err_cs / 100.0
        rel_err = abs(err_cs) / max(1.0, float(p.target_time_cs))
        abs_errs_sec.append(abs_sec)
        sq_errs_sec.append(abs_sec * abs_sec)
        signed_errs_sec.append(signed_sec)
        rel_abs_errs.append(rel_err)
        if rel_err <= 0.005:
            within_05pct += 1
        if rel_err <= 0.010:
            within_10pct += 1
        if rel_err <= 0.020:
            within_20pct += 1
        by_swimmer[p.swimmer_key].append(abs_sec)
        by_cohort[(p.direction, p.event_key, p.category)].append(abs_sec)

    n = len(abs_errs_sec)
    if n == 0:
        return {"evaluated_pairs": 0}

    sorted_abs = sorted(abs_errs_sec)
    p90_idx = min(n - 1, int(math.floor(0.90 * (n - 1))))
    swimmer_maes = [sum(v) / len(v) for v in by_swimmer.values()]
    qualifying_cohorts = [sum(v) / len(v) for v in by_cohort.values() if len(v) >= 20]
    if not qualifying_cohorts:
        qualifying_cohorts = [sum(v) / len(v) for v in by_cohort.values()]

    return {
        "evaluated_pairs": n,
        "evaluated_swimmers": len(by_swimmer),
        "mae_seconds": round(sum(abs_errs_sec) / n, 4),
        "median_ae_seconds": round(statistics.median(sorted_abs), 4),
        "rmse_seconds": round(math.sqrt(sum(sq_errs_sec) / n), 4),
        "p90_ae_seconds": round(sorted_abs[p90_idx], 4),
        "signed_bias_seconds": round(sum(signed_errs_sec) / n, 4),
        "mape_percent": round(100.0 * sum(rel_abs_errs) / n, 4),
        "within_0_5_pct": round(100.0 * within_05pct / n, 2),
        "within_1_0_pct": round(100.0 * within_10pct / n, 2),
        "within_2_0_pct": round(100.0 * within_20pct / n, 2),
        "swimmer_equalized_mae_seconds": round(sum(swimmer_maes) / len(swimmer_maes), 4),
        "macro_cohort_mae_seconds": round(sum(qualifying_cohorts) / len(qualifying_cohorts), 4),
    }


def augment_sparse_training_pairs(
    train_30: list[DirectionalPair],
    train_60: list[DirectionalPair],
) -> tuple[list[DirectionalPair], dict[str, int]]:
    """Supplement 30-day training pairs with 31-60 day training pairs for sparse events/courses.

    Because swimmer_partition() depends only on (source, swimmer_id), train_60 contains
    exclusively training-partition swimmers and never leaks validation or test swimmers.
    31-60 day pairs are automatically downweighted by exp(-gap_days / 21) in compute_training_weights().
    """
    seen_keys = {
        (
            p.swimmer_key,
            p.direction,
            p.event_key,
            p.source_meet_id,
            p.target_meet_id,
            p.source_time_cs,
            p.target_time_cs,
        )
        for p in train_30
    }
    augmented = list(train_30)
    added_by_event: Counter[str] = Counter()
    for p in train_60:
        if p.partition != "train":
            continue
        is_sparse_target = (p.event_key in SPARSE_AUGMENT_EVENTS) or ("SCM" in p.direction)
        if not is_sparse_target:
            continue
        key = (
            p.swimmer_key,
            p.direction,
            p.event_key,
            p.source_meet_id,
            p.target_meet_id,
            p.source_time_cs,
            p.target_time_cs,
        )
        if key not in seen_keys:
            seen_keys.add(key)
            augmented.append(p)
            added_by_event[p.event_key] += 1
    return augmented, dict(sorted(added_by_event.items()))


class SplitConformalCalibrator:
    """Distribution-free split-conformal prediction intervals calibrated on Validation only.

    Uses relative non-conformity scores |y - y_hat| / max(100, y_hat) per (direction, event_key)
    with fallback to direction, guaranteeing finite-sample exchangeability coverage.
    """

    LEVELS = (0.50, 0.80, 0.90)

    def __init__(self):
        self.quantiles_by_cell: dict[tuple[str, str], dict[float, float]] = {}
        self.quantiles_by_dir: dict[str, dict[float, float]] = {}
        self.global_quantiles: dict[float, float] = {lvl: 0.02 for lvl in self.LEVELS}

    @staticmethod
    def _conformal_quantile(scores: list[float], alpha: float) -> float:
        if not scores:
            return 0.02
        ordered = sorted(scores)
        n = len(ordered)
        rank = min(n - 1, max(0, int(math.ceil((n + 1) * alpha)) - 1))
        return float(ordered[rank])

    def fit(self, val_pairs: list[DirectionalPair], predictor) -> None:
        by_cell: dict[tuple[str, str], list[float]] = defaultdict(list)
        by_dir: dict[str, list[float]] = defaultdict(list)
        all_scores: list[float] = []
        for p in val_pairs:
            if p.is_ratio_outlier:
                continue
            pred = predictor(p)
            if pred is None or pred <= 0:
                continue
            rel_err = abs(p.target_time_cs - pred) / max(100.0, float(pred))
            by_cell[(p.direction, p.event_key)].append(rel_err)
            by_dir[p.direction].append(rel_err)
            all_scores.append(rel_err)

        if all_scores:
            self.global_quantiles = {lvl: self._conformal_quantile(all_scores, lvl) for lvl in self.LEVELS}
        for d, scores in by_dir.items():
            if len(scores) >= 10:
                self.quantiles_by_dir[d] = {lvl: self._conformal_quantile(scores, lvl) for lvl in self.LEVELS}
        for cell, scores in by_cell.items():
            if len(scores) >= 12:
                self.quantiles_by_cell[cell] = {lvl: self._conformal_quantile(scores, lvl) for lvl in self.LEVELS}

    def half_width_cs(self, p: DirectionalPair, pred_cs: int, level: float) -> int:
        q_map = (
            self.quantiles_by_cell.get((p.direction, p.event_key))
            or self.quantiles_by_dir.get(p.direction)
            or self.global_quantiles
        )
        rel_q = q_map[level]
        return max(1, int(round(pred_cs * rel_q)))

    def evaluate(self, test_pairs: list[DirectionalPair], predictor) -> dict:
        def _eval_subset(sub: list[DirectionalPair]) -> dict:
            out = {"evaluated_pairs": 0}
            covered = Counter()
            widths_sec: dict[float, list[float]] = defaultdict(list)
            valid_n = 0
            for p in sub:
                pred = predictor(p)
                if pred is None:
                    continue
                valid_n += 1
                err_cs = abs(p.target_time_cs - pred)
                for lvl in self.LEVELS:
                    hw = self.half_width_cs(p, pred, lvl)
                    if err_cs <= hw:
                        covered[lvl] += 1
                    widths_sec[lvl].append(hw / 100.0)
            out["evaluated_pairs"] = valid_n
            if valid_n == 0:
                return out
            for lvl in self.LEVELS:
                pct_key = f"nominal_{int(lvl * 100)}pct"
                out[pct_key] = {
                    "empirical_coverage_pct": round(100.0 * covered[lvl] / valid_n, 2),
                    "mean_half_width_seconds": round(sum(widths_sec[lvl]) / valid_n, 3),
                    "median_half_width_seconds": round(statistics.median(widths_sec[lvl]), 3),
                }
            return out

        clean = [p for p in test_pairs if not p.is_ratio_outlier]
        by_event = {}
        for ev in CANONICAL_EVENT_ORDER:
            ev_sub = [p for p in clean if p.event_key == ev]
            if len(ev_sub) >= 10:
                by_event[ev] = _eval_subset(ev_sub)
        return {
            "overall_clean_test": _eval_subset(clean),
            "by_event": by_event,
        }


def compute_bootstrap_significance(
    clean_test: list[DirectionalPair],
    predictors: dict,
    n_boot: int = 200,
    seed: int = 20261022,
) -> dict:
    """Swimmer-clustered paired bootstrap for 95% CIs and z-scores on MAE reductions."""
    if not clean_test:
        return {}

    # Precompute per-pair absolute errors in seconds for each predictor
    pair_errs: dict[str, list[float]] = {}
    for name, fn in predictors.items():
        errs = []
        for p in clean_test:
            pred = fn(p)
            errs.append(abs((pred or p.source_time_cs) - p.target_time_cs) / 100.0)
        pair_errs[name] = errs

    def _cluster_boot_subset(indices: list[int]) -> dict:
        if len(indices) < 10:
            return {}
        by_swimmer_idx: dict[str, list[int]] = defaultdict(list)
        for idx in indices:
            by_swimmer_idx[clean_test[idx].swimmer_key].append(idx)
        swimmer_keys = sorted(by_swimmer_idx.keys())
        n_swimmers = len(swimmer_keys)
        if n_swimmers < 5:
            return {}

        # Pre-aggregate per-swimmer sum of errors and count of pairs for fast exact cluster resampling
        swimmer_counts = [len(by_swimmer_idx[k]) for k in swimmer_keys]
        swimmer_err_sums: dict[str, list[float]] = {
            name: [sum(pair_errs[name][i] for i in by_swimmer_idx[k]) for k in swimmer_keys]
            for name in predictors
        }

        total_pairs = sum(swimmer_counts)
        point_mae = {
            name: sum(swimmer_err_sums[name]) / total_pairs
            for name in predictors
        }

        rng = random.Random(seed)
        boot_deltas_ncaa: dict[str, list[float]] = defaultdict(list)
        boot_deltas_colo: dict[str, list[float]] = defaultdict(list)

        for _ in range(n_boot):
            sampled_s_idx = [rng.randrange(n_swimmers) for _ in range(n_swimmers)]
            denom = float(sum(swimmer_counts[s] for s in sampled_s_idx))
            if denom <= 0:
                continue
            ncaa_b = sum(swimmer_err_sums["ncaa_2025_27"][s] for s in sampled_s_idx) / denom
            colo_b = sum(swimmer_err_sums["colorado_2026"][s] for s in sampled_s_idx) / denom
            for name in ("quantile_equivalence", "tier1_huber_pace_core", "tier1_gbm_core", "tier2_huber_pace_age", "tier2_gbm_age"):
                mod_b = sum(swimmer_err_sums[name][s] for s in sampled_s_idx) / denom
                boot_deltas_ncaa[name].append(mod_b - ncaa_b)
                boot_deltas_colo[name].append(mod_b - colo_b)

        out = {
            "evaluated_pairs": total_pairs,
            "clustered_swimmers": n_swimmers,
            "bootstrap_replicates": n_boot,
            "comparisons_vs_ncaa": {},
            "comparisons_vs_colorado": {},
        }
        for name, deltas in boot_deltas_ncaa.items():
            ordered = sorted(deltas)
            lo = ordered[max(0, int(math.floor(0.025 * len(ordered))))]
            hi = ordered[min(len(ordered) - 1, int(math.ceil(0.975 * len(ordered))) - 1)]
            diff = point_mae[name] - point_mae["ncaa_2025_27"]
            se = statistics.pstdev(ordered) if len(ordered) > 1 else 0.0
            out["comparisons_vs_ncaa"][name] = {
                "delta_mae_seconds": round(diff, 4),
                "relative_change_pct": round(100.0 * diff / max(1e-9, point_mae["ncaa_2025_27"]), 2),
                "se_seconds": round(se, 4),
                "ci95_low_seconds": round(lo, 4),
                "ci95_high_seconds": round(hi, 4),
                "z_score": round(diff / se, 2) if se > 1e-9 else 0.0,
            }
        for name, deltas in boot_deltas_colo.items():
            ordered = sorted(deltas)
            lo = ordered[max(0, int(math.floor(0.025 * len(ordered))))]
            hi = ordered[min(len(ordered) - 1, int(math.ceil(0.975 * len(ordered))) - 1)]
            diff = point_mae[name] - point_mae["colorado_2026"]
            se = statistics.pstdev(ordered) if len(ordered) > 1 else 0.0
            out["comparisons_vs_colorado"][name] = {
                "delta_mae_seconds": round(diff, 4),
                "relative_change_pct": round(100.0 * diff / max(1e-9, point_mae["colorado_2026"]), 2),
                "se_seconds": round(se, 4),
                "ci95_low_seconds": round(lo, 4),
                "ci95_high_seconds": round(hi, 4),
                "z_score": round(diff / se, 2) if se > 1e-9 else 0.0,
            }
        return out

    all_idx = list(range(len(clean_test)))
    families = {
        "overall_clean_test": all_idx,
        "sprint_50_100": [i for i, p in enumerate(clean_test) if p.event_key in ("50-FR", "100-FR", "100-BK", "100-BR", "100-FL")],
        "middle_200_400": [i for i, p in enumerate(clean_test) if p.event_key in ("200-FR", "400-FR", "200-BK", "200-BR", "200-IM")],
        "distance_800_1500": [i for i, p in enumerate(clean_test) if p.event_key in ("800-FR", "1500-FR")],
        "specialty_200fl_400im": [i for i, p in enumerate(clean_test) if p.event_key in ("200-FL", "400-IM")],
    }
    return {k: _cluster_boot_subset(v) for k, v in families.items() if len(v) >= 10}


def load_venue_lookup(venues_csv: Path | None) -> dict[str, dict]:
    if venues_csv is None or not venues_csv.exists():
        return {}
    import csv

    high_altitude_cities = {
        "rapid city", "spearfish", "lead", "deadwood", "custer", "hot springs",
        "sturgis", "belle fourche", "hill city", "box elder", "truckee",
        "south lake tahoe", "incline village", "carson city", "reno", "sparks",
        "minden", "gardnerville", "elko", "fallon", "boone", "banner elk",
    }
    high_altitude_zip3 = {"577", "894", "895", "897", "898", "961"}

    lookup: dict[str, dict] = {}
    with venues_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            mid = row.get("meet_id")
            if not mid:
                continue
            alt_ft = 0
            try:
                if row.get("reported_altitude_feet"):
                    alt_ft = int(float(row["reported_altitude_feet"]))
            except ValueError:
                alt_ft = 0
            state = (row.get("source_meet_state") or "").strip().upper()
            city = " ".join((row.get("source_meet_city") or "").split()).lower()
            z5 = (row.get("source_meet_postal_5") or "").strip()
            reg = (row.get("region") or "").strip().lower()
            is_alt = (
                alt_ft >= 3000
                or state in {"CO", "UT", "WY", "NM", "ID", "MT", "NV"}
                or reg in {"utah", "montana", "utah swimming", "montana swimming"}
                or city in high_altitude_cities
                or (len(z5) >= 3 and z5[:3] in high_altitude_zip3)
            )
            lookup[mid] = {
                "facility_id": (row.get("matched_facility_id") or "").strip(),
                "state": state,
                "altitude_ft": alt_ft,
                "is_altitude": is_alt,
            }
    return lookup


def evaluate_models_on_split(
    train_pairs: list[DirectionalPair],
    val_pairs: list[DirectionalPair],
    test_pairs: list[DirectionalPair],
    venue_lookup: dict[str, dict] | None = None,
    include_bootstrap_and_conformal: bool = False,
) -> tuple[dict, dict]:
    """Fit all candidate models on Train (early stopping on Val) and evaluate on Test."""
    weights = compute_training_weights(train_pairs)

    quantile_model = EmpiricalQuantileModel()
    quantile_model.fit(train_pairs)

    huber_core = HuberPaceModel(include_age=False)
    huber_core.fit(train_pairs, weights)

    huber_age = HuberPaceModel(include_age=True)
    huber_age.fit(train_pairs, weights)

    gbm_core = BoundedHistogramGBM(include_age=False)
    gbm_core.fit(train_pairs, weights, val_pairs)

    gbm_age = BoundedHistogramGBM(include_age=True)
    gbm_age.fit(train_pairs, weights, val_pairs)

    predictors = {
        "ncaa_2025_27": lambda p: predict_ncaa_cs(
            p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
        ),
        "colorado_2026": lambda p: predict_colorado_cs(
            p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance
        ),
        "quantile_equivalence": quantile_model.predict,
        "tier1_huber_pace_core": huber_core.predict,
        "tier1_gbm_core": gbm_core.predict,
        "tier2_huber_pace_age": huber_age.predict,
        "tier2_gbm_age": gbm_age.predict,
    }

    clean_test = [p for p in test_pairs if not p.is_ratio_outlier]
    results = {
        "clean_test": {},
        "untrimmed_test": {},
        "by_direction": {},
        "by_event": {},
        "by_age_band": {},
        "by_speed_quartile": {},
    }

    for name, fn in predictors.items():
        clean_preds = [fn(p) for p in clean_test]
        raw_preds = [fn(p) for p in test_pairs]
        results["clean_test"][name] = compute_metrics(clean_test, clean_preds)
        results["untrimmed_test"][name] = compute_metrics(test_pairs, raw_preds)

    # Breakdowns on clean_test by direction
    for direction in sorted({p.direction for p in clean_test}):
        sub = [p for p in clean_test if p.direction == direction]
        if len(sub) < 10:
            continue
        results["by_direction"][direction] = {
            name: compute_metrics(sub, [fn(p) for p in sub])
            for name, fn in predictors.items()
        }

    # Breakdowns on clean_test by canonical event (all 14 events)
    for ev in CANONICAL_EVENT_ORDER:
        sub = [p for p in clean_test if p.event_key == ev]
        if not sub:
            continue
        ev_entry = {
            "display_label": EVENT_DISPLAY_LABELS.get(ev, ev),
            "evaluated_pairs": len(sub),
            "evaluated_swimmers": len({p.swimmer_key for p in sub}),
            "models": {},
        }
        for name, fn in predictors.items():
            m = compute_metrics(sub, [fn(p) for p in sub])
            ev_entry["models"][name] = {
                "mae_seconds": m["mae_seconds"],
                "median_ae_seconds": m["median_ae_seconds"],
                "rmse_seconds": m["rmse_seconds"],
                "mape_percent": m["mape_percent"],
                "signed_bias_seconds": m["signed_bias_seconds"],
                "within_1_0_pct": m["within_1_0_pct"],
            }
        results["by_event"][ev] = ev_entry

    for band in ("10u", "11-12", "13-14", "15-16", "17-18", "19+"):
        sub = [p for p in clean_test if p.age_band == band]
        if len(sub) < 10:
            continue
        results["by_age_band"][band] = {
            name: {
                "pairs": len(sub),
                "mae_seconds": compute_metrics(sub, [fn(p) for p in sub])["mae_seconds"],
                "signed_bias_seconds": compute_metrics(sub, [fn(p) for p in sub])["signed_bias_seconds"],
            }
            for name, fn in predictors.items()
        }

    # Speed quartiles within each (direction, event_key, category)
    by_cell: dict[tuple[str, str, str], list[DirectionalPair]] = defaultdict(list)
    for p in clean_test:
        by_cell[(p.direction, p.event_key, p.category)].append(p)
    quartiles: dict[str, list[DirectionalPair]] = defaultdict(list)
    for cell_pairs in by_cell.values():
        if len(cell_pairs) < 8:
            continue
        ordered = sorted(cell_pairs, key=lambda x: x.source_time_cs)
        q = len(ordered)
        for idx, p in enumerate(ordered):
            bucket = (
                "Q1_fastest_25pct"
                if idx < q * 0.25
                else "Q2_25_to_50pct"
                if idx < q * 0.50
                else "Q3_50_to_75pct"
                if idx < q * 0.75
                else "Q4_slowest_25pct"
            )
            quartiles[bucket].append(p)

    for q_label, sub in sorted(quartiles.items()):
        results["by_speed_quartile"][q_label] = {
            name: {
                "pairs": len(sub),
                "mae_seconds": compute_metrics(sub, [fn(p) for p in sub])["mae_seconds"],
                "signed_bias_seconds": compute_metrics(sub, [fn(p) for p in sub])["signed_bias_seconds"],
            }
            for name, fn in predictors.items()
        }

    if venue_lookup:
        cohorts: dict[str, list[DirectionalPair]] = defaultdict(list)
        for p in clean_test:
            v_src = venue_lookup.get(p.source_meet_id)
            v_dst = venue_lookup.get(p.target_meet_id)
            if v_src and v_dst:
                f_src = v_src.get("facility_id")
                f_dst = v_dst.get("facility_id")
                if f_src and f_dst:
                    if f_src == f_dst:
                        cohorts["same_facility_transition"].append(p)
                    else:
                        cohorts["different_facility_transition"].append(p)
                if v_src.get("is_altitude") or v_dst.get("is_altitude") or p.region in ("Utah Swimming", "Montana Swimming"):
                    cohorts["altitude_meet_involved"].append(p)
                else:
                    cohorts["sea_level_both_meets"].append(p)
            elif p.region in ("Utah Swimming", "Montana Swimming") or (v_src and v_src.get("is_altitude")) or (v_dst and v_dst.get("is_altitude")):
                cohorts["altitude_meet_involved"].append(p)
        results["by_venue_cohort"] = {}
        for c_name, sub in sorted(cohorts.items()):
            if len(sub) < 10:
                continue
            results["by_venue_cohort"][c_name] = {
                "evaluated_pairs": len(sub),
                "evaluated_swimmers": len({p.swimmer_key for p in sub}),
                "models": {
                    name: {
                        "mae_seconds": compute_metrics(sub, [fn(p) for p in sub])["mae_seconds"],
                        "median_ae_seconds": compute_metrics(sub, [fn(p) for p in sub])["median_ae_seconds"],
                        "signed_bias_seconds": compute_metrics(sub, [fn(p) for p in sub])["signed_bias_seconds"],
                    }
                    for name, fn in predictors.items()
                },
            }

    if include_bootstrap_and_conformal:
        results["bootstrap_significance"] = compute_bootstrap_significance(clean_test, predictors)
        conformal_core = SplitConformalCalibrator()
        conformal_core.fit(val_pairs, huber_core.predict)
        conformal_gbm = SplitConformalCalibrator()
        conformal_gbm.fit(val_pairs, gbm_age.predict)
        results["conformal_prediction_intervals"] = {
            "tier1_huber_pace_core": conformal_core.evaluate(clean_test, huber_core.predict),
            "tier2_gbm_age": conformal_gbm.evaluate(clean_test, gbm_age.predict),
        }

    model_metadata = {
        "gbm_core_trees_by_direction": gbm_core.best_tree_count,
        "gbm_age_trees_by_direction": gbm_age.best_tree_count,
        "huber_core_cells_fitted": len(huber_core.models),
        "quantile_tables_fitted": len(quantile_model.tables),
        "predictors": predictors,
        "huber_core_model": huber_core,
    }
    return results, model_metadata


def load_swims_from_csv(csv_path: Path) -> list[SwimRecord]:
    import csv

    records: list[SwimRecord] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("status") != "OK":
                continue
            try:
                age = float(row["age_years"]) if row.get("age_years") else None
                records.append(
                    SwimRecord(
                        source=row["source"],
                        race_id=row["race_id"],
                        swimmer_id=row["swimmer_id"],
                        meet_id=row["meet_id"],
                        race_date=date.fromisoformat(row["date"]),
                        course=row["course"],
                        distance=int(row["distance"]),
                        stroke=row["stroke"],
                        category=row["category"],
                        time_cs=int(row["time_cs"]),
                        age_years=age,
                        region=row.get("region") or "unknown",
                    )
                )
            except (ValueError, KeyError):
                continue
    return records


def load_swims_from_duckdb(duckdb_path: Path) -> list[SwimRecord]:
    """Fast DuckDB/Iceberg best-of-meet extraction for multi-million-row checkpoints."""
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        con.execute("LOAD iceberg")
        # Collapse same-meet rounds in SQL first (fastest valid time per swimmer, meet, course, distance, stroke, category)
        rows = con.execute("""
            SELECT source,
                   arg_min(race_id, time_cs) AS race_id,
                   swimmer_id,
                   meet_id,
                   arg_min(race_date, time_cs) AS race_date,
                   course,
                   distance,
                   stroke,
                   category,
                   min(time_cs) AS time_cs,
                   arg_min(age_years, time_cs) AS age_years,
                   coalesce(arg_min(region, time_cs), 'unknown') AS region
            FROM races
            WHERE distance IN (50, 100, 200, 400, 500, 800, 1000, 1500, 1650)
              AND NOT (distance = 50 AND stroke != 'freestyle')
              AND NOT (distance = 100 AND stroke = 'individual-medley')
            GROUP BY source, swimmer_id, meet_id, course, distance, stroke, category
        """).fetchall()
        return [
            SwimRecord(
                source=r[0],
                race_id=r[1],
                swimmer_id=r[2],
                meet_id=r[3],
                race_date=r[4] if isinstance(r[4], date) else date.fromisoformat(str(r[4])),
                course=r[5],
                distance=int(r[6]),
                stroke=r[7],
                category=r[8],
                time_cs=int(r[9]),
                age_years=float(r[10]) if r[10] is not None else None,
                region=r[11],
            )
            for r in rows
        ]
    finally:
        con.close()


def build_featured_events_deep_dive(
    predictors: dict,
    pairs_30: list[DirectionalPair],
    pairs_60: list[DirectionalPair],
    augmented_counts: dict[str, int],
) -> dict:
    """Detailed evaluation on distance & specialty events (800/1000, 1500/1650, 200 Fly, 400 IM, 500/400 Free)."""
    featured_keys = ("800-FR", "1500-FR", "200-FL", "400-IM", "400-FR")
    clean_test_30 = [p for p in pairs_30 if p.partition == "test" and not p.is_ratio_outlier]
    clean_test_60 = [p for p in pairs_60 if p.partition == "test" and not p.is_ratio_outlier]
    clean_train_30 = [p for p in pairs_30 if p.partition == "train" and not p.is_ratio_outlier]

    out = {}
    for ev in featured_keys:
        t30 = [p for p in clean_test_30 if p.event_key == ev]
        t60 = [p for p in clean_test_60 if p.event_key == ev]
        tr30_n = sum(1 for p in clean_train_30 if p.event_key == ev)
        aug_n = augmented_counts.get(ev, 0)
        if not t30 and not t60:
            continue
        entry = {
            "display_label": EVENT_DISPLAY_LABELS.get(ev, ev),
            "train_pairs_30d": tr30_n,
            "train_pairs_added_31_to_60d": aug_n,
            "train_pairs_total_augmented": tr30_n + aug_n,
            "test_30d": {
                "evaluated_pairs": len(t30),
                "evaluated_swimmers": len({p.swimmer_key for p in t30}),
                "models": {
                    name: compute_metrics(t30, [fn(p) for p in t30])
                    for name, fn in predictors.items()
                } if t30 else {},
                "by_direction": {},
            },
            "test_60d": {
                "evaluated_pairs": len(t60),
                "evaluated_swimmers": len({p.swimmer_key for p in t60}),
                "models": {
                    name: compute_metrics(t60, [fn(p) for p in t60])
                    for name, fn in predictors.items()
                } if t60 else {},
            },
        }
        for d in ("SCY->LCM", "LCM->SCY", "SCM->LCM", "LCM->SCM", "SCY->SCM", "SCM->SCY"):
            sub_d = [p for p in t30 if p.direction == d]
            if len(sub_d) >= 4:
                entry["test_30d"]["by_direction"][d] = {
                    "evaluated_pairs": len(sub_d),
                    "ncaa_2025_27_mae_s": compute_metrics(sub_d, [predictors["ncaa_2025_27"](p) for p in sub_d])["mae_seconds"],
                    "colorado_2026_mae_s": compute_metrics(sub_d, [predictors["colorado_2026"](p) for p in sub_d])["mae_seconds"],
                    "tier1_huber_pace_core_mae_s": compute_metrics(sub_d, [predictors["tier1_huber_pace_core"](p) for p in sub_d])["mae_seconds"],
                    "tier2_huber_pace_age_mae_s": compute_metrics(sub_d, [predictors["tier2_huber_pace_age"](p) for p in sub_d])["mae_seconds"],
                    "tier2_gbm_age_mae_s": compute_metrics(sub_d, [predictors["tier2_gbm_age"](p) for p in sub_d])["mae_seconds"],
                }
        out[ev] = entry
    return out


def run_pipeline(
    swims: list[SwimRecord],
    input_label: str,
    max_days: int = 30,
    output_dir: Path | None = None,
    public_summary_path: Path | None = None,
    venues_csv: Path | None = DEFAULT_VENUES_CSV,
    export_empirical_json: Path | None = None,
) -> dict:
    dedup_swims, hygiene_stats = deduplicate_best_of_meet(swims)
    pairs_30 = build_directional_pairs(dedup_swims, max_days=max_days)
    pairs_14 = build_directional_pairs(dedup_swims, max_days=14)
    pairs_60 = build_directional_pairs(dedup_swims, max_days=60)
    venue_lookup = load_venue_lookup(venues_csv)

    # 1. Swimmer-disjoint 70/15/15 split (with adaptive 31-60d training supplementation for sparse events/SCM)
    train_sw_30 = [p for p in pairs_30 if p.partition == "train"]
    train_sw_60 = [p for p in pairs_60 if p.partition == "train"]
    train_sw, augmented_counts = augment_sparse_training_pairs(train_sw_30, train_sw_60)
    val_sw = [p for p in pairs_30 if p.partition == "validation"]
    test_sw = [p for p in pairs_30 if p.partition == "test"]
    swimmer_holdout, model_meta = evaluate_models_on_split(
        train_sw,
        val_sw,
        test_sw,
        venue_lookup=venue_lookup,
        include_bootstrap_and_conformal=True,
    )
    predictors = model_meta.pop("predictors")
    huber_core_model: HuberPaceModel = model_meta.pop("huber_core_model")
    model_meta["sparse_event_60d_augmented_train_pairs"] = sum(augmented_counts.values())
    model_meta["sparse_event_60d_augmented_by_event"] = augmented_counts

    evaluated_at_str = datetime.now(timezone.utc).date().isoformat()
    if export_empirical_json is not None:
        snapshot = huber_core_model.export_snapshot_dict(
            revision=f"2026-10-22 ({input_label})",
            evaluated_at=evaluated_at_str,
        )
        export_empirical_json.write_text(
            json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    featured_deep_dive = build_featured_events_deep_dive(
        predictors=predictors,
        pairs_30=pairs_30,
        pairs_60=pairs_60,
        augmented_counts=augmented_counts,
    )

    # 2. Window sensitivity check (14d, 30d, 60d test sets evaluated with the trained models)
    window_sensitivity = {}
    for w_label, w_pairs in (("14d", pairs_14), ("30d", pairs_30), ("60d", pairs_60)):
        w_test = [p for p in w_pairs if p.partition == "test" and not p.is_ratio_outlier]
        if w_test:
            window_sensitivity[w_label] = {
                "evaluated_pairs": len(w_test),
                "evaluated_swimmers": len({p.swimmer_key for p in w_test}),
                "ncaa_2025_27_mae_s": compute_metrics(w_test, [predictors["ncaa_2025_27"](p) for p in w_test])["mae_seconds"],
                "colorado_2026_mae_s": compute_metrics(w_test, [predictors["colorado_2026"](p) for p in w_test])["mae_seconds"],
                "tier1_huber_pace_core_mae_s": compute_metrics(w_test, [predictors["tier1_huber_pace_core"](p) for p in w_test])["mae_seconds"],
                "tier1_gbm_core_mae_s": compute_metrics(w_test, [predictors["tier1_gbm_core"](p) for p in w_test])["mae_seconds"],
                "tier2_huber_pace_age_mae_s": compute_metrics(w_test, [predictors["tier2_huber_pace_age"](p) for p in w_test])["mae_seconds"],
                "tier2_gbm_age_mae_s": compute_metrics(w_test, [predictors["tier2_gbm_age"](p) for p in w_test])["mae_seconds"],
            }

    # 3. Temporal later-season holdout (Train/Val <= 2025, Test >= 2026)
    pre_2026 = [p for p in pairs_30 if p.source_year <= 2025 and p.target_year <= 2025]
    train_temp = [p for p in pre_2026 if p.partition in ("train", "test")]
    val_temp = [p for p in pre_2026 if p.partition == "validation"]
    test_temp = [p for p in pairs_30 if p.source_year >= 2026 and p.target_year >= 2026]
    temporal_holdout = (
        evaluate_models_on_split(train_temp, val_temp, test_temp)[0]["clean_test"]
        if len(train_temp) >= 50 and len(test_temp) >= 20
        else {"status": "insufficient_temporal_split"}
    )

    # 4. Leave-One-Region-Out (LORO) holdout (hold out Southeastern + Adirondack + South Dakota + PVS + Midwestern)
    heldout_regions = {
        "Southeastern Swimming",
        "Adirondack Swimming",
        "South Dakota Swimming",
        "Potomac Valley Swimming",
        "Midwestern Swimming",
    }
    in_reg = [p for p in pairs_30 if p.region not in heldout_regions]
    out_reg = [p for p in pairs_30 if p.region in heldout_regions]
    train_loro = [p for p in in_reg if p.partition in ("train", "test")]
    val_loro = [p for p in in_reg if p.partition == "validation"]
    loro_holdout = (
        evaluate_models_on_split(train_loro, val_loro, out_reg)[0]["clean_test"]
        if len(train_loro) >= 50 and len(out_reg) >= 20
        else {"status": "insufficient_regional_split"}
    )

    # 5. Pilot scope subset (SCY -> LCM 50/100/200 Freestyle) for continuity with initial pilot
    pilot_train = [
        p for p in train_sw_30
        if p.direction == "SCY->LCM" and p.stroke == "freestyle" and p.source_distance in (50, 100, 200)
    ]
    pilot_val = [
        p for p in val_sw
        if p.direction == "SCY->LCM" and p.stroke == "freestyle" and p.source_distance in (50, 100, 200)
    ]
    pilot_test = [
        p for p in test_sw
        if p.direction == "SCY->LCM" and p.stroke == "freestyle" and p.source_distance in (50, 100, 200)
    ]
    pilot_subset = (
        evaluate_models_on_split(pilot_train, pilot_val, pilot_test)[0]["clean_test"]
        if pilot_train and pilot_test
        else {}
    )

    report = {
        "checkpoint": "evaluation-checkpoint-06",
        "evaluated_at": datetime.now(timezone.utc).date().isoformat(),
        "scope": "aggregate local model evaluation receipt; no swimmer-level records",
        "input_source": input_label,
        "matching_window_days": max_days,
        "hygiene_and_pairing": {
            **hygiene_stats,
            "directional_pairs_14d": len(pairs_14),
            "directional_pairs_30d": len(pairs_30),
            "directional_pairs_60d": len(pairs_60),
            "unique_undirected_pairs_30d": len(pairs_30) // 2,
            "ratio_outliers_flagged_30d": sum(1 for p in pairs_30 if p.is_ratio_outlier),
            "clean_directional_pairs_30d": sum(1 for p in pairs_30 if not p.is_ratio_outlier),
            "swimmers_with_pairs_30d": len({p.swimmer_key for p in pairs_30}),
            "by_direction_30d": dict(sorted(Counter(p.direction for p in pairs_30 if not p.is_ratio_outlier).items())),
            "by_event_30d": {
                ev: sum(1 for p in pairs_30 if not p.is_ratio_outlier and p.event_key == ev)
                for ev in CANONICAL_EVENT_ORDER
            },
            "by_event_60d": {
                ev: sum(1 for p in pairs_60 if not p.is_ratio_outlier and p.event_key == ev)
                for ev in CANONICAL_EVENT_ORDER
            },
            "by_region_30d": dict(sorted(Counter(p.region for p in pairs_30 if not p.is_ratio_outlier).items())),
        },
        "partitions_30d": {
            part: {
                "directional_pairs": sum(1 for p in pairs_30 if p.partition == part),
                "clean_directional_pairs": sum(1 for p in pairs_30 if p.partition == part and not p.is_ratio_outlier),
                "swimmers": len({p.swimmer_key for p in pairs_30 if p.partition == part}),
            }
            for part in ("train", "validation", "test")
        },
        "model_metadata": model_meta,
        "pilot_scy_to_lcm_freestyle_50_100_200_test": pilot_subset,
        "featured_events_deep_dive": featured_deep_dive,
        "window_sensitivity_test": window_sensitivity,
        "swimmer_disjoint_holdout": swimmer_holdout,
        "temporal_2026_holdout": temporal_holdout,
        "leave_regions_out_holdout": loro_holdout,
        "validated_for_product": False,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "evaluation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if public_summary_path is not None:
        public_summary_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Normalized results.csv path")
    parser.add_argument("--duckdb", type=Path, help="queries.duckdb path from lakehouse.py")
    parser.add_argument("--input-label", type=str, default=None, help="Checkpoint label for provenance")
    parser.add_argument("--venues-csv", type=Path, default=DEFAULT_VENUES_CSV, help="Optional meet_venues.csv path")
    parser.add_argument("--max-days", type=int, default=30)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--public-summary", type=Path, default=None)
    parser.add_argument("--export-empirical-json", type=Path, default=None)
    args = parser.parse_args()

    if bool(args.csv) == bool(args.duckdb):
        raise SystemExit("Provide exactly one of --csv or --duckdb")

    if args.duckdb:
        swims = load_swims_from_duckdb(args.duckdb)
        label = args.input_label or "local-lakehouse-national-checkpoint-14"
    else:
        swims = load_swims_from_csv(args.csv)
        label = args.input_label or args.csv.name

    report = run_pipeline(
        swims=swims,
        input_label=label,
        max_days=args.max_days,
        output_dir=args.output_dir,
        public_summary_path=args.public_summary,
        venues_csv=args.venues_csv,
        export_empirical_json=args.export_empirical_json,
    )
    print(json.dumps(report["swimmer_disjoint_holdout"]["clean_test"], indent=2))


if __name__ == "__main__":
    main()
