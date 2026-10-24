"""Offline fitting and evaluation of the Turnmark equivalence model.

The equivalence model treats a swimmer's two swims of one event in different courses as noisy
readings of one latent ability. For each (event, category) it places every course on a shared
log-time ability scale with a location and a scale, so a conversion is

    ln y = location_B + (scale_B / scale_A) * (ln x - location_A).

Converting back is the exact inverse, converting through a third course equals converting
directly, and the map is monotone with no shrinkage toward the average swimmer. The parameters
come from Deming (errors-in-variables) lines through paired swims in log space, with the error
variance ratio estimated from same-course repeat swims, empirical-Bayes shrinkage of thin cells
toward pool geometry and a flat multiplier, and a weighted reconciliation across the three
course pairs.

It is compared with the shipped NCAA (2025-27) and Colorado Timing (2026) formulas, a flat
empirical multiplier, and same-input and age-aware percentile matching, on:
- a swimmer-disjoint 70/15/15 holdout,
- a later-season holdout (training <= 2025, test 2026, swimmer-disjoint),
- a leave-regions-out holdout (region- and swimmer-disjoint),
reporting round-trip closure, three-course transitivity, percentile preservation, signed bias
binned by pair-mean ability, pair MAE, and swimmer- and meet-clustered bootstrap intervals.

No swimmer-level records or identity keys are written to public artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
import hashlib
import json
import math
import multiprocessing
import re
import statistics
from pathlib import Path
from typing import Callable, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent.parent.parent
CONVERSIONS_JSON = ROOT / "data/conversions.json"
COLORADO_JSON = ROOT / "data/colorado.json"
EMPIRICAL_PARITY_FIXTURE = ROOT / "fixtures/empirical-parity.json"
DEFAULT_VENUES_CSV = ROOT / "research/conversion-model/data/national-checkpoint-17/meet_venues.csv"
EVALUATION_CHECKPOINT = "evaluation-checkpoint-08"
SNAPSHOT_SCHEMA_VERSION = 3

COURSES = ("SCY", "SCM", "LCM")
# Each undirected course pair is fitted once and serves both directions.
COURSE_PAIRS = (("SCY", "LCM"), ("SCY", "SCM"), ("SCM", "LCM"))
ALL_DIRECTIONS = ("SCY->LCM", "LCM->SCY", "SCY->SCM", "SCM->SCY", "SCM->LCM", "LCM->SCM")
CATEGORIES = ("women", "men")
# A course-pair cell is low-evidence when fewer than this many effective swimmers (Kish's formula
# over each swimmer's total weight, so a swimmer's repeated pairs count once) swam the event in both
# courses. Its parameters then lean on the event pool, related events and pool geometry. The
# threshold is a judgment, not a fitted value.
LOW_EVIDENCE_SWIMMERS = 100.0
# Swimmers with same-course repeat swims per course and event needed before their noise estimate is
# used alone.
MIN_REPEAT_SWIMMERS = 200
TAU2_FLOOR = 1e-8
# The less-coupled ability diagnostic: the swimmer's swim of the same event in the pair's canonical
# source course at another meet, nearest in date to the pair's swim in that course and at most
# INSTRUMENT_MAX_DAYS from it, and at least INSTRUMENT_MIN_DAYS from both of the pair's swims.
# Swims nearer either one share more of its form and taper, which couples them to the pair's error.
INSTRUMENT_MIN_DAYS = 31
INSTRUMENT_MAX_DAYS = 90
# An entered time is low-evidence where the bootstrap 95% CI of its conversion is wider than this.
PRECISION_LIMIT_PCT = 1.0
# Fast-swimmer example: 14:13.00 for 1650 yd SCY (men) converted to 1500 m LCM.
FAST_SWIMMER_EXAMPLE = {"time_cs": 85300, "course": "SCY", "distance": 1650, "to": "LCM", "category": "men"}

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


def canonical_event_key(course: str, stroke: str, distance: int) -> str | None:
    """The canonical event (e.g. "400-FR") a swim belongs to, or None outside the 14 events.
    Yard freestyle distance events are 500/1000/1650; a 400/800/1500 yd freestyle swim is a
    different race and must not share the 500 yd/400 m (or longer) bucket."""
    if stroke not in STROKE_CODE:
        return None
    if course == "SCY" and stroke == "freestyle" and distance in (400, 800, 1500):
        return None
    key = f"{canonical_metric_distance(course, stroke, distance)}-{STROKE_CODE[stroke]}"
    return key if key in CANONICAL_EVENT_ORDER else None


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
    source_date: date | None = None
    target_date: date | None = None


def is_plausible_swim(course: str, distance: int, time_cs: int) -> bool:
    lo = MIN_PLAUSIBLE_CS.get((course, distance))
    hi = MAX_PLAUSIBLE_CS.get(distance)
    if lo is None or hi is None:
        return False
    return lo <= time_cs <= hi


def geometric_physics_factor(
    source_course: str,
    target_course: str,
    stroke: str,
    source_distance: int,
) -> float | None:
    """First-principles pool-geometry factor:
    - Exact unit conversion (1 yd = 0.9144 m)
    - 25-unit vs 50m wall turn frequency (1.022 for ->LCM, 1/1.022 for LCM->)
    - 25y (22.86m) vs 25m/50m surface-swimming portion per length (~2.05% for equal nominal distance,
      ~1.15% for distance-changing freestyle where turns are a smaller fraction of total race time)

    Strictly independent of NCAA and Colorado conversion tables.
    """
    target_distance = mapped_distance(source_course, target_course, stroke, source_distance)
    if target_distance is None:
        return None
    metric_dist = canonical_metric_distance(source_course, stroke, source_distance)
    if f"{metric_dist}-{STROKE_CODE.get(stroke, '')}" not in CANONICAL_EVENT_ORDER:
        return None
    if source_course == target_course:
        return 1.0
    src_meters = float(source_distance) * (0.9144 if source_course == "SCY" else 1.0)
    dst_meters = float(target_distance) * (0.9144 if target_course == "SCY" else 1.0)
    dist_ratio = dst_meters / src_meters
    is_dist_change = source_distance != target_distance
    scy_wall_factor = 1.0115 if is_dist_change else 1.0205
    yard_surface_ratio = 1.0
    if source_course == "SCY" and target_course in ("SCM", "LCM"):
        yard_surface_ratio = scy_wall_factor
    elif source_course in ("SCM", "LCM") and target_course == "SCY":
        yard_surface_ratio = 1.0 / scy_wall_factor
    turn_ratio = 1.022 if target_course == "LCM" else (1.0 / 1.022 if source_course == "LCM" else 1.0)
    return dist_ratio * yard_surface_ratio * turn_ratio


def geometric_physics_reference_cs(
    time_cs: int,
    source_course: str,
    target_course: str,
    stroke: str,
    source_distance: int,
) -> int | None:
    factor = geometric_physics_factor(source_course, target_course, stroke, source_distance)
    if factor is None:
        return None
    return truncate_cs((time_cs / 100.0) * factor)


def is_pair_ratio_outlier(
    source_course: str,
    target_course: str,
    stroke: str,
    source_distance: int,
    source_time_cs: int,
    target_time_cs: int,
    category: str = "",
) -> bool:
    """Flag extreme non-physiological ratio anomalies (>18% off pool-geometry reference)."""
    phys_pred = geometric_physics_reference_cs(
        source_time_cs, source_course, target_course, stroke, source_distance
    )
    if phys_pred is None or phys_pred <= 0:
        return True
    rel_diff = abs(target_time_cs - phys_pred) / float(phys_pred)
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
        stats["round_collapsed_candidate_swims"] += 1
        if rec.stroke not in STROKE_CODE or rec.category not in ("women", "men"):
            stats["excluded_unsupported_event"] += 1
            continue
        # Exclude 50 BK/BR/FL, 100 IM and 400/800/1500 yd freestyle: not canonical conversion events
        if canonical_event_key(rec.course, rec.stroke, rec.distance) is None:
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
        if canonical_event_key(s.course, s.stroke, s.distance) is None:
            continue
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
                # One screen per matched pair, judged in the canonical orientation (c_a -> c_b), so
                # both directions of a pair are kept or dropped together.
                outlier = is_pair_ratio_outlier(c_a, c_b, stroke, a.distance, a.time_cs, b.time_cs, category)
                for src, dst in ((a, b), (b, a)):
                    age = src.age_years if src.age_years is not None else dst.age_years
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
                            source_date=src.race_date,
                            target_date=dst.race_date,
                        )
                    )
    return directional_pairs


def swimmer_weights(pairs: list[DirectionalPair]) -> list[float]:
    """1 / (pairs the swimmer contributes to the same direction, event and category), so each
    swimmer carries equal total weight within a cell."""
    counts = Counter((p.swimmer_key, p.direction, p.event_key, p.category) for p in pairs)
    return [1.0 / counts[(p.swimmer_key, p.direction, p.event_key, p.category)] for p in pairs]


def swimmer_totals(weights: np.ndarray, swimmers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(swimmer index per row, each swimmer's total weight). Rows are clustered by swimmer."""
    _, index = np.unique(swimmers, return_inverse=True)
    return index, np.bincount(index, weights=weights)


def weighted_quantiles(values: np.ndarray, weights: np.ndarray, qs: Iterable[float]) -> list[float]:
    """Inverse of the weighted empirical CDF: for each q, the smallest value whose cumulative weight
    reaches q of the total. Splitting a row's weight over identical copies leaves it unchanged; the
    tolerance keeps float error in the running sum from stepping past a value it reaches exactly."""
    order = np.argsort(values, kind="stable")
    cum = np.cumsum(weights[order])
    tol = 1e-9 * cum[-1]
    return [float(values[order][min(int(np.searchsorted(cum, q * cum[-1] - tol, side="left")), len(cum) - 1)]) for q in qs]


def effective_swimmers(weights: np.ndarray, swimmers: np.ndarray) -> float:
    """Kish's effective sample size over swimmers, (sum W)^2 / sum(W^2) with W a swimmer's total
    weight: the independent-evidence count. Repeating a swimmer's rows does not change it."""
    _, totals = swimmer_totals(weights, swimmers)
    squares = float((totals * totals).sum())
    return float(totals.sum()) ** 2 / squares if squares > 0.0 else 0.0


@dataclass(frozen=True)
class RepeatSwim:
    """Log ratio between consecutive same-course swims of one event by one swimmer."""

    swimmer_key: str
    partition: str
    course: str
    event_key: str
    region: str
    year: int
    log_ratio: float


def build_repeat_swims(swims: list[SwimRecord], max_days: int = 30) -> list[RepeatSwim]:
    """Consecutive best-of-meet swims of one event in one course by one swimmer, at different meets
    1 to max_days apart. Their spread estimates each course's per-swim noise."""
    by_key: dict[tuple, list[SwimRecord]] = defaultdict(list)
    for s in swims:
        by_key[(s.source, s.swimmer_id, s.course, s.distance, s.stroke, s.category)].append(s)
    out: list[RepeatSwim] = []
    for (source, swimmer_id, course, distance, stroke, _category), group in sorted(by_key.items()):
        if len(group) < 2:
            continue
        event_key = canonical_event_key(course, stroke, distance)
        if event_key is None:
            continue
        group.sort(key=lambda s: (s.race_date, s.race_id))
        for a, b in zip(group, group[1:]):
            gap = (b.race_date - a.race_date).days
            if 1 <= gap <= max_days and a.meet_id != b.meet_id:
                out.append(
                    RepeatSwim(
                        swimmer_key=f"{source}|{swimmer_id}",
                        partition=swimmer_partition(source, swimmer_id),
                        course=course,
                        event_key=event_key,
                        region=b.region or a.region or "unknown",
                        year=b.race_date.year,
                        log_ratio=math.log(b.time_cs / a.time_cs),
                    )
                )
    return out


def estimate_course_noise(repeats: Iterable[RepeatSwim]) -> dict[tuple[str, str], float]:
    """Per-swim log-time noise variance per (course, event): half the swimmer-weighted variance of
    repeat-swim log ratios (each swimmer's repeats in a cell carry equal total weight), after the same
    18% screen used for pairs. A course with repeats from fewer than MIN_REPEAT_SWIMMERS swimmers in
    an event takes the mean of the courses that have enough. Same-course repeats see timing, race-day
    and short-term form noise; they cannot see a swimmer's aptitude for one course over another."""
    by_cell: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for r in repeats:
        if abs(r.log_ratio) <= math.log(1.18):
            by_cell[(r.course, r.event_key)].append((r.swimmer_key, r.log_ratio))
    noise: dict[tuple[str, str], float] = {}
    for ev in CANONICAL_EVENT_ORDER:
        measured = {}
        for c in COURSES:
            rows = by_cell[(c, ev)]
            swimmers = np.array([k for k, _ in rows])
            if len(set(swimmers.tolist())) < MIN_REPEAT_SWIMMERS:
                continue
            values = np.array([v for _, v in rows])
            index = np.unique(swimmers, return_inverse=True)[1]
            w = 1.0 / np.bincount(index)[index]
            mean = float((w * values).sum() / w.sum())
            measured[c] = float((w * (values - mean) ** 2).sum() / w.sum()) / 2.0
        pooled = sum(measured.values()) / len(measured) if measured else None
        for c in COURSES:
            value = measured.get(c, pooled)
            if value is not None:
                noise[(c, ev)] = value
    return noise


def deming_slope(sxx: float, syy: float, sxy: float, delta: float) -> float:
    """Deming slope of y on x, where delta = var(error in y) / var(error in x)."""
    spread = syy - delta * sxx
    return (spread + math.sqrt(spread * spread + 4.0 * delta * sxy * sxy)) / (2.0 * sxy)


@dataclass(frozen=True)
class PairLine:
    """One Deming line through paired swims in log seconds: it passes through (center, center +
    shift) with slope exp(log_slope). The shift variance is a swimmer-clustered sandwich estimate;
    the slope variance is an approximation that counts swimmers, not rows."""

    center: float
    shift: float
    shift_var: float
    log_slope: float
    log_slope_var: float  # (1 - r^2) / effective swimmers: an approximation, not a cluster variance
    effective_swimmers: float
    pairs: int
    swimmers: int


def fit_pair_line(rows: np.ndarray, swimmer_ids: np.ndarray, delta: float) -> PairLine | None:
    """rows: columns (log source, log target, weight); swimmer_ids: the swimmer of each row.
    Duplicating every row of a swimmer leaves the line, its variances and its evidence unchanged:
    swimmer weights renormalize, and uncertainty is counted over swimmers, not rows."""
    x, y, w = rows[:, 0], rows[:, 1], rows[:, 2]
    index, totals = swimmer_totals(w, swimmer_ids)
    n_sw = effective_swimmers(w, swimmer_ids)
    if n_sw < 3.0:
        return None
    total = float(w.sum())
    xm = float((w * x).sum() / total)
    ym = float((w * y).sum() / total)
    sxx = float((w * (x - xm) ** 2).sum() / total)
    syy = float((w * (y - ym) ** 2).sum() / total)
    sxy = float((w * (x - xm) * (y - ym)).sum() / total)
    if sxx <= 0.0 or syy <= 0.0 or sxy <= 0.0:
        return None
    r2 = min(1.0, sxy * sxy / (sxx * syy))
    # Cluster-robust (swimmer) sampling variance of the weighted mean shift, with the small-sample
    # factor m / (m - 1) over the m swimmers.
    m = len(totals)
    scores = np.bincount(index, weights=w * ((y - x) - (ym - xm)))
    shift_var = float((scores * scores).sum()) / (total * total) * m / max(m - 1, 1)
    return PairLine(
        center=xm,
        shift=ym - xm,
        shift_var=max(TAU2_FLOOR, shift_var),
        log_slope=math.log(deming_slope(sxx, syy, sxy, delta)),
        log_slope_var=max(TAU2_FLOOR, (1.0 - r2) / n_sw),
        effective_swimmers=n_sw,
        pairs=len(rows),
        swimmers=m,
    )


@dataclass(frozen=True)
class Posterior:
    value: float
    var: float
    own_share: float


def shrink_toward(
    estimates: dict[tuple, tuple[float, float]], priors: dict[tuple, Posterior]
) -> tuple[dict[tuple, Posterior], float]:
    """Empirical-Bayes shrinkage of each estimate (value, sampling variance) toward its prior.
    The between-cell variance tau^2 is a moment estimate around the known priors; each posterior
    weights its own estimate by (prior var + tau^2) / (prior var + tau^2 + sampling var)."""
    keys = [k for k in priors if k in estimates]
    tau2 = TAU2_FLOOR
    if keys:
        w = np.array([1.0 / (estimates[k][1] + priors[k].var) for k in keys])
        r2 = np.array([(estimates[k][0] - priors[k].value) ** 2 for k in keys])
        tau2 = max(TAU2_FLOOR, float(((w * r2).sum() - len(keys)) / w.sum()))
    out: dict[tuple, Posterior] = {}
    for key, prior in priors.items():
        prior_var = prior.var + tau2
        if key not in estimates:
            out[key] = Posterior(prior.value, prior_var, 0.0)
            continue
        value, var = estimates[key]
        share = prior_var / (prior_var + var)
        out[key] = Posterior(share * value + (1.0 - share) * prior.value, share * var, share)
    return out, tau2


class EquivalenceModel:
    """Per (event, category, course), a monotone piecewise-linear map in log time onto one shared
    latent ability scale (SCY log seconds), so every direction is a composition of the same per-course
    maps: exact inverses before rounding, three-course transitivity by construction, and monotone.

    1. Deming lines per course pair, event and category (and per course pair and event, categories
       pooled) through train pairs, each swimmer weighted equally within a cell; the error variance
       ratio comes from same-course repeat swims.
    2. Empirical-Bayes shrinkage: event lines toward pool geometry (shift) and a flat multiplier
       (slope 1); category cells toward their event line.
    3. Per (event, category), weighted least squares across the three course pairs gives a linear
       map of LCM and SCM log time onto the SCY latent (SCY is the identity).
    4. Each course map spans its training support (latent 0.5th to 99.5th percentile of the pairs it
       appears in). Beyond it, the map continues with slope 1 in log time: the time ratio at the edge
       of the data is held constant instead of extrapolating an ability slope.
    """

    def __init__(self) -> None:
        # (event_key, category) -> {course: (location, scale)} of the reconciled linear stage
        self.linear: dict[tuple[str, str], dict[str, tuple[float, float]]] = {}
        # (event_key, category) -> {course: [(latent, course log seconds), ...]}, rounded as exported
        self.tables: dict[tuple[str, str], dict[str, list[tuple[float, float]]]] = {}
        # "A->B|event|category" -> (latent lo, latent hi) where the 95% CI width is within the limit,
        # or None when it never is; set by precise_latent_ranges.
        self.precise_ranges: dict[str, tuple[float, float] | None] | None = None
        self.lines: dict[tuple[str, str, str], PairLine] = {}
        self.shift_post: dict[tuple[str, str, str], Posterior] = {}
        self.event_shift_post: dict[tuple[str, str, str], Posterior] = {}
        self.slope_post: dict[tuple[str, str, str], Posterior] = {}
        self.tau2: dict[str, dict[str, float]] = {}
        self.noise: dict[tuple[str, str], float] = {}

    def fit(self, train_pairs: list[DirectionalPair], noise: dict[tuple[str, str], float]) -> None:
        self.noise = noise
        canonical = {f"{a}->{b}" for a, b in COURSE_PAIRS}
        rows = [p for p in train_pairs if not p.is_ratio_outlier and p.direction in canonical]
        weights = swimmer_weights(rows)
        grouped: dict[tuple[str, str, str], list[tuple[float, float, float]]] = defaultdict(list)
        swimmers: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        for p, w in zip(rows, weights):
            row = (math.log(p.source_time_cs / 100.0), math.log(p.target_time_cs / 100.0), w)
            for cat in (p.category, "all"):
                grouped[(p.direction, p.event_key, cat)].append(row)
                swimmers[(p.direction, p.event_key, cat)].append(p.swimmer_key)
        for key, group in grouped.items():
            direction, ev, _ = key
            src, dst = direction.split("->")
            delta = noise.get((dst, ev), 1.0) / noise.get((src, ev), 1.0)
            line = fit_pair_line(np.array(group), np.array(swimmers[key]), delta)
            if line is not None:
                self.lines[key] = line

        for src, dst in COURSE_PAIRS:
            direction = f"{src}->{dst}"
            geometry = {
                ev: math.log(geometric_physics_factor(src, dst, *_event_key_to_stroke_and_source_dist(ev, src)))
                for ev in CANONICAL_EVENT_ORDER
            }
            event_keys = [(direction, ev, "all") for ev in CANONICAL_EVENT_ORDER]
            ev_shift, tau_shift_ev = shrink_toward(
                {k: (self.lines[k].shift, self.lines[k].shift_var) for k in event_keys if k in self.lines},
                {k: Posterior(geometry[k[1]], 0.0, 0.0) for k in event_keys},
            )
            ev_slope, tau_slope_ev = shrink_toward(
                {k: (self.lines[k].log_slope, self.lines[k].log_slope_var) for k in event_keys if k in self.lines},
                {k: Posterior(0.0, 0.0, 0.0) for k in event_keys},
            )
            cell_keys = [(direction, ev, cat) for ev in CANONICAL_EVENT_ORDER for cat in CATEGORIES]
            cell_shift, tau_shift = shrink_toward(
                {k: (self.lines[k].shift, self.lines[k].shift_var) for k in cell_keys if k in self.lines},
                {k: ev_shift[(direction, k[1], "all")] for k in cell_keys},
            )
            cell_slope, tau_slope = shrink_toward(
                {k: (self.lines[k].log_slope, self.lines[k].log_slope_var) for k in cell_keys if k in self.lines},
                {k: ev_slope[(direction, k[1], "all")] for k in cell_keys},
            )
            self.shift_post.update(cell_shift)
            self.event_shift_post.update(ev_shift)
            self.slope_post.update(cell_slope)
            self.tau2[direction] = {
                "event_shift": tau_shift_ev,
                "event_log_slope": tau_slope_ev,
                "category_shift": tau_shift,
                "category_log_slope": tau_slope,
            }

        for ev in CANONICAL_EVENT_ORDER:
            for cat in CATEGORIES:
                self.linear[(ev, cat)] = self._reconcile(ev, cat)
                self.tables[(ev, cat)] = self._course_tables(ev, cat, grouped)

    def _center(self, direction: str, ev: str, cat: str) -> float | None:
        for key in ((direction, ev, cat), (direction, ev, "all")):
            if key in self.lines:
                return self.lines[key].center
        return None

    def _reconcile(self, ev: str, cat: str) -> dict[str, tuple[float, float]]:
        sl, ss, ml = ((f"{a}->{b}", ev, cat) for a, b in COURSE_PAIRS)
        # The SCY anchor is the SCY center of the SCY-LCM pairs, else of the SCY-SCM pairs. An event
        # with neither (never in the national data) is anchored at a nominal SCY time; its cells have
        # no pairs, so the snapshot lists them as low-evidence and every input as out of range.
        anchor = self._center(*sl)
        if anchor is None:
            anchor = self._center(*ss)
        if anchor is None:
            stroke, scy_distance = _event_key_to_stroke_and_source_dist(ev, "SCY")
            anchor = math.log(MIN_PLAUSIBLE_CS[("SCY", scy_distance)] * 1.45 / 100.0)
        # Log scales of LCM and SCM relative to SCY: l_L = SL, l_M = SS, l_L - l_M = ML.
        design = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, -1.0]])
        target = np.array([self.slope_post[k].value for k in (sl, ss, ml)])
        weight = np.diag([1.0 / self.slope_post[k].var for k in (sl, ss, ml)])
        log_l, log_m = np.linalg.solve(design.T @ weight @ design, design.T @ weight @ target)
        scale_l, scale_m = math.exp(log_l), math.exp(log_m)
        # Locations (course log time at the SCY anchor). Each line passes through its pair center.
        x_sl = self._center(*sl)
        if x_sl is None:
            x_sl = anchor
        x_ss = self._center(*ss)
        if x_ss is None:
            x_ss = anchor
        rows = [[1.0, 0.0], [0.0, 1.0]]
        rhs = [
            x_sl + self.shift_post[sl].value - scale_l * (x_sl - anchor),
            x_ss + self.shift_post[ss].value - scale_m * (x_ss - anchor),
        ]
        x_ml = self._center(*ml)
        if x_ml is None:
            x_ml = rhs[1]
        ratio = scale_l / scale_m
        rows.append([1.0, -ratio])
        rhs.append(x_ml + self.shift_post[ml].value - ratio * x_ml)
        design = np.array(rows)
        weight = np.diag([1.0 / self.shift_post[k].var for k in (sl, ss, ml)])
        loc_l, loc_m = np.linalg.solve(design.T @ weight @ design, design.T @ weight @ np.array(rhs))
        return {"SCY": (anchor, 1.0), "SCM": (float(loc_m), scale_m), "LCM": (float(loc_l), scale_l)}

    def _course_tables(self, ev: str, cat: str, grouped: dict) -> dict[str, list[tuple[float, float]]]:
        lin = self.linear[(ev, cat)]
        anchor = lin["SCY"][0]

        def to_latent(course: str, v: np.ndarray) -> np.ndarray:
            loc, scale = lin[course]
            return anchor + (v - loc) / scale

        def from_latent(course: str, u: np.ndarray | float) -> np.ndarray | float:
            loc, scale = lin[course]
            return loc + scale * (u - anchor)

        # Training support of each course on the latent scale: the swimmer-weighted 0.5th to 99.5th
        # percentile of the pair-mean latent of every pair it appears in (this category only).
        latents: dict[str, list[np.ndarray]] = defaultdict(list)
        latent_weights: dict[str, list[np.ndarray]] = defaultdict(list)
        for a, b in COURSE_PAIRS:
            group = grouped.get((f"{a}->{b}", ev, cat))
            if not group:
                continue
            arr = np.array(group)
            u = 0.5 * (to_latent(a, arr[:, 0]) + to_latent(b, arr[:, 1]))
            for course in (a, b):
                latents[course].append(u)
                latent_weights[course].append(arr[:, 2])
        tables: dict[str, list[tuple[float, float]]] = {}
        for course in COURSES:
            u_all = np.concatenate(latents[course]) if latents[course] else np.array([])
            if len(u_all) >= 5:
                lo, hi = weighted_quantiles(u_all, np.concatenate(latent_weights[course]), (0.005, 0.995))
            else:
                # No usable pairs: a degenerate support, so every input is out of range and converts at
                # the linear map's ratio at the anchor.
                lo, hi = anchor - 1e-3, anchor + 1e-3
            tables[course] = [
                (round(lo, 6), round(float(from_latent(course, lo)), 6)),
                (round(hi, 6), round(float(from_latent(course, hi)), 6)),
            ]
        return tables

    def event_share_of_level(self, key: tuple[str, str, str]) -> float:
        """Share of a cell's fitted level taken from this event's pairs in this course pair: its own
        category's share, plus the rest times the event line's share against pool geometry."""
        own = self.shift_post[key].own_share
        return own + (1.0 - own) * self.event_shift_post[(key[0], key[1], "all")].own_share

    def is_low_evidence(self, key: tuple[str, str, str]) -> bool:
        line = self.lines.get(key)
        return line is None or line.effective_swimmers < LOW_EVIDENCE_SWIMMERS

    def low_evidence_cells(self) -> list[str]:
        out = []
        for key in self.shift_post:
            direction, ev, cat = key
            if self.is_low_evidence(key):
                src, dst = direction.split("->")
                out += [f"{src}->{dst}|{ev}|{cat}", f"{dst}->{src}|{ev}|{cat}"]
        return sorted(out)

    def export_snapshot_dict(self, revision: str, evaluated_at: str) -> dict:
        """The engine snapshot (data/empirical.json): per (event, category) and course, the knots
        [latent, course log seconds] of its monotone map onto the shared latent scale; the
        whole-cell low-evidence list; and per direction the latent range where the conversion's
        bootstrap 95% CI is no wider than PRECISION_LIMIT_PCT."""
        payload = {
            "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
            "cells": {
                f"{ev}|{cat}": {
                    course: {"knots": [[u, v] for u, v in self.tables[(ev, cat)][course]]}
                    for course in sorted(self.tables[(ev, cat)])
                }
                for (ev, cat) in sorted(self.tables)
            },
            "lowEvidenceCells": self.low_evidence_cells(),
            "preciseLatentRanges": {
                key: (None if rng is None else [round(rng[0], 6), round(rng[1], 6)])
                for key, rng in sorted((self.precise_ranges or {}).items())
            },
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return {
            "source": {
                "id": "turnmark-empirical-2026",
                "title": "Turnmark Equivalence Model (2010–2026 US Competition Swims)",
                "url": "https://github.com/Stanback/turnmark/blob/main/research/conversion-model/REPORT.md",
                "revision": revision,
                "verified": evaluated_at,
                "sha256": digest,
            },
            **payload,
        }

    def convert(self, p: DirectionalPair) -> EquivalentTime | None:
        cell = self.tables.get((p.event_key, p.category))
        if cell is None:
            return None
        return engine_equivalence(cell[p.source_course], cell[p.target_course], p.source_time_cs)

    def predict(self, p: DirectionalPair) -> int | None:
        if p.source_course == p.target_course:
            return p.source_time_cs
        result = self.convert(p)
        return result.hundredths if result else None

    def caveat(self, p: DirectionalPair) -> str | None:
        """The engine's caveat for this conversion: out of range beats low evidence."""
        result = self.convert(p)
        if result is None or p.source_course == p.target_course:
            return None
        key = f"{p.source_course}->{p.target_course}|{p.event_key}|{p.category}"
        ranges = self.precise_ranges or {}
        return conversion_caveat(result, key, set(self.low_evidence_cells()), ranges.get(key) if self.precise_ranges is not None else (-math.inf, math.inf))

    def cell_support(self, train_pairs: list[DirectionalPair], clean_test: list[DirectionalPair]) -> dict:
        """Evidence behind each course-pair cell: training pairs, swimmers and effective swimmers, the
        share of its fitted level and slope taken from its own pairs, its latent support, and held-out
        test pairs (both directions). Effective swimmers drive the whole-cell low-evidence flag."""
        canonical = {f"{a}->{b}" for a, b in COURSE_PAIRS}

        def undirected(p: DirectionalPair) -> str:
            return p.direction if p.direction in canonical else f"{p.target_course}->{p.source_course}"

        test_pairs = Counter((undirected(p), p.event_key, p.category) for p in clean_test)
        test_swimmers: dict[tuple, set[str]] = defaultdict(set)
        for p in clean_test:
            test_swimmers[(undirected(p), p.event_key, p.category)].add(p.swimmer_key)
        cells = {}
        flags = Counter()
        for key in sorted(self.shift_post):
            direction, ev, cat = key
            a, b = direction.split("->")
            line = self.lines.get(key)
            low = self.is_low_evidence(key)
            tab = self.tables[(ev, cat)]
            support = [max(tab[a][0][0], tab[b][0][0]), min(tab[a][-1][0], tab[b][-1][0])]
            cells["|".join(key)] = {
                "train_pairs": line.pairs if line else 0,
                "train_swimmers": line.swimmers if line else 0,
                "effective_swimmers": round(line.effective_swimmers, 1) if line else 0.0,
                "own_category_share_of_level": round(self.shift_post[key].own_share, 3),
                "event_share_of_level": round(self.event_share_of_level(key), 3),
                "own_share_of_slope": round(self.slope_post[key].own_share, 3),
                "latent_support_seconds": [round(math.exp(support[0]), 2), round(math.exp(support[1]), 2)],
                "test_directional_pairs": test_pairs[key],
                "test_swimmers": len(test_swimmers[key]),
                "low_evidence": low,
            }
            flags["cells_low_evidence"] += low
            flags["cells_without_train_line"] += line is None
            flags["cells_under_20_train_swimmers"] += (line.swimmers if line else 0) < 20
            flags["cells_without_test_pairs"] += test_pairs[key] == 0
            flags["cells_under_5_test_swimmers"] += len(test_swimmers[key]) < 5
        return {**{name: int(count) for name, count in sorted(flags.items())}, "cells": cells}

    def metadata(self) -> dict:
        return {
            "course_pair_cells": len(self.shift_post),
            "event_category_cells": len(self.tables),
            "noise_variance_log_seconds": {
                f"{course}|{ev}": round(value, 7) for (course, ev), value in sorted(self.noise.items())
            },
            "between_cell_variance": {
                direction: {name: round(value, 9) for name, value in taus.items()}
                for direction, taus in self.tau2.items()
            },
        }


def knot_map(knots: list[tuple[float, float]] | list[list[float]], x: float, inverse: bool) -> float:
    """Evaluate a course's monotone piecewise-linear map exactly as engine.rs does: latent -> course
    log seconds (inverse=False) or back (inverse=True), with slope 1 beyond the outer knots."""
    i_in, i_out = (1, 0) if inverse else (0, 1)
    first, last = knots[0], knots[-1]
    if x <= first[i_in]:
        return first[i_out] + (x - first[i_in])
    if x >= last[i_in]:
        return last[i_out] + (x - last[i_in])
    i = 0
    while knots[i + 1][i_in] <= x:
        i += 1
    lo, hi = knots[i], knots[i + 1]
    return lo[i_out] + (x - lo[i_in]) * (hi[i_out] - lo[i_out]) / (hi[i_in] - lo[i_in])


@dataclass(frozen=True)
class EquivalentTime:
    hundredths: int
    latent: float
    out_of_range: bool


def engine_equivalence(source: list, target: list, time_cs: int) -> EquivalentTime | None:
    """Convert exactly as crates/turnmark-core/src/engine.rs does with exported knot tables: the
    entered time's latent ability through the source course's map, then the target course's map,
    truncated to hundredths once. A result that truncates to zero is rejected (None), matching the
    engine's unsafe-result outcome. Out of range when the latent lies outside either course's support."""
    seconds = time_cs / 100.0
    latent = knot_map(source, math.log(seconds), inverse=True)
    converted = truncate_cs(math.exp(knot_map(target, latent, inverse=False)))
    if converted <= 0:
        return None
    lo = max(source[0][0], target[0][0])
    hi = min(source[-1][0], target[-1][0])
    return EquivalentTime(converted, latent, not (lo <= latent <= hi))


def engine_equivalence_cs(source: list, target: list, time_cs: int) -> int | None:
    result = engine_equivalence(source, target, time_cs)
    return result.hundredths if result else None


def conversion_caveat(result: EquivalentTime, key: str, low_evidence: set[str], precise: tuple[float, float] | list | None) -> str | None:
    """Out of the training range beats low evidence; low evidence covers both a thin cell and an
    entered time outside the range where the bootstrap 95% CI is within PRECISION_LIMIT_PCT."""
    if result.out_of_range:
        return "empirical-out-of-range"
    if key in low_evidence or precise is None or not (precise[0] <= result.latent <= precise[1]):
        return "empirical-low-evidence"
    return None


_BOOT: dict = {}


def _bootstrap_init(train_pairs: list[DirectionalPair], noise: dict) -> None:
    by_swimmer: dict[str, list[DirectionalPair]] = defaultdict(list)
    for p in train_pairs:
        by_swimmer[p.swimmer_key].append(p)
    _BOOT.update(keys=sorted(by_swimmer), by_swimmer=by_swimmer, noise=noise)


def _bootstrap_refit(seed: int) -> dict:
    """One swimmer-cluster bootstrap refit; repeated swimmers get distinct keys so swimmer weighting
    treats each draw as its own swimmer."""
    rng = np.random.default_rng(seed)
    keys = _BOOT["keys"]
    seen: Counter = Counter()
    pairs: list[DirectionalPair] = []
    for j in rng.integers(0, len(keys), len(keys)):
        key = keys[j]
        copy = seen[key]
        seen[key] += 1
        pairs += [p if copy == 0 else replace(p, swimmer_key=f"{key}#{copy}") for p in _BOOT["by_swimmer"][key]]
    model = EquivalenceModel()
    model.fit(pairs, _BOOT["noise"])
    return model.tables


def precise_latent_ranges(
    model: EquivalenceModel, train_pairs: list[DirectionalPair], noise: dict, n_boot: int = 200, seed: int = 20261023
) -> tuple[dict[str, tuple[float, float] | None], dict]:
    """Swimmer-cluster bootstrap refits of the model. For every direction, event and category, on 41
    latent points across the joint support, the 95% interval of the converted log time for the entered
    time the fitted model places there. The precise range is the contiguous run around the narrowest
    point whose width is at most PRECISION_LIMIT_PCT; None when none is."""
    canonical = [p for p in train_pairs if not p.is_ratio_outlier and p.direction in {f"{a}->{b}" for a, b in COURSE_PAIRS}]
    import concurrent.futures

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=8, mp_context=multiprocessing.get_context("spawn"), initializer=_bootstrap_init,
        initargs=(canonical, noise),
    ) as pool:
        replicates = list(pool.map(_bootstrap_refit, range(seed, seed + n_boot), chunksize=4))
    ranges: dict[str, tuple[float, float] | None] = {}
    widths: dict[str, dict] = {}
    for (ev, cat), tables in model.tables.items():
        for a in COURSES:
            for b in COURSES:
                if a == b:
                    continue
                lo = max(tables[a][0][0], tables[b][0][0])
                hi = min(tables[a][-1][0], tables[b][-1][0])
                key = f"{a}->{b}|{ev}|{cat}"
                if hi <= lo:
                    ranges[key] = None
                    widths[key] = {"min_ci95_width_pct": None, "precise_share_of_support": 0.0}
                    continue
                grid = np.linspace(lo, hi, 41)
                entered = [knot_map(tables[a], u, inverse=False) for u in grid]
                draws = np.array(
                    [[knot_map(rep[(ev, cat)][b], knot_map(rep[(ev, cat)][a], x, inverse=True), inverse=False) for x in entered] for rep in replicates]
                )
                width = 100.0 * (np.quantile(draws, 0.975, axis=0) - np.quantile(draws, 0.025, axis=0))
                best = int(np.argmin(width))
                if width[best] > PRECISION_LIMIT_PCT:
                    ranges[key] = None
                else:
                    i0 = best
                    while i0 > 0 and width[i0 - 1] <= PRECISION_LIMIT_PCT:
                        i0 -= 1
                    i1 = best
                    while i1 < len(grid) - 1 and width[i1 + 1] <= PRECISION_LIMIT_PCT:
                        i1 += 1
                    ranges[key] = (float(grid[i0]), float(grid[i1]))
                widths[key] = {
                    "min_ci95_width_pct": round(float(width[best]), 3),
                    "ci95_width_pct_at_support_edges": [round(float(width[0]), 3), round(float(width[-1]), 3)],
                    "precise_share_of_support": round(float((width <= PRECISION_LIMIT_PCT).mean()), 3),
                }
    return ranges, {"bootstrap_refits": n_boot, "limit_pct": PRECISION_LIMIT_PCT, "by_direction": widths}


class FlatMultiplierModel:
    """Baseline: one directional multiplier per (direction, event, category), the swimmer-weighted
    median of target/source time ratios normalized by pool geometry, shrunk by effective swimmers toward its event
    (k = 120), the event toward its stroke (k = 120) and the stroke toward geometry (k = 80). Each
    direction is fitted separately."""

    def __init__(self) -> None:
        self.factors: dict[tuple[str, str, str], float] = {}

    def fit(self, train_pairs: list[DirectionalPair]) -> None:
        clean = [p for p in train_pairs if not p.is_ratio_outlier]
        weights = swimmer_weights(clean)
        levels: dict[tuple, list[tuple[float, float]]] = defaultdict(list)
        level_swimmers: dict[tuple, list[str]] = defaultdict(list)
        for p, w in zip(clean, weights):
            geom = geometric_physics_factor(p.source_course, p.target_course, p.stroke, p.source_distance) or 1.0
            ratio = (p.target_time_cs / p.source_time_cs) / geom
            for key in (("cell", p.direction, p.event_key, p.category), ("event", p.direction, p.event_key), ("stroke", p.direction, p.stroke)):
                levels[key].append((ratio, w))
                level_swimmers[key].append(p.swimmer_key)

        def shrunk(key: tuple, prior: float, k: float) -> float:
            items = levels.get(key, [])
            if not items:
                return prior
            n_sw = effective_swimmers(np.array([w for _, w in items]), np.array(level_swimmers[key]))
            return (n_sw * _weighted_median(items) + k * prior) / (n_sw + k)

        for direction in ALL_DIRECTIONS:
            src, dst = direction.split("->")
            for ev in CANONICAL_EVENT_ORDER:
                stroke, src_dist = _event_key_to_stroke_and_source_dist(ev, src)
                geom = geometric_physics_factor(src, dst, stroke, src_dist) or 1.0
                stroke_mult = shrunk(("stroke", direction, stroke), 1.0, 80.0)
                event_mult = shrunk(("event", direction, ev), stroke_mult, 120.0)
                for cat in CATEGORIES:
                    self.factors[(direction, ev, cat)] = round(geom * shrunk(("cell", direction, ev, cat), event_mult, 120.0), 5)

    def predict(self, p: DirectionalPair) -> int | None:
        if p.source_course == p.target_course:
            return p.source_time_cs
        factor = self.factors.get((p.direction, p.event_key, p.category))
        if factor is None:
            return None
        return max(1, truncate_cs(p.source_time_cs / 100.0 * factor))


class AnchoredPercentileModel:
    """Percentile-matching baseline on the same SCY-anchored latent scale as the equivalence model:
    per event, category and non-SCY course B, 201 quantiles of paired SCY and B log times from
    Train's SCY-B pairs (outliers screened once per pair). A course maps to the latent by its quantile
    table and back by the target's, with slope 1 in log time beyond the tables, so it inverts and
    composes across courses up to truncation. Age-aware tables use the swimmer's age band when it has
    at least 25 pairs, else all ages. A course with no table converts by pool geometry."""

    KNOTS = 201
    MIN_PAIRS = 25

    def __init__(self, age_aware: bool) -> None:
        self.age_aware = age_aware
        self.tables: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def fit(self, train_pairs: list[DirectionalPair]) -> None:
        groups: dict[tuple, list[tuple[float, float]]] = defaultdict(list)
        for p in train_pairs:
            if p.is_ratio_outlier or p.source_course != "SCY" or p.target_course == "SCY":
                continue
            row = (math.log(p.source_time_cs), math.log(p.target_time_cs))
            groups[(p.event_key, p.category, p.target_course, "all")].append(row)
            if self.age_aware:
                groups[(p.event_key, p.category, p.target_course, p.age_band)].append(row)
        ps = np.linspace(0.0, 1.0, self.KNOTS)
        jitter = np.arange(self.KNOTS) * 1e-9  # strictly increasing knots, so the map inverts
        for key, rows in groups.items():
            if len(rows) < self.MIN_PAIRS:
                continue
            arr = np.array(rows)
            self.tables[key] = (np.quantile(arr[:, 0], ps) + jitter, np.quantile(arr[:, 1], ps) + jitter)

    def _table(self, p: DirectionalPair, course: str):
        if self.age_aware and (p.event_key, p.category, course, p.age_band) in self.tables:
            return self.tables[(p.event_key, p.category, course, p.age_band)]
        return self.tables.get((p.event_key, p.category, course, "all"))

    def _geometry(self, p: DirectionalPair, course: str) -> float:
        stroke, scy_distance = _event_key_to_stroke_and_source_dist(p.event_key, "SCY")
        return math.log(geometric_physics_factor("SCY", course, stroke, scy_distance))

    def _to_latent(self, p: DirectionalPair, course: str, v: float) -> float:
        if course == "SCY":
            return v
        table = self._table(p, course)
        if table is None:
            return v - self._geometry(p, course)
        qx, qy = table
        if v <= qy[0]:
            return qx[0] + (v - qy[0])
        if v >= qy[-1]:
            return qx[-1] + (v - qy[-1])
        return float(np.interp(v, qy, qx))

    def _from_latent(self, p: DirectionalPair, course: str, u: float) -> float:
        if course == "SCY":
            return u
        table = self._table(p, course)
        if table is None:
            return u + self._geometry(p, course)
        qx, qy = table
        if u <= qx[0]:
            return qy[0] + (u - qx[0])
        if u >= qx[-1]:
            return qy[-1] + (u - qx[-1])
        return float(np.interp(u, qx, qy))

    def predict(self, p: DirectionalPair) -> int | None:
        if p.source_course == p.target_course:
            return p.source_time_cs
        latent = self._to_latent(p, p.source_course, math.log(p.source_time_cs))
        converted = truncate_cs(math.exp(self._from_latent(p, p.target_course, latent)) / 100.0)
        return converted if converted > 0 else None


def _weighted_median(val_weights: list[tuple[float, float]]) -> float | None:
    if not val_weights:
        return None
    return weighted_quantiles(np.array([v for v, _ in val_weights]), np.array([w for _, w in val_weights]), (0.5,))[0]


def _event_key_to_stroke_and_source_dist(event_key: str, source_course: str) -> tuple[str, int]:
    dist_s, code = event_key.split("-")
    metric_dist = int(dist_s)
    stroke_map = {v: k for k, v in STROKE_CODE.items()}
    stroke = stroke_map[code]
    if source_course == "SCY" and stroke == "freestyle":
        src_dist = {400: 500, 800: 1000, 1500: 1650}.get(metric_dist, metric_dist)
    else:
        src_dist = metric_dist
    return stroke, src_dist


def format_clock_cs(time_cs: int) -> str:
    minutes, rem = divmod(time_cs, 6000)
    return f"{minutes}:{rem // 100:02d}.{rem % 100:02d}" if minutes else f"{rem // 100}.{rem % 100:02d}"


def build_empirical_parity_fixture(snapshot: dict) -> dict:
    """Exact-hundredths conversion cases for every exported (event, category) and ordered course
    pair, computed by the Python reference from data/empirical.json, so the Rust engine is held to
    the arithmetic that was evaluated. Probes run from below to above the joint training support (so
    the out-of-range edges and the constant-ratio extrapolation are pinned) and include a 0.01 s
    case (a valid conversion or the engine's rejection). Each case records the expected caveat."""
    cases = []
    low_evidence = set(snapshot["lowEvidenceCells"])
    precise = snapshot["preciseLatentRanges"]
    for cell_key, courses in sorted(snapshot["cells"].items()):
        event_key, category = cell_key.split("|")
        for source_course in COURSES:
            for target_course in COURSES:
                if source_course == target_course:
                    continue
                source = courses[source_course]["knots"]
                target = courses[target_course]["knots"]
                stroke, source_distance = _event_key_to_stroke_and_source_dist(event_key, source_course)
                direction_key = f"{source_course}->{target_course}|{cell_key}"
                lo = max(source[0][0], target[0][0])
                hi = min(source[-1][0], target[-1][0])
                latents = [lo - 0.1, lo + 0.25 * (hi - lo), 0.5 * (lo + hi), lo + 0.75 * (hi - lo), hi + 0.1]
                probes = [int(round(math.exp(knot_map(source, u, inverse=False)) * 100.0)) for u in latents]
                for time_cs in [*probes, 1]:
                    result = engine_equivalence(source, target, time_cs)
                    case = {
                        "cell": direction_key,
                        "time": format_clock_cs(time_cs),
                        "event": {"distance": source_distance, "stroke": stroke, "course": source_course},
                        "to": target_course,
                        "table": category,
                    }
                    if result is None:
                        case["expectedStatus"] = "invalid"
                    else:
                        case["expectedHundredths"] = result.hundredths
                        case["expectedCaveat"] = conversion_caveat(result, direction_key, low_evidence, precise.get(direction_key))
                    cases.append(case)
    return {"cellsSha256": snapshot["source"]["sha256"], "cases": cases}


def knot_map_np(knots: list, x: np.ndarray, inverse: bool) -> np.ndarray:
    """Vectorized knot_map (np.interp inside, slope 1 outside); for whole-range checks only, the
    parity fixture uses the scalar reference."""
    arr = np.array(knots, dtype=np.float64)
    xs, ys = (arr[:, 1], arr[:, 0]) if inverse else (arr[:, 0], arr[:, 1])
    out = np.interp(x, xs, ys)
    out = np.where(x < xs[0], ys[0] + (x - xs[0]), out)
    return np.where(x > xs[-1], ys[-1] + (x - xs[-1]), out)


def snapshot_arithmetic_properties(snapshot: dict) -> dict:
    """Round-trip closure, transitivity and monotonicity of the exported snapshot, checked at every
    hundredth of each source course's plausible time range (MIN/MAX_PLAUSIBLE_CS) with truncation,
    plus the closure of the unrounded maps. Before truncation both are identities up to floating
    point; the only residue is truncation to hundredths."""
    roundtrip = Counter()
    transitive = Counter()
    exact_log_error = 0.0
    evaluated = 0
    monotone_violations = 0
    for cell_key, courses in snapshot["cells"].items():
        event_key = cell_key.split("|")[0]
        knots = {c: courses[c]["knots"] for c in COURSES}

        def unrounded(logs: np.ndarray, a: str, b: str) -> np.ndarray:
            return knot_map_np(knots[b], knot_map_np(knots[a], logs, inverse=True), inverse=False)

        def convert(cs: np.ndarray, a: str, b: str) -> np.ndarray:
            return np.floor(np.exp(unrounded(np.log(cs / 100.0), a, b)) * 100.0 + 1e-8).astype(np.int64)

        for a in COURSES:
            _stroke, dist = _event_key_to_stroke_and_source_dist(event_key, a)
            lo, hi = MIN_PLAUSIBLE_CS[(a, dist)], MAX_PLAUSIBLE_CS[dist]
            times = np.arange(lo, hi + 1, dtype=np.int64)
            evaluated += len(times)
            for b in COURSES:
                if b == a:
                    continue
                forward = convert(times, a, b)
                monotone_violations += int(np.sum(np.diff(forward) < 0))
                back = convert(forward, b, a)
                for value, count in zip(*np.unique(np.abs(back - times), return_counts=True)):
                    roundtrip[int(value)] += int(count)
                logs = np.log(times / 100.0)
                exact_log_error = max(exact_log_error, float(np.max(np.abs(unrounded(unrounded(logs, a, b), b, a) - logs))))
                mid = next(c for c in COURSES if c not in (a, b))
                via = convert(convert(times, a, mid), mid, b)
                for value, count in zip(*np.unique(np.abs(via - forward), return_counts=True)):
                    transitive[int(value)] += int(count)
    total_rt = sum(roundtrip.values())
    total_tr = sum(transitive.values())
    return {
        "source_times_checked_per_course": evaluated,
        "roundtrip_conversions_checked": total_rt,
        "roundtrip_error_hundredths_distribution": {str(k): v for k, v in sorted(roundtrip.items())},
        "roundtrip_max_error_hundredths": max(roundtrip),
        "roundtrip_exact_share": round(roundtrip[0] / total_rt, 6),
        "unrounded_roundtrip_max_abs_log_error": exact_log_error,
        "transitivity_conversions_checked": total_tr,
        "transitivity_difference_hundredths_distribution": {str(k): v for k, v in sorted(transitive.items())},
        "transitivity_max_difference_hundredths": max(transitive),
        "transitivity_exact_share": round(transitive[0] / total_tr, 6),
        "monotonicity_violations": monotone_violations,
    }


def requery(p: DirectionalPair, source_course: str, target_course: str, time_cs: int) -> DirectionalPair:
    """The same swimmer, event and category asked as a conversion between other courses."""
    _stroke, source_distance = _event_key_to_stroke_and_source_dist(p.event_key, source_course)
    _stroke, target_distance = _event_key_to_stroke_and_source_dist(p.event_key, target_course)
    return replace(
        p,
        direction=f"{source_course}->{target_course}",
        source_course=source_course,
        target_course=target_course,
        source_distance=source_distance,
        target_distance=target_distance,
        source_time_cs=time_cs,
    )


def _summarize_abs_cs(errors: list[int]) -> dict:
    if not errors:
        return {"evaluated": 0}
    arr = np.array(errors, dtype=np.float64)
    return {
        "evaluated": len(errors),
        "mean_abs_seconds": round(float(arr.mean()) / 100.0, 4),
        "p95_abs_seconds": round(float(np.quantile(arr, 0.95)) / 100.0, 4),
        "max_abs_seconds": round(float(arr.max()) / 100.0, 2),
        "exact_share": round(float((arr == 0).mean()), 4),
        "within_0_01s_share": round(float((arr <= 1).mean()), 4),
    }


def roundtrip_and_transitivity(clean_test: list[DirectionalPair], predictors: dict) -> dict:
    """On held-out swims: A->B->A against the entered time, and A->C->B against A->B, for each
    method using its own conversions in every direction."""
    out = {}
    for name, fn in predictors.items():
        closure: list[int] = []
        transit: list[int] = []
        for p in clean_test:
            forward = fn(p)
            if forward is None:
                continue
            back = fn(requery(p, p.target_course, p.source_course, forward))
            if back is not None:
                closure.append(abs(back - p.source_time_cs))
            mid = next(c for c in COURSES if c not in (p.source_course, p.target_course))
            step = fn(requery(p, p.source_course, mid, p.source_time_cs))
            via = fn(requery(p, mid, p.target_course, step)) if step is not None else None
            if via is not None:
                transit.append(abs(via - forward))
        out[name] = {"roundtrip_closure": _summarize_abs_cs(closure), "transitivity_via_third_course": _summarize_abs_cs(transit)}
    return out


def _canonical_orientation(p: DirectionalPair) -> tuple[tuple[str, str], str]:
    for a, b in COURSE_PAIRS:
        if (p.source_course, p.target_course) == (a, b):
            return (a, b), "forward"
        if (p.source_course, p.target_course) == (b, a):
            return (a, b), "reverse"
    raise ValueError(p.direction)


def pair_mean_deciles(clean_test: list[DirectionalPair], min_pairs: int = 20) -> list[int | None]:
    """Decile (0 = fastest) of each row's pair-mean ability, the mean of the two log times, within
    its (course pair, event, category) cell. Both directions of a pair share one decile. Cells with
    fewer than min_pairs rows get None."""
    groups: dict[tuple, list[int]] = defaultdict(list)
    for i, p in enumerate(clean_test):
        groups[(_canonical_orientation(p)[0], p.event_key, p.category)].append(i)
    deciles: list[int | None] = [None] * len(clean_test)
    for idxs in groups.values():
        if len(idxs) < min_pairs:
            continue
        m = np.array([math.log(clean_test[i].source_time_cs) + math.log(clean_test[i].target_time_cs) for i in idxs])
        cuts = np.quantile(m, np.linspace(0.0, 1.0, 11)[1:-1])
        for i, d in zip(idxs, np.searchsorted(cuts, m, side="right")):
            deciles[i] = int(d)
    return deciles


InstrumentIndex = dict[tuple[str, str, str, str], list[tuple[date, str, float]]]


def build_instrument_index(swims: Iterable[SwimRecord], pairs: Iterable[DirectionalPair]) -> InstrumentIndex:
    """(swimmer key, course, event, category) -> [(race date, meet, log seconds)] by date, for the
    less-coupled ability diagnostic; only the keys some pair can draw on (its canonical source course)."""
    wanted = {(p.swimmer_key, _canonical_orientation(p)[0][0], p.event_key, p.category) for p in pairs}
    index: InstrumentIndex = defaultdict(list)
    for s in swims:
        event_key = canonical_event_key(s.course, s.stroke, s.distance)
        key = (f"{s.source}|{s.swimmer_id}", s.course, event_key, s.category)
        if event_key is not None and key in wanted:
            index[key].append((s.race_date, s.meet_id, math.log(s.time_cs / 100.0)))
    for swims_of_key in index.values():
        swims_of_key.sort()
    return index


def independent_swim_deciles(
    clean_test: list[DirectionalPair],
    index: InstrumentIndex,
    min_days: int = INSTRUMENT_MIN_DAYS,
    max_days: int = INSTRUMENT_MAX_DAYS,
    min_pairs: int = 20,
) -> tuple[list[int | None], dict]:
    """Decile (0 = fastest) of an ability measure that shares no swim with the pair: the swimmer's
    swim of the same event in the pair's canonical source course (SCY for SCY-LCM and SCY-SCM, SCM
    for SCM-LCM) at a meet other than either pair meet, at most max_days from the pair's swim in that
    course and at least min_days from both pair swims, the nearest such swim to the pair's swim in that
    course (ties: the earlier date, then the lower meet ID). Deciles are within (course pair, event,
    category) among rows that have one; both directions of a pair share it. This removes the shared
    measurement error that couples a pair-mean bin to the pair's residual, and the minimum gap reduces
    shared form and taper with either swim. It does not remove all coupling: form persists beyond a
    month, progression between the swims and which swimmers race often can still correlate the
    independent swim with the pair. Rows without an independent swim, and cells with fewer than
    min_pairs rows that have one, get None."""
    values: list[float | None] = []
    for p in clean_test:
        (a, _), _ = _canonical_orientation(p)
        when = p.source_date if p.source_course == a else p.target_date
        other = p.target_date if p.source_course == a else p.source_date
        best: tuple[int, date, float] | None = None
        if when is not None and other is not None:
            for race_date, meet, log_s in index.get((p.swimmer_key, a, p.event_key, p.category), ()):
                gap = abs((race_date - when).days)
                if (
                    gap > max_days
                    or min(gap, abs((race_date - other).days)) < min_days
                    or meet in (p.source_meet_id, p.target_meet_id)
                ):
                    continue
                if best is None or (gap, race_date, meet) < best[:3]:
                    best = (gap, race_date, meet, log_s)
        values.append(None if best is None else best[3])
    groups: dict[tuple, list[int]] = defaultdict(list)
    for i, p in enumerate(clean_test):
        if values[i] is not None:
            groups[(_canonical_orientation(p)[0], p.event_key, p.category)].append(i)
    deciles: list[int | None] = [None] * len(clean_test)
    for idxs in groups.values():
        if len(idxs) < min_pairs:
            continue
        m = np.array([values[i] for i in idxs])
        cuts = np.quantile(m, np.linspace(0.0, 1.0, 11)[1:-1])
        for i, d in zip(idxs, np.searchsorted(cuts, m, side="right")):
            deciles[i] = int(d)
    coverage = {
        "rows": len(clean_test),
        "rows_with_independent_swim": sum(v is not None for v in values),
        "rows_in_deciles": sum(d is not None for d in deciles),
        "min_days": min_days,
        "max_days": max_days,
    }
    return deciles, coverage


def signed_log_errors_pct(clean_test: list[DirectionalPair], fn: Callable) -> np.ndarray:
    """100 * ln(converted / actual) per row (positive = converted slower than swum); NaN when the
    method has no conversion."""
    out = np.full(len(clean_test), np.nan)
    for i, p in enumerate(clean_test):
        pred = fn(p)
        if pred:
            out[i] = 100.0 * math.log(pred / p.target_time_cs)
    return out


def ability_bias_columns(
    clean_test: list[DirectionalPair], deciles: list[int | None], signed: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    """Per-row columns for the pair-mean-decile bias: for each method, orientation (forward =
    SCY->LCM, SCY->SCM, SCM->LCM; reverse = the opposite) and decile, the row's signed % error,
    NaN outside the group."""
    orient = np.array([_canonical_orientation(p)[1] for p in clean_test])
    dec = np.array([-1 if d is None else d for d in deciles])
    columns = {}
    for name, errs in signed.items():
        for side in ("forward", "reverse"):
            for d in range(10):
                mask = (orient == side) & (dec == d)
                columns[f"{name}|{side}|D{d + 1}"] = np.where(mask, errs, np.nan)
    return columns


def percentile_preservation(clean_test: list[DirectionalPair], predictors: dict, min_pairs: int = 20) -> dict:
    """Within each direction, event and category of the held-out pairs (the same swimmers in both
    courses), compare the converted time's percentile among the actual target-course times with
    the entered time's percentile among the source-course times. Positive = the converted time
    ranks slower than the entered one did. Reported overall and by source-percentile decile."""
    groups: dict[tuple, list[DirectionalPair]] = defaultdict(list)
    for p in clean_test:
        groups[(p.direction, p.event_key, p.category)].append(p)

    def mid_rank(sorted_vals: np.ndarray, values: np.ndarray) -> np.ndarray:
        below = np.searchsorted(sorted_vals, values, side="left")
        upto = np.searchsorted(sorted_vals, values, side="right")
        return 100.0 * (below + upto) / (2.0 * len(sorted_vals))

    out = {}
    for name, fn in predictors.items():
        shifts: list[float] = []
        by_decile: dict[int, list[float]] = defaultdict(list)
        for group in groups.values():
            if len(group) < min_pairs:
                continue
            src = np.array([p.source_time_cs for p in group], dtype=np.float64)
            dst = np.array([p.target_time_cs for p in group], dtype=np.float64)
            preds = [fn(p) for p in group]
            keep = np.array([pr is not None for pr in preds])
            conv = np.array([pr if pr is not None else 0 for pr in preds], dtype=np.float64)
            p_src = mid_rank(np.sort(src), src)
            p_conv = mid_rank(np.sort(dst), conv)
            for ps, pc, k in zip(p_src, p_conv, keep):
                if k:
                    shifts.append(pc - ps)
                    by_decile[min(9, int(ps // 10))].append(pc - ps)
        arr = np.array(shifts)
        out[name] = {
            "evaluated": len(shifts),
            "mean_abs_shift_points": round(float(np.abs(arr).mean()), 3) if len(arr) else None,
            "mean_signed_shift_points": round(float(arr.mean()), 3) if len(arr) else None,
            "mean_signed_shift_by_source_decile": {
                f"D{d + 1}": round(float(np.mean(by_decile[d])), 3) for d in range(10) if by_decile[d]
            },
        }
    return out


def clustered_bootstrap(
    clusters: list[str], columns: dict[str, np.ndarray], n_boot: int, seed: int
) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    """Cluster bootstrap of column means (NaN = row not in that column). Resampling clusters with
    replacement is a multinomial count per cluster, so each replicate mean is a ratio of weighted
    per-cluster sums. Returns point means and replicate means."""
    keys = sorted(set(clusters))
    index = {k: i for i, k in enumerate(keys)}
    rows = np.array([index[c] for c in clusters])
    names = list(columns)
    values = np.column_stack([columns[n] for n in names])
    present = ~np.isnan(values)
    sums = np.zeros((len(keys), len(names)))
    counts = np.zeros((len(keys), len(names)))
    np.add.at(sums, rows, np.where(present, values, 0.0))
    np.add.at(counts, rows, present.astype(np.float64))
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(len(keys), np.full(len(keys), 1.0 / len(keys)), size=n_boot).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = (draws @ sums) / (draws @ counts)
        point = sums.sum(axis=0) / counts.sum(axis=0)
    return dict(zip(names, point)), {n: boot[:, j] for j, n in enumerate(names)}


def _interval(point: float, replicates: np.ndarray, digits: int = 4) -> dict:
    reps = replicates[~np.isnan(replicates)]
    if not len(reps) or math.isnan(point):
        return {}
    se = float(np.std(reps))
    out = {
        "estimate": round(float(point), digits),
        "ci95_low": round(float(np.quantile(reps, 0.025)), digits),
        "ci95_high": round(float(np.quantile(reps, 0.975)), digits),
        "se": round(se, digits),
    }
    return out


def _delta_summary(point: float, replicates: np.ndarray) -> dict:
    summary = _interval(point, replicates)
    se = summary.get("se", 0.0)
    summary["z_score"] = round(point / se, 1) if se > 1e-9 else 0.0
    # Two-sided normal p-value from the bootstrap standard error; Holm-adjusted across families.
    summary["p_value"] = round(math.erfc(abs(point / se) / math.sqrt(2.0)), 6) if se > 1e-9 else 1.0
    return summary


CANDIDATE = "turnmark_equivalence"


def mae_bootstrap_families(
    clean_test: list[DirectionalPair], abs_errors: dict[str, np.ndarray], clusters: list[str], n_boot: int, seed: int
) -> dict:
    """Clustered bootstrap of MAE and of the candidate's MAE difference from each baseline, for the
    overall test set and each event, direction and event-group family; Holm-adjusted per comparison."""
    families = {
        "overall_clean_test": list(range(len(clean_test))),
        "sprint_50_100": [i for i, p in enumerate(clean_test) if p.event_key in ("50-FR", "100-FR", "100-BK", "100-BR", "100-FL")],
        "middle_200_400": [i for i, p in enumerate(clean_test) if p.event_key in ("200-FR", "400-FR", "200-BK", "200-BR", "200-IM")],
        "distance_800_1500": [i for i, p in enumerate(clean_test) if p.event_key in ("800-FR", "1500-FR")],
        "specialty_200fl_400im": [i for i, p in enumerate(clean_test) if p.event_key in ("200-FL", "400-IM")],
        "scm_all_directions": [i for i, p in enumerate(clean_test) if "SCM" in p.direction],
    }
    for direction in ALL_DIRECTIONS:
        families[f"dir_{direction.replace('->', '_to_')}"] = [i for i, p in enumerate(clean_test) if p.direction == direction]
    for ev in CANONICAL_EVENT_ORDER:
        families[f"event_{ev.replace('-', '_')}"] = [i for i, p in enumerate(clean_test) if p.event_key == ev]
    results = {}
    for family, idxs in families.items():
        if len({clusters[i] for i in idxs}) < 5 or len(idxs) < 10:
            continue
        sel = np.array(idxs)
        columns = {f"mae|{n}": e[sel] for n, e in abs_errors.items()}
        for ref in abs_errors:
            if ref != CANDIDATE:
                columns[f"delta|{ref}"] = abs_errors[CANDIDATE][sel] - abs_errors[ref][sel]
        point, boot = clustered_bootstrap([clusters[i] for i in idxs], columns, n_boot, seed)
        results[family] = {
            "evaluated_pairs": len(idxs),
            "clusters": len({clusters[i] for i in idxs}),
            "bootstrap_replicates": n_boot,
            "mae_seconds": {n: _interval(point[f"mae|{n}"], boot[f"mae|{n}"]) for n in abs_errors},
            **{
                f"comparisons_vs_{ref}": {CANDIDATE: _delta_summary(point[f"delta|{ref}"], boot[f"delta|{ref}"])}
                for ref in abs_errors
                if ref != CANDIDATE
            },
        }
    _apply_holm_correction(results)
    return results


def ability_bias_bootstrap(
    clean_test: list[DirectionalPair], deciles: list[int | None], signed: dict[str, np.ndarray], clusters: list[str], n_boot: int, seed: int
) -> dict:
    """Signed % bias by pair-mean ability decile and orientation, with clustered bootstrap intervals,
    plus each method's tail spread (fastest-decile bias minus slowest-decile bias, forward)."""
    columns = ability_bias_columns(clean_test, deciles, signed)
    point, boot = clustered_bootstrap(clusters, columns, n_boot, seed)
    out = {}
    for name in signed:
        entry = {side: {} for side in ("forward", "reverse")}
        for side in ("forward", "reverse"):
            for d in range(1, 11):
                key = f"{name}|{side}|D{d}"
                entry[side][f"D{d}"] = _interval(point[key], boot[key], 3)
        entry["tail_spread_forward_D1_minus_D10"] = _interval(
            point[f"{name}|forward|D1"] - point[f"{name}|forward|D10"],
            boot[f"{name}|forward|D1"] - boot[f"{name}|forward|D10"],
            3,
        )
        entry["max_abs_decile_bias_pct"] = round(
            max(abs(point[f"{name}|{side}|D{d}"]) for side in ("forward", "reverse") for d in range(1, 11)), 3
        )
        fwd = np.array([point[f"{name}|forward|D{d}"] for d in range(1, 11)])
        reps = np.column_stack([boot[f"{name}|forward|D{d}"] for d in range(1, 11)])
        reps = reps[~np.isnan(reps).any(axis=1)]
        entry["forward_decile_range_pct"] = round(float(fwd.max() - fwd.min()), 3)
        # Shape test: are the ten forward decile biases equal? Wald statistic of their deviations from
        # their mean with the bootstrap covariance (9 degrees of freedom; 5% critical value 16.92).
        dev = fwd - fwd.mean()
        cov = np.cov((reps - reps.mean(axis=1, keepdims=True)).T)
        entry["forward_shape_wald_chi2_9"] = round(float(dev @ np.linalg.pinv(cov) @ dev), 1)
        mid = lambda m: m[..., 1:5].mean(axis=-1) - m[..., 6:9].mean(axis=-1)  # noqa: E731
        entry["forward_D2_5_minus_D7_9"] = _interval(float(mid(fwd)), mid(reps), 3)
        out[name] = entry
    return out


def ability_bias_by_course_pair(clean_test: list[DirectionalPair], deciles: list[int | None], signed: dict[str, np.ndarray]) -> dict:
    """Point estimates of the pair-mean-decile bias for each course pair separately."""
    out = {}
    for a, b in COURSE_PAIRS:
        sel = [i for i, p in enumerate(clean_test) if _canonical_orientation(p)[0] == (a, b)]
        sub = [clean_test[i] for i in sel]
        cols = ability_bias_columns(sub, [deciles[i] for i in sel], {n: e[np.array(sel)] for n, e in signed.items()})
        entry = {}
        for name in signed:
            entry[name] = {
                side: {
                    f"D{d}": (round(float(np.nanmean(col)), 3) if np.any(~np.isnan(col)) else None)
                    for d in range(1, 11)
                    for col in (cols[f"{name}|{side}|D{d}"],)
                }
                for side in ("forward", "reverse")
            }
        out[f"{a}<->{b}"] = {"evaluated_rows": len(sub), "methods": entry}
    return out


def meet_cluster(p: DirectionalPair) -> str:
    """One meet per underlying pair (the lexically smaller of its two meets), so both directions of a
    pair share a cluster. Dependence through the other meet remains."""
    return min(p.source_meet_id, p.target_meet_id)


def fast_swimmer_pair(age_band: str = "unknown") -> DirectionalPair:
    ex = FAST_SWIMMER_EXAMPLE
    return DirectionalPair(
        swimmer_key="example", partition="test", direction=f"{ex['course']}->{ex['to']}",
        event_key="1500-FR", stroke="freestyle", source_course=ex["course"], target_course=ex["to"],
        source_distance=ex["distance"], target_distance=mapped_distance(ex["course"], ex["to"], "freestyle", ex["distance"]),
        category=ex["category"], source_time_cs=ex["time_cs"], target_time_cs=0, age_years=None, age_band=age_band,
        gap_days=0, signed_gap_days=0, source_year=2026, target_year=2026, region="example",
        source_meet_id="example", target_meet_id="example", is_ratio_outlier=False,
    )


def fast_swimmer_example(predictors: dict) -> dict:
    ex = FAST_SWIMMER_EXAMPLE
    sample = fast_swimmer_pair()
    out = {
        "input": f"{format_clock_cs(ex['time_cs'])} {ex['distance']} yd {ex['course']} freestyle ({ex['category']})",
        "target": f"{sample.target_distance} m {ex['to']}",
        "converted": {},
    }
    for name, fn in predictors.items():
        for band in (("17-18", "19+") if name == "percentile_age_aware" else (None,)):
            p = fast_swimmer_pair(band or "unknown")
            pred = fn(p)
            label = name if band is None else f"{name} (age {band})"
            entry = {"time": format_clock_cs(pred) if pred else None}
            if pred:
                back = fn(requery(p, ex["to"], ex["course"], pred))
                entry["converted_back"] = format_clock_cs(back) if back else None
            out["converted"][label] = entry
    return out


def venue_cohorts(clean_test: list[DirectionalPair], venue_lookup: dict[str, dict], predictors: dict) -> dict:
    """Facility cohorts compare the facility each meet's ZIP or city resolved to; that is a locality
    proxy, not a verified building. The altitude cohort is a proxy too: a meet counts if the venue
    lookup flags it (mountain-state, listed high-elevation locality, or a declared altitude) or the
    pair comes from the Utah or Montana archive; no flag is not evidence of sea level."""
    cohorts: dict[str, list[DirectionalPair]] = defaultdict(list)
    for p in clean_test:
        v_src = venue_lookup.get(p.source_meet_id)
        v_dst = venue_lookup.get(p.target_meet_id)
        if v_src and v_dst:
            f_src = v_src.get("facility_id")
            f_dst = v_dst.get("facility_id")
            if f_src and f_dst:
                cohorts["same_matched_facility" if f_src == f_dst else "different_matched_facility"].append(p)
            if v_src.get("is_altitude") or v_dst.get("is_altitude") or p.region in ("Utah Swimming", "Montana Swimming"):
                cohorts["altitude_proxy_meet_involved"].append(p)
            else:
                cohorts["no_altitude_flag_both_meets"].append(p)
        elif p.region in ("Utah Swimming", "Montana Swimming") or (v_src and v_src.get("is_altitude")) or (v_dst and v_dst.get("is_altitude")):
            cohorts["altitude_proxy_meet_involved"].append(p)
    out = {}
    for name, sub in sorted(cohorts.items()):
        if len(sub) < 10:
            continue
        out[name] = {
            "evaluated_pairs": len(sub),
            "evaluated_swimmers": len({p.swimmer_key for p in sub}),
            "models": {},
        }
        for model, fn in predictors.items():
            m = compute_metrics(sub, [fn(p) for p in sub])
            out[name]["models"][model] = {k: m[k] for k in ("mae_seconds", "median_ae_seconds", "signed_bias_seconds")}
    return out


def fit_predictors(train_pairs: list[DirectionalPair], noise: dict[tuple[str, str], float]) -> tuple[dict, EquivalenceModel]:
    """Fit every compared method on Train and return name -> predictor."""
    equivalence = EquivalenceModel()
    equivalence.fit(train_pairs, noise)
    flat = FlatMultiplierModel()
    flat.fit(train_pairs)
    same_input = AnchoredPercentileModel(age_aware=False)
    same_input.fit(train_pairs)
    age_aware = AnchoredPercentileModel(age_aware=True)
    age_aware.fit(train_pairs)
    predictors = {
        "ncaa_2025_27": lambda p: predict_ncaa_cs(
            p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance, p.category
        ),
        "colorado_2026": lambda p: predict_colorado_cs(
            p.source_time_cs, p.source_course, p.target_course, p.stroke, p.source_distance
        ),
        "flat_empirical_multiplier": flat.predict,
        # Same inputs as the equivalence model: no age band.
        "percentile_same_input": same_input.predict,
        "percentile_age_aware": age_aware.predict,
    }
    predictors[CANDIDATE] = equivalence.predict
    return predictors, equivalence


def evaluate_split(
    train_pairs: list[DirectionalPair],
    test_pairs: list[DirectionalPair],
    repeats: list[RepeatSwim],
    venue_lookup: dict[str, dict] | None = None,
    full: bool = False,
    n_boot: int = 2000,
    seed: int = 20261023,
    instruments: InstrumentIndex | None = None,
) -> tuple[dict, dict]:
    """Fit on Train (repeat-swim noise from the same training swimmers) and evaluate on Test."""
    noise = estimate_course_noise(repeats)
    predictors, equivalence = fit_predictors(train_pairs, noise)
    clean_test = [p for p in test_pairs if not p.is_ratio_outlier]
    results: dict = {"clean_test": {}, "by_direction": {}}
    for name, fn in predictors.items():
        results["clean_test"][name] = compute_metrics(clean_test, [fn(p) for p in clean_test])
    for direction in ALL_DIRECTIONS:
        sub = [p for p in clean_test if p.direction == direction]
        if len(sub) >= 10:
            results["by_direction"][direction] = {
                name: {k: m[k] for k in ("evaluated_pairs", "mae_seconds", "signed_bias_seconds", "mape_percent")}
                for name, fn in predictors.items()
                for m in (compute_metrics(sub, [fn(p) for p in sub]),)
            }
    deciles = pair_mean_deciles(clean_test)
    signed = {name: signed_log_errors_pct(clean_test, fn) for name, fn in predictors.items()}
    swimmer_clusters = [p.swimmer_key for p in clean_test]
    boot_n = n_boot if full else 400
    results["ability_bias_by_pair_mean_decile"] = {
        "description": "Mean signed % error, 100 * ln(converted / actual), by decile of the pair's mean log time within its course pair, event and category (D1 fastest). Forward = SCY->LCM, SCY->SCM, SCM->LCM. The bin variable shares the pair's measurement errors, so with unequal course noise even the true equivalence map shows a trend here: a coupled diagnostic, not a test of ability bias.",
        "swimmer_clustered": ability_bias_bootstrap(clean_test, deciles, signed, swimmer_clusters, boot_n, seed),
    }
    if instruments is not None:
        independent, coverage = independent_swim_deciles(clean_test, instruments)
        results["ability_bias_by_independent_swim_decile"] = {
            "description": "Mean signed % error by decile of a separate swim's log time: " + " ".join(independent_swim_deciles.__doc__.split("Decile (0 = fastest) of ")[1].split()),
            "coverage": coverage,
            "swimmer_clustered": (
                ability_bias_bootstrap(clean_test, independent, signed, swimmer_clusters, boot_n, seed)
                if coverage["rows_in_deciles"]
                else {}
            ),
        }
    results["percentile_preservation"] = percentile_preservation(clean_test, predictors)
    results["roundtrip_and_transitivity_on_test_swims"] = roundtrip_and_transitivity(clean_test, predictors)
    meta = {"equivalence": equivalence, "noise": noise, "predictors": predictors}
    if not full:
        return results, meta

    results["untrimmed_test"] = {name: compute_metrics(test_pairs, [fn(p) for p in test_pairs]) for name, fn in predictors.items()}
    results["by_event"] = {}
    for ev in CANONICAL_EVENT_ORDER:
        sub = [p for p in clean_test if p.event_key == ev]
        if not sub:
            continue
        results["by_event"][ev] = {
            "display_label": EVENT_DISPLAY_LABELS.get(ev, ev),
            "evaluated_pairs": len(sub),
            "evaluated_swimmers": len({p.swimmer_key for p in sub}),
            "models": {
                name: {k: m[k] for k in ("mae_seconds", "median_ae_seconds", "rmse_seconds", "mape_percent", "signed_bias_seconds", "within_1_0_pct")}
                for name, fn in predictors.items()
                for m in (compute_metrics(sub, [fn(p) for p in sub]),)
            },
        }
    results["by_age_band"] = {}
    for band in ("10u", "11-12", "13-14", "15-16", "17-18", "19+"):
        sub = [p for p in clean_test if p.age_band == band]
        if len(sub) >= 10:
            results["by_age_band"][band] = {
                name: {"pairs": len(sub), "mae_seconds": m["mae_seconds"], "signed_bias_seconds": m["signed_bias_seconds"]}
                for name, fn in predictors.items()
                for m in (compute_metrics(sub, [fn(p) for p in sub]),)
            }
    results["ability_bias_by_pair_mean_decile"]["meet_clustered"] = ability_bias_bootstrap(
        clean_test, deciles, signed, [meet_cluster(p) for p in clean_test], n_boot, seed
    )
    results["ability_bias_by_pair_mean_decile"]["by_course_pair"] = ability_bias_by_course_pair(clean_test, deciles, signed)
    abs_errors = {
        name: np.array([abs((pred if pred is not None else p.source_time_cs) - p.target_time_cs) / 100.0 for p in clean_test for pred in (fn(p),)])
        for name, fn in predictors.items()
    }
    results["bootstrap_mae"] = {
        "swimmer_clustered": mae_bootstrap_families(clean_test, abs_errors, swimmer_clusters, n_boot, seed),
        "meet_clustered_overall": mae_bootstrap_families(
            clean_test, abs_errors, [meet_cluster(p) for p in clean_test], n_boot, seed
        )["overall_clean_test"],
    }
    results["fast_swimmer_example"] = fast_swimmer_example(predictors)
    if venue_lookup:
        results["by_venue_cohort"] = venue_cohorts(clean_test, venue_lookup, predictors)
    meta["cell_support"] = equivalence.cell_support(train_pairs, clean_test)
    return results, meta


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


def _apply_holm_correction(results: dict) -> None:
    """Holm-adjust each (comparison, model) p-value across every reported bootstrap family."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for family in results.values():
        for comparison, by_model in family.items():
            if comparison.startswith("comparisons_vs_"):
                for model, summary in by_model.items():
                    groups[(comparison, model)].append(summary)
    for summaries in groups.values():
        ordered = sorted(summaries, key=lambda d: d["p_value"])
        running = 0.0
        for rank, summary in enumerate(ordered):
            running = max(running, min(1.0, (len(ordered) - rank) * summary["p_value"]))
            summary["holm_p_value"] = round(running, 6)
            summary["significant_after_holm_0_05"] = running < 0.05


def summarize_venue_matches(venues_csv: Path) -> dict:
    """Meet-to-facility locality match counts, one row per unique meet in the venue CSV."""
    import csv

    with venues_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    basis = Counter(row["match_basis"] for row in rows)
    return {
        "unique_meets": len(rows),
        "matched_facility": sum(1 for row in rows if row["matched_facility_id"]),
        "matched_by_postal_code": basis["postal_code_5"],
        "matched_by_city_state": basis["city_state"],
        "unmatched": basis["unmatched"],
        "with_locality_coordinates": sum(1 for row in rows if row["locality_latitude"]),
    }


def load_venue_lookup(venues_csv: Path | None) -> dict[str, dict]:
    if venues_csv is None:
        return {}
    if not venues_csv.exists():
        raise FileNotFoundError(f"Venue CSV not found: {venues_csv} (pass --venues-csv, or None for no venue cohorts)")
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


def underlying_pair_key(p: DirectionalPair) -> tuple:
    """The two races behind a directional row, so a pair and its reverse share one key."""
    return (
        p.swimmer_key,
        p.event_key,
        frozenset(((p.source_course, p.source_meet_id), (p.target_course, p.target_meet_id))),
    )


def pair_counts(pairs: list[DirectionalPair]) -> dict:
    """Raw and clean directional rows, distinct underlying swim pairs and swimmers for one population."""
    clean = [p for p in pairs if not p.is_ratio_outlier]
    return {
        "directional_pairs": len(pairs),
        "clean_directional_pairs": len(clean),
        "underlying_pairs": len({underlying_pair_key(p) for p in pairs}),
        "clean_underlying_pairs": len({underlying_pair_key(p) for p in clean}),
        "swimmers": len({p.swimmer_key for p in pairs}),
        "clean_swimmers": len({p.swimmer_key for p in clean}),
    }


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


def measure_lakehouse_view(duckdb_path: Path) -> dict:
    """Read the Iceberg snapshot the `races` view actually scans, and its row count, from the
    database itself. Honors an explicit `snapshot_from_id`; any other selector is rejected rather
    than reported as the table's current snapshot."""
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        con.execute("LOAD iceberg")
        view_sql = con.execute("SELECT sql FROM duckdb_views() WHERE view_name = 'races'").fetchone()[0]
        rows = con.execute("SELECT count(*) FROM races").fetchone()[0]
    finally:
        con.close()
    return {"iceberg_snapshot_id": _scanned_snapshot_id(view_sql), "rows": rows}


def _scanned_snapshot_id(view_sql: str) -> int:
    """The snapshot an `iceberg_scan(...)` view definition reads."""
    from pyiceberg.table import StaticTable

    match = re.search(r"iceberg_scan\(\s*'((?:[^']|'')*)'(.*?)\)", view_sql, flags=re.S)
    if match is None:
        raise ValueError(f"`races` view is not a single iceberg_scan over table metadata: {view_sql}")
    location = match.group(1).replace("''", "'")
    options = match.group(2)
    # pyiceberg's own file IO opens the metadata location as written, including file:// URIs.
    metadata = StaticTable.from_metadata(location).metadata
    snapshot_ids = {snapshot.snapshot_id for snapshot in metadata.snapshots}
    explicit = re.search(r"snapshot_from_id\s*:?=\s*(\d+)", options)
    if explicit:
        snapshot_id = int(explicit.group(1))
        if snapshot_id not in snapshot_ids:
            raise ValueError(f"view selects snapshot {snapshot_id}, which the table metadata does not contain")
        return snapshot_id
    if re.search(r"snapshot|version", options, flags=re.I):
        raise ValueError(f"unsupported iceberg_scan snapshot selector in `races` view: {options.strip()}")
    return metadata.current_snapshot_id


def load_swims_from_duckdb(duckdb_path: Path) -> list[SwimRecord]:
    """Fast DuckDB/Iceberg best-of-meet extraction for multi-million-row checkpoints."""
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        con.execute("LOAD iceberg")
        # Collapse same-meet rounds in SQL first: keep one complete row per swimmer, meet, course,
        # distance, stroke and category. Rows that deduplicate_best_of_meet would keep (supported
        # stroke and category, time inside the plausibility bounds) rank ahead of rows it would
        # drop, then ties break by (time, date, race id) exactly as it does. So an impossible fastest
        # round can't hide a valid slower one, and a group with no valid round passes one row
        # through for Python to screen and count.
        bounds = ", ".join(
            f"('{course}', {distance}, {lo}, {MAX_PLAUSIBLE_CS[distance]})"
            for (course, distance), lo in MIN_PLAUSIBLE_CS.items()
            if distance in MAX_PLAUSIBLE_CS
        )
        strokes = ", ".join(f"'{stroke}'" for stroke in STROKE_CODE)
        sql = """
            SELECT source, race_id, swimmer_id, meet_id, race_date, course, distance, stroke,
                   category, time_cs, age_years, coalesce(region, 'unknown') AS region
            FROM races
            LEFT JOIN (VALUES {bounds}) AS bounds(b_course, b_distance, lo_cs, hi_cs)
              ON races.course = bounds.b_course AND races.distance = bounds.b_distance
            WHERE distance IN (50, 100, 200, 400, 500, 800, 1000, 1500, 1650)
              AND NOT (distance = 50 AND stroke != 'freestyle')
              AND NOT (distance = 100 AND stroke = 'individual-medley')
            QUALIFY row_number() OVER (
                PARTITION BY source, swimmer_id, meet_id, course, distance, stroke, category
                ORDER BY
                    CASE WHEN stroke IN ({strokes}) AND category IN ('women', 'men')
                              AND time_cs BETWEEN lo_cs AND hi_cs THEN 0 ELSE 1 END,
                    time_cs, race_date, race_id
            ) = 1
            ORDER BY source, swimmer_id, meet_id, course, distance, stroke, category
        """.format(bounds=bounds, strokes=strokes)
        rows = con.execute(sql).fetchall()
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


def compute_swims_sha256(swims: Iterable[SwimRecord]) -> str:
    """Deterministic SHA-256 digest over loaded candidate swim records."""
    h = hashlib.sha256()
    for s in sorted(
        swims,
        key=lambda r: (
            r.source,
            r.race_id,
            r.swimmer_id,
            r.meet_id,
            r.race_date.isoformat(),
            r.course,
            r.distance,
            r.stroke,
            r.category,
            r.time_cs,
        ),
    ):
        h.update(
            f"{s.source}|{s.race_id}|{s.swimmer_id}|{s.meet_id}|{s.race_date.isoformat()}|{s.course}|{s.distance}|{s.stroke}|{s.category}|{s.time_cs}|{s.age_years}|{s.region}\n".encode(
                "utf-8"
            )
        )
    return h.hexdigest()


LEAVE_OUT_REGIONS = frozenset(
    {
        "Southeastern Swimming",
        "Adirondack Swimming",
        "South Dakota Swimming",
        "Potomac Valley Swimming",
        "Midwestern Swimming",
    }
)


def start_independent_tasks(tasks: dict[str, tuple[Callable[..., dict], tuple]]) -> Callable[[], dict[str, dict]]:
    """Run independent, deterministic evaluation tasks in fresh worker processes and return a
    function that waits for their results. Workers are spawned, not forked: by this point the
    parent has used DuckDB, whose threads make fork able to deadlock a child on macOS. Each task
    is a module-level function and its arguments, pickled to the worker."""
    import concurrent.futures

    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=len(tasks), mp_context=multiprocessing.get_context("spawn")
    )
    futures = {name: executor.submit(fn, *args) for name, (fn, args) in tasks.items()}

    def wait() -> dict[str, dict]:
        try:
            return {name: future.result() for name, future in futures.items()}
        finally:
            executor.shutdown()

    return wait



def temporal_holdout_splits(
    pairs: list[DirectionalPair], repeats: list[RepeatSwim]
) -> tuple[list[DirectionalPair], list[DirectionalPair], list[RepeatSwim]]:
    """Train on <= 2025 pairs from training-partition swimmers and test on 2026 pairs from
    test-partition swimmers: later in time and swimmer-disjoint. Repeat-swim noise uses the same
    training swimmers and years."""
    train = [p for p in pairs if p.partition == "train" and p.source_year <= 2025 and p.target_year <= 2025]
    test = [p for p in pairs if p.partition == "test" and p.source_year >= 2026 and p.target_year >= 2026]
    return train, test, [r for r in repeats if r.partition == "train" and r.year <= 2025]


def leave_regions_out_splits(
    pairs: list[DirectionalPair], repeats: list[RepeatSwim]
) -> tuple[list[DirectionalPair], list[DirectionalPair], list[RepeatSwim]]:
    """Test on every pair from LEAVE_OUT_REGIONS. Train on the other regions' train- and
    test-partition pairs after removing every swimmer with any pair in a held-out region, so the
    holdout is both region-disjoint and swimmer-disjoint."""
    test = [p for p in pairs if p.region in LEAVE_OUT_REGIONS]
    heldout = {p.swimmer_key for p in test}
    train = [
        p
        for p in pairs
        if p.partition in ("train", "test") and p.region not in LEAVE_OUT_REGIONS and p.swimmer_key not in heldout
    ]
    fit_repeats = [
        r
        for r in repeats
        if r.partition in ("train", "test") and r.region not in LEAVE_OUT_REGIONS and r.swimmer_key not in heldout
    ]
    return train, test, fit_repeats


def _holdout(splits: tuple, insufficient: str, instruments: InstrumentIndex) -> dict:
    train, test, repeats = splits
    if len(train) < 50 or len(test) < 20:
        return {"status": insufficient}
    results, _ = evaluate_split(train, test, repeats, instruments=instruments)
    return {
        "training_set": pair_counts(train),
        "test_set": pair_counts(test),
        **results,
    }


def _temporal_holdout(pairs: list[DirectionalPair], repeats: list[RepeatSwim], instruments: InstrumentIndex) -> dict:
    return _holdout(temporal_holdout_splits(pairs, repeats), "insufficient_temporal_split", instruments)


def _regions_holdout(pairs: list[DirectionalPair], repeats: list[RepeatSwim], instruments: InstrumentIndex) -> dict:
    return _holdout(leave_regions_out_splits(pairs, repeats), "insufficient_regional_split", instruments)


def validation_curvature(
    train: list[DirectionalPair], validation: list[DirectionalPair], repeats: list[RepeatSwim], instruments: InstrumentIndex
) -> dict:
    """The fixed linear map, fitted on Train, scored on Validation: MAE and the decile biases by the
    less-coupled independent-swim diagnostic and by the coupled pair-mean one. This is where any
    remaining curvature is examined and whether a nonlinear stage deserves a known-truth experiment
    is decided; Test is not used for it, and nothing here changes the shipped map."""
    results, _ = evaluate_split(train, validation, repeats, instruments=instruments)
    keep = (CANDIDATE, "ncaa_2025_27", "flat_empirical_multiplier")
    out = {"rule": " ".join(validation_curvature.__doc__.split()), "mae_seconds": {n: results["clean_test"][n]["mae_seconds"] for n in keep}}
    for block in ("ability_bias_by_independent_swim_decile", "ability_bias_by_pair_mean_decile"):
        out[block] = {
            "coverage": results[block].get("coverage"),
            **{n: results[block]["swimmer_clustered"][n] for n in keep if n in results[block]["swimmer_clustered"]},
        }
    return out


INTERVAL_DISCLOSURE = (
    "Bootstrap intervals resample swimmers (primary) or one meet per pair (sensitivity) with the fitted "
    "models held fixed. They do not cover model-selection uncertainty: the shrinkage priors and "
    "the noise ratios were estimated once, and the 30-day window and the outlier screen were chosen "
    "once; none is re-estimated or re-chosen inside each replicate. They also do not remove residual "
    "dependence: a pair joins two meets but is clustered on one, swimmers share clubs, coaches and "
    "taper cycles, and same-day conditions (pool, timing system, altitude) correlate errors across "
    "swimmers in ways neither clustering captures."
)


def run_pipeline(
    swims: list[SwimRecord],
    input_label: str,
    max_days: int = 30,
    output_dir: Path | None = None,
    public_summary_path: Path | None = None,
    venues_csv: Path | None = DEFAULT_VENUES_CSV,
    export_empirical_json: Path | None = None,
    lakehouse_snapshot_path: Path | None = None,
    export_parity_fixture: Path | None = None,
    measured_lakehouse: dict | None = None,
    n_boot: int = 2000,
    precision_boot: int = 200,
) -> dict:
    loaded_swims_sha256 = compute_swims_sha256(swims)
    lakehouse_meta: dict = {}
    if lakehouse_snapshot_path is not None:
        # A DuckDB run must record which lakehouse snapshot it read; a missing or unreadable
        # snapshot.json fails the run instead of producing a receipt without provenance.
        snap_raw = json.loads(lakehouse_snapshot_path.read_text(encoding="utf-8"))
        # The sidecar's claims must describe the database that was actually read.
        if measured_lakehouse is None:
            raise ValueError("A lakehouse snapshot sidecar needs the measured view to check it against")
        for claim, measured in (("iceberg_snapshot_id", "iceberg_snapshot_id"), ("rows", "rows")):
            if snap_raw.get(claim) != measured_lakehouse[measured]:
                raise ValueError(
                    f"snapshot.json {claim}={snap_raw.get(claim)} does not match the opened view "
                    f"({measured_lakehouse[measured]})"
                )
        lakehouse_meta = {
            "iceberg_snapshot_id": snap_raw["iceberg_snapshot_id"],
            "lakehouse_input_sha256": snap_raw["input_sha256"],
            "archive_usable_races": snap_raw.get("rows"),
            "sources_count": len(snap_raw.get("manifest", {}).get("sources", [])),
        }

    dedup_swims, hygiene_stats = deduplicate_best_of_meet(swims)
    pairs_30 = build_directional_pairs(dedup_swims, max_days=max_days)
    pairs_14 = build_directional_pairs(dedup_swims, max_days=14)
    pairs_60 = build_directional_pairs(dedup_swims, max_days=60)
    repeats = build_repeat_swims(dedup_swims, max_days=max_days)
    venue_lookup = load_venue_lookup(venues_csv)

    train_sw = [p for p in pairs_30 if p.partition == "train"]
    val_sw = [p for p in pairs_30 if p.partition == "validation"]
    test_sw = [p for p in pairs_30 if p.partition == "test"]
    train_repeats = [r for r in repeats if r.partition == "train"]
    # Every evaluated split draws its test rows from these: the validation and test partitions and the held-out regions.
    instruments = build_instrument_index(dedup_swims, (p for p in pairs_30 if p.partition != "train" or p.region in LEAVE_OUT_REGIONS))
    curvature = validation_curvature(train_sw, val_sw, train_repeats, instruments)

    # The two further holdouts don't depend on the main fit or on each other, so they run alongside it.
    wait_for_independent = start_independent_tasks(
        {
            "temporal": (_temporal_holdout, (pairs_30, repeats, instruments)),
            "leave_regions_out": (_regions_holdout, (pairs_30, repeats, instruments)),
        }
    )

    swimmer_holdout, meta = evaluate_split(
        train_sw, test_sw, train_repeats, venue_lookup=venue_lookup, full=True, n_boot=n_boot, instruments=instruments
    )
    predictors = meta["predictors"]
    equivalence: EquivalenceModel = meta["equivalence"]
    equivalence.precise_ranges, precision = precise_latent_ranges(equivalence, train_sw, meta["noise"], n_boot=precision_boot)
    clean_test = [p for p in test_sw if not p.is_ratio_outlier]
    test_caveats = Counter(equivalence.caveat(p) or "none" for p in clean_test)
    swimmer_holdout["caveat_shares_on_test"] = {k: round(v / len(clean_test), 4) for k, v in sorted(test_caveats.items())} if clean_test else {}
    swimmer_holdout["fast_swimmer_example"]["turnmark_equivalence_caveat"] = equivalence.caveat(fast_swimmer_pair())
    swimmer_holdout["validation"] = {
        name: compute_metrics(clean_val, [fn(p) for p in clean_val])
        for clean_val in ([p for p in val_sw if not p.is_ratio_outlier],)
        for name, fn in predictors.items()
    }

    evaluated_at_str = datetime.now(timezone.utc).date().isoformat()
    script_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    snapshot = equivalence.export_snapshot_dict(
        revision=f"{evaluated_at_str} ({input_label})",
        evaluated_at=evaluated_at_str,
    )
    snapshot["source"]["evaluator_sha256"] = script_sha256
    snapshot["source"]["loaded_swims_sha256"] = loaded_swims_sha256
    if lakehouse_meta.get("iceberg_snapshot_id") is not None:
        snapshot["source"]["iceberg_snapshot_id"] = lakehouse_meta["iceberg_snapshot_id"]
    if lakehouse_meta.get("lakehouse_input_sha256") is not None:
        snapshot["source"]["lakehouse_input_sha256"] = lakehouse_meta["lakehouse_input_sha256"]
    if export_empirical_json is not None:
        export_empirical_json.write_text(
            json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    if export_parity_fixture is not None:
        export_parity_fixture.write_text(
            json.dumps(build_empirical_parity_fixture(snapshot), indent=1) + "\n", encoding="utf-8"
        )

    model_meta = {
        **equivalence.metadata(),
        "cell_support": meta["cell_support"],
        "low_evidence_directional_cells": len(snapshot["lowEvidenceCells"]),
        "validation_curvature": curvature,
        "precision_bootstrap": precision,
        "repeat_swims_for_noise": len(train_repeats),
        "evaluator_script_sha256": script_sha256,
        "exported_empirical_cells_sha256": snapshot["source"]["sha256"],
        "loaded_swims_sha256": loaded_swims_sha256,
    }
    if lakehouse_meta:
        model_meta["lakehouse_provenance"] = lakehouse_meta

    # Matching-window sensitivity: 14-, 30- and 60-day test sets with the same fitted models.
    window_sensitivity = {}
    for w_label, w_pairs in (("14d", pairs_14), ("30d", pairs_30), ("60d", pairs_60)):
        w_test = [p for p in w_pairs if p.partition == "test" and not p.is_ratio_outlier]
        if w_test:
            window_sensitivity[w_label] = {
                "evaluated_pairs": len(w_test),
                "evaluated_swimmers": len({p.swimmer_key for p in w_test}),
                **{f"{name}_mae_s": compute_metrics(w_test, [fn(p) for p in w_test])["mae_seconds"] for name, fn in predictors.items()},
            }

    independent = wait_for_independent()

    hygiene_block = {}
    if lakehouse_meta.get("archive_usable_races") is not None:
        hygiene_block["archive_usable_races"] = lakehouse_meta["archive_usable_races"]
    hygiene_block.update(hygiene_stats)

    report = {
        "checkpoint": EVALUATION_CHECKPOINT,
        "evaluated_at": evaluated_at_str,
        "scope": "aggregate local model evaluation receipt; no swimmer-level records",
        "model": "turnmark-empirical-2026: equivalence map, linear in log time per event, category and course onto one SCY-anchored latent scale, held at the edge ratio beyond the training support",
        "input_source": input_label,
        "input_provenance": {
            "input_label": input_label,
            "loaded_swims_sha256": loaded_swims_sha256,
            **lakehouse_meta,
            "venues_csv_sha256": hashlib.sha256(venues_csv.read_bytes()).hexdigest() if venues_csv else None,
        },
        "meet_locality_matches": summarize_venue_matches(venues_csv) if venues_csv else None,
        "matching_window_days": max_days,
        "hygiene_and_pairing": {
            **hygiene_block,
            "directional_pairs_14d": len(pairs_14),
            "directional_pairs_30d": len(pairs_30),
            "directional_pairs_60d": len(pairs_60),
            "unique_undirected_pairs_30d": len({underlying_pair_key(p) for p in pairs_30}),
            "ratio_outliers_flagged_30d": sum(1 for p in pairs_30 if p.is_ratio_outlier),
            "clean_directional_pairs_30d": sum(1 for p in pairs_30 if not p.is_ratio_outlier),
            "swimmers_with_pairs_30d": len({p.swimmer_key for p in pairs_30}),
            "same_course_repeat_swims_30d": len(repeats),
            "by_direction_30d": dict(sorted(Counter(p.direction for p in pairs_30 if not p.is_ratio_outlier).items())),
            "by_event_30d": {
                ev: sum(1 for p in pairs_30 if not p.is_ratio_outlier and p.event_key == ev)
                for ev in CANONICAL_EVENT_ORDER
            },
            "by_region_30d": dict(sorted(Counter(p.region for p in pairs_30 if not p.is_ratio_outlier).items())),
        },
        "partitions_30d": {
            part: pair_counts([p for p in pairs_30 if p.partition == part])
            for part in ("train", "validation", "test")
        },
        "training_set": pair_counts(train_sw),
        "model_metadata": model_meta,
        "snapshot_arithmetic": snapshot_arithmetic_properties(snapshot),
        "interval_disclosure": INTERVAL_DISCLOSURE,
        "window_sensitivity_test": window_sensitivity,
        "swimmer_disjoint_holdout": swimmer_holdout,
        "temporal_2026_holdout": independent["temporal"],
        "leave_regions_out_holdout": independent["leave_regions_out"],
        # Whether this run wrote data/empirical.json.
        "exported_to_engine": bool(export_empirical_json is not None),
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

    snapshot_path: Path | None = None
    measured_lakehouse: dict | None = None
    if args.duckdb:
        swims = load_swims_from_duckdb(args.duckdb)
        # Default to the lakehouse directory name rather than a hardcoded checkpoint label.
        label = args.input_label or args.duckdb.resolve().parent.name
        snapshot_path = args.duckdb.resolve().parent / "snapshot.json"
        measured_lakehouse = measure_lakehouse_view(args.duckdb)
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
        # Regenerated with every export so the engine parity cases always describe the shipped cells.
        export_parity_fixture=EMPIRICAL_PARITY_FIXTURE if args.export_empirical_json else None,
        lakehouse_snapshot_path=snapshot_path,
        measured_lakehouse=measured_lakehouse,
    )
    print(json.dumps({name: m["mae_seconds"] for name, m in report["swimmer_disjoint_holdout"]["clean_test"].items()}, indent=2))


if __name__ == "__main__":
    main()
