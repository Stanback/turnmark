"""Forward-only "likely time" predictor POC (research only, not wired into any app).

Question answered: a swimmer swam X in course A on day d_s; what will they most likely swim in
the same event in course B on a later day d_t, and within what 80% range?

This is a *prediction* (age, progression, gap and the swimmer's own history matter), not the
symmetric course *equivalence* the converter ships. Every feature is computed from swims dated on
or before the source swim, which is itself strictly before the target swim; the only target-side
inputs are the target date (which the user supplies) and, as the label, the target time. Examples
require an age recorded on the source swim.

Evaluation design:
- Temporal: models train on examples whose target swim is before CUTOFF; the test set is target
  swims on or after CUTOFF. Interval quantiles are calibrated on validation-partition swimmers
  with targets in the year before CUTOFF.
- Swimmer-disjoint (headline): train / validation / test use the shared deterministic 70/15/15
  swimmer partition from evaluate_and_train.swimmer_partition.
- Non-disjoint (real use case): the model may also train on the test swimmers' own pre-cutoff
  examples. It is scored on the same test rows, so the two are directly comparable.

Models, simplest first:
  ncaa      NCAA 2025-27 factor (the shipped default conversion).
  flat      Per (direction, event, sex) median ratio from training targets.
  pooled    Huber regression on log(target/source), offset by the NCAA log factor, with
            unpenalized direction-level terms and ridge-shrunk per-cell deviations, plus age,
            gap and age x gap progression terms.
  history   pooled + the swimmer's own history known at the source date: recent best in the
            target course, and the source time against their recent best in the source course.
  gbm       Small residual GBM on top of `history`, kept only if it clearly beats it.

Public outputs carry aggregates only: no swimmer IDs, names, dates or individual times. Cells
with fewer than MIN_REPORT_ROWS rows or MIN_REPORT_SWIMMERS swimmers are suppressed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import evaluate_and_train as ET  # noqa: E402  (read-only reuse: loader, dedupe, partition, NCAA)

DEFAULT_DUCKDB = Path("/Users/bri/Projects/Stanback/turnmark/target/lakehouse-national-17/queries.duckdb")
DEFAULT_RECEIPT = HERE / "predictor-receipt-checkpoint-17.json"

# Integer direction codes index this tuple, so its order is pinned here (it fixes the design
# matrix column order and therefore the receipt) rather than borrowed from the equivalence code.
DIRECTIONS = ("SCY->LCM", "LCM->SCY", "SCM->LCM", "LCM->SCM", "SCY->SCM", "SCM->SCY")
assert set(DIRECTIONS) == set(ET.ALL_DIRECTIONS)
EVENTS = ET.CANONICAL_EVENT_ORDER
SEXES = ("women", "men")
N_CELLS = len(DIRECTIONS) * len(EVENTS) * len(SEXES)
PARTITIONS = ("train", "validation", "test")

CUTOFF = date(2026, 1, 1)
CALIBRATION_START = date(2025, 1, 1)
MAX_GAP_DAYS = 365
HISTORY_WINDOW_DAYS = 365
GAP_BUCKETS = ((1, 30), (31, 90), (91, 180), (181, 365))
INTERVAL_LEVEL = 0.80
Q_LO, Q_HI = (1.0 - INTERVAL_LEVEL) / 2.0, 1.0 - (1.0 - INTERVAL_LEVEL) / 2.0
MIN_CALIBRATION_ROWS = 300
MIN_REPORT_ROWS = 50
MIN_REPORT_SWIMMERS = 20
# Freestyle distances that are not the standard event for their course (e.g. a 400 free swum in
# yards) would collide with the 500Y/400M canonical key, so they are dropped before pairing.
NONSTANDARD_FREE = {("SCY", 400), ("SCY", 800), ("SCY", 1500), ("LCM", 500), ("LCM", 1000),
               ("LCM", 1650), ("SCM", 500), ("SCM", 1000), ("SCM", 1650)}
EPOCH = date(1970, 1, 1)


def day_number(d: date) -> int:
    return (d - EPOCH).days


def cell_index(direction: int, event: int, sex: int) -> int:
    return (direction * len(EVENTS) + event) * len(SEXES) + sex


def gap_bucket_label(gap: int) -> str:
    for lo, hi in GAP_BUCKETS:
        if lo <= gap <= hi:
            return f"{lo}-{hi}d"
    return "out-of-range"


# ---------------------------------------------------------------------------------------------
# Examples: forward-only (source, target) pairs plus history known at the source date
# ---------------------------------------------------------------------------------------------


@dataclass
class Examples:
    """Column store of forward examples. Arrays share one row order."""

    cols: dict[str, np.ndarray]

    def __len__(self) -> int:
        return len(self.cols["tgt_cs"])

    def __getattr__(self, name: str) -> np.ndarray:
        try:
            return self.cols[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def subset(self, mask: np.ndarray) -> "Examples":
        return Examples({k: v[mask] for k, v in self.cols.items()})


def _swims_arrow(swims: Iterable[ET.SwimRecord]):
    """Best-of-meet swims to an Arrow table keyed by an integer person code."""
    import pyarrow as pa

    codes: dict[tuple[str, str], int] = {}
    part_of: list[int] = []
    cols: dict[str, list] = {k: [] for k in ("swimmer", "part", "course", "ev", "stroke", "distance",
                                              "sex", "d", "t", "age")}
    for s in swims:
        if s.category not in SEXES or (s.stroke == "freestyle" and (s.course, s.distance) in NONSTANDARD_FREE):
            continue
        key = (s.source, s.swimmer_id)
        code = codes.get(key)
        if code is None:
            code = len(codes)
            codes[key] = code
            part_of.append(PARTITIONS.index(ET.swimmer_partition(s.source, s.swimmer_id)))
        metric = ET.canonical_metric_distance(s.course, s.stroke, s.distance)
        cols["swimmer"].append(code)
        cols["part"].append(part_of[code])
        cols["course"].append(s.course)
        cols["ev"].append(EVENTS.index(f"{metric}-{ET.STROKE_CODE[s.stroke]}"))
        cols["stroke"].append(s.stroke)
        cols["distance"].append(s.distance)
        cols["sex"].append(SEXES.index(s.category))
        cols["d"].append(s.race_date)
        cols["t"].append(s.time_cs)
        cols["age"].append(s.age_years)
    return pa.table(cols)


EXAMPLE_SQL = """
CREATE OR REPLACE TABLE ex AS
SELECT row_number() OVER () - 1 AS rid, * FROM (
  {unions}
) ORDER BY tgt_day, swimmer, dir, ev;
"""

DIRECTION_SQL = """
SELECT t.swimmer, t.part, {dir} AS dir, t.ev, t.sex,
       s.t::DOUBLE AS src_cs, t.t::DOUBLE AS tgt_cs,
       datediff('day', DATE '1970-01-01', s.d) AS src_day,
       datediff('day', DATE '1970-01-01', t.d) AS tgt_day,
       datediff('day', s.d, t.d) AS gap,
       s.age AS age,
       month(t.d) AS tgt_month,
       s.d AS src_date
FROM (SELECT * FROM swims WHERE course = '{dst}') t
ASOF JOIN (SELECT * FROM swims WHERE course = '{src}') s
  ON t.swimmer = s.swimmer AND t.ev = s.ev AND t.sex = s.sex AND t.d > s.d
WHERE datediff('day', s.d, t.d) BETWEEN 1 AND {max_gap}
  AND s.age IS NOT NULL AND isfinite(s.age)
"""
# Target-side columns read above: t.t is the label; t.d is the target meet date the user supplies
# (gap, target month); swimmer/ev/sex are the join keys, equal to the source's. Nothing else from
# the target record may enter a feature. Age must be recorded on the source swim: an example whose
# source age is missing is dropped, never backfilled from the target or imputed.

HISTORY_SQL = """
CREATE OR REPLACE TABLE ex_hist AS
WITH tb AS (
  SELECT e.rid, min(h.t)::DOUBLE AS tb_cs, arg_min(h.d, h.t) AS tb_date
  FROM ex e JOIN swims h
    ON h.swimmer = e.swimmer AND h.ev = e.ev AND h.sex = e.sex AND h.course = {tgt_course_expr}
   AND h.d <= e.src_date AND h.d >= e.src_date - INTERVAL {window} DAY
  GROUP BY e.rid
), sp AS (
  SELECT e.rid, min(h.t)::DOUBLE AS sp_cs
  FROM ex e JOIN swims h
    ON h.swimmer = e.swimmer AND h.ev = e.ev AND h.sex = e.sex AND h.course = {src_course_expr}
   AND h.d < e.src_date AND h.d >= e.src_date - INTERVAL {window} DAY
  GROUP BY e.rid
)
SELECT e.* EXCLUDE (src_date), tb.tb_cs,
       datediff('day', tb.tb_date, e.src_date) AS tb_days, sp.sp_cs
FROM ex e LEFT JOIN tb USING (rid) LEFT JOIN sp USING (rid)
ORDER BY e.rid
"""


def _course_case(column: str, pos: int) -> str:
    """SQL CASE mapping a direction index to its source (pos=0) or target (pos=1) course."""
    whens = " ".join(f"WHEN {i} THEN '{d.split('->')[pos]}'" for i, d in enumerate(DIRECTIONS))
    return f"(CASE {column} {whens} END)"


def build_examples(swims: Iterable[ET.SwimRecord], max_gap_days: int = MAX_GAP_DAYS) -> Examples:
    """Pair every target swim with the swimmer's most recent earlier swim of the same event in
    each other course (gap 1..max_gap_days), and attach history known at the source date. A pair
    whose source swim has no recorded age is dropped."""
    import duckdb

    con = duckdb.connect()
    try:
        con.register("swims_arrow", _swims_arrow(swims))
        con.execute("CREATE TABLE swims AS SELECT * FROM swims_arrow")
        unions = "\nUNION ALL\n".join(
            DIRECTION_SQL.format(dir=i, src=d.split("->")[0], dst=d.split("->")[1], max_gap=max_gap_days)
            for i, d in enumerate(DIRECTIONS)
        )
        con.execute(EXAMPLE_SQL.format(unions=unions))
        con.execute(
            HISTORY_SQL.format(
                tgt_course_expr=_course_case("e.dir", 1),
                src_course_expr=_course_case("e.dir", 0),
                window=HISTORY_WINDOW_DAYS,
            )
        )
        raw = con.execute("SELECT * FROM ex_hist").fetchnumpy()
    finally:
        con.close()
    cols: dict[str, np.ndarray] = {}
    for k, v in raw.items():
        arr = np.ma.filled(v.astype(float), np.nan) if np.ma.isMaskedArray(v) else np.asarray(v)
        if k in ("age", "tb_cs", "tb_days", "sp_cs", "src_cs", "tgt_cs"):
            cols[k] = np.asarray(arr, dtype=float)
        else:
            cols[k] = np.asarray(arr, dtype=np.int64)
    cols["cell"] = cell_index(cols["dir"], cols["ev"], cols["sex"])
    return Examples(cols)


# ---------------------------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------------------------


def ncaa_log_factor_table() -> np.ndarray:
    """log(NCAA ratio) per cell; falls back to the geometric pool factor where NCAA has none."""
    out = np.zeros(N_CELLS)
    for di, d in enumerate(DIRECTIONS):
        src, dst = d.split("->")
        for ei, ev in enumerate(EVENTS):
            metric, code = ev.split("-")
            stroke = next(s for s, c in ET.STROKE_CODE.items() if c == code)
            src_dist = _source_distance(src, stroke, int(metric))
            for si, sex in enumerate(SEXES):
                pred = ET.predict_ncaa_cs(10_000_000, src, dst, stroke, src_dist, sex)
                if pred is not None:
                    ratio = pred / 10_000_000
                else:
                    ratio = ET.geometric_physics_factor(src, dst, stroke, src_dist) or 1.0
                out[cell_index(di, ei, si)] = math.log(ratio)
    return out


def _source_distance(course: str, stroke: str, metric: int) -> int:
    if course == "SCY" and stroke == "freestyle":
        return {400: 500, 800: 1000, 1500: 1650}.get(metric, metric)
    return metric


def predict_ncaa(ex: Examples) -> np.ndarray:
    """NCAA factor applied to the source time, truncated to hundredths like the engine."""
    table = ncaa_log_factor_table()
    return np.floor(ex.src_cs * np.exp(table[ex.cell]) + 1e-6)


class FlatMultiplier:
    """Median target/source ratio per cell from training rows (NCAA when a cell is unseen)."""

    def fit(self, ex: Examples) -> "FlatMultiplier":
        self.log_ratio = ncaa_log_factor_table().copy()
        y = np.log(ex.tgt_cs / ex.src_cs)
        for c in np.unique(ex.cell):
            m = ex.cell == c
            if m.sum() >= 20:
                self.log_ratio[c] = float(np.median(y[m]))
        return self

    def predict(self, ex: Examples) -> np.ndarray:
        return ex.src_cs * np.exp(self.log_ratio[ex.cell])


# ---------------------------------------------------------------------------------------------
# Pooled shrinkage regression on log(target/source)
# ---------------------------------------------------------------------------------------------

AGE_KNOTS = (10.0, 12.0, 16.0, 18.0)
TARGET_COURSES = ("SCY", "LCM", "SCM")
TARGET_COURSE_OF_DIR = np.array([TARGET_COURSES.index(d.split("->")[1]) for d in DIRECTIONS])


def month_block(ex: Examples) -> np.ndarray:
    """Target-month one-hot per target course (January is the reference): the season and its
    championship taper, known to the app once the swimmer names the target meet."""
    out = np.zeros((len(ex), len(TARGET_COURSES) * 11))
    m = ex.tgt_month.astype(int)
    rows = np.flatnonzero(m >= 2)
    out[rows, TARGET_COURSE_OF_DIR[ex.dir[rows]] * 11 + (m[rows] - 2)] = 1.0
    return out


def age_basis(age: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Linear + hinge basis in age (clamped 8..23); missing ages route to an indicator."""
    missing = ~np.isfinite(age)
    a = np.clip(np.where(missing, 14.0, age), 8.0, 23.0)
    cols = [(a - 14.0) / 4.0] + [np.maximum(0.0, a - k) / 4.0 for k in AGE_KNOTS]
    basis = np.stack(cols, axis=1)
    basis[missing] = 0.0
    return basis, missing.astype(float)


@dataclass
class FeatureSpec:
    use_history: bool
    n_age: int = 1 + len(AGE_KNOTS)

    def names(self) -> list[str]:
        g = [f"age{i}" for i in range(self.n_age)] + ["age_missing", "gap", "gap2", "gap_x_z", "z2"]
        g += [f"{c}_month{m:02d}" for c in TARGET_COURSES for m in range(2, 13)]
        g += [f"gap_x_age{i}" for i in range(self.n_age)] + ["gap_x_age_missing"]
        if self.use_history:
            g += ["hb", "hb_missing", "hb_x_stale", "hb_x_gap", "trend", "trend_missing", "trend_x_gap"]
        d = []
        for di in range(len(DIRECTIONS)):
            d += [f"dir{di}_int", f"dir{di}_z"] + [f"dir{di}_age{i}" for i in range(self.n_age)]
        c = [f"cell{ci}_int" for ci in range(N_CELLS)] + [f"cell{ci}_z" for ci in range(N_CELLS)]
        return g + d + c

    def n_penalized(self) -> int:
        return 2 * N_CELLS


@dataclass
class Standardizer:
    """log(source time) mean/sd per (source course, event, sex) from training rows."""

    mu: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sd: np.ndarray = field(default_factory=lambda: np.ones(0))

    @staticmethod
    def group(ex: Examples) -> np.ndarray:
        src_course = np.array([["SCY", "LCM", "SCM"].index(d.split("->")[0]) for d in DIRECTIONS])
        return (src_course[ex.dir] * len(EVENTS) + ex.ev) * len(SEXES) + ex.sex

    def fit(self, ex: Examples) -> "Standardizer":
        n_groups = 3 * len(EVENTS) * len(SEXES)
        g = self.group(ex)
        x = np.log(ex.src_cs)
        self.mu = np.full(n_groups, float(np.mean(x)))
        self.sd = np.full(n_groups, float(np.std(x)) or 1.0)
        for k in np.unique(g):
            m = g == k
            if m.sum() >= 20:
                self.mu[k] = float(np.mean(x[m]))
                self.sd[k] = max(float(np.std(x[m])), 1e-3)
        return self

    def z(self, ex: Examples) -> np.ndarray:
        g = self.group(ex)
        return np.clip((np.log(ex.src_cs) - self.mu[g]) / self.sd[g], -3.0, 3.0)


def design(ex: Examples, spec: FeatureSpec, std: Standardizer, flat_log: np.ndarray) -> np.ndarray:
    n = len(ex)
    z = std.z(ex)
    ab, am = age_basis(ex.age)
    g = ex.gap / 365.0
    blocks = [ab, am[:, None], g[:, None], (g * g)[:, None], (g * z)[:, None], (z * z)[:, None],
              month_block(ex), ab * g[:, None], (am * g)[:, None]]
    if spec.use_history:
        hb_raw = np.log(ex.tb_cs / ex.src_cs) - flat_log[ex.cell]
        hb_missing = ~np.isfinite(hb_raw)
        hb = np.where(hb_missing, 0.0, np.clip(hb_raw, -0.3, 0.3))
        stale = np.where(hb_missing, 0.0, np.clip(ex.tb_days, 0, 365) / 365.0)
        tr_raw = np.log(ex.src_cs / ex.sp_cs)
        tr_missing = ~np.isfinite(tr_raw)
        tr = np.where(tr_missing, 0.0, np.clip(tr_raw, -0.3, 0.3))
        blocks += [hb[:, None], hb_missing[:, None].astype(float), (hb * stale)[:, None],
                   (hb * g)[:, None], tr[:, None], tr_missing[:, None].astype(float), (tr * g)[:, None]]
    nd = len(DIRECTIONS)
    per_dir = 2 + spec.n_age
    dblock = np.zeros((n, nd * per_dir))
    rows = np.arange(n)
    base = ex.dir * per_dir
    dblock[rows, base] = 1.0
    dblock[rows, base + 1] = z
    for i in range(spec.n_age):
        dblock[rows, base + 2 + i] = ab[:, i]
    cblock = np.zeros((n, 2 * N_CELLS))
    cblock[rows, ex.cell] = 1.0
    cblock[rows, N_CELLS + ex.cell] = z
    return np.hstack(blocks + [dblock, cblock])


def training_weights(ex: Examples) -> np.ndarray:
    """1/sqrt(rows per swimmer x direction x event) so prolific swimmers don't dominate."""
    key = (ex.swimmer * len(DIRECTIONS) + ex.dir) * len(EVENTS) + ex.ev
    _, inv, counts = np.unique(key, return_inverse=True, return_counts=True)
    w = 1.0 / np.sqrt(counts[inv])
    return w / w.mean()


class PooledRegression:
    """Huber IRLS on y = log(target/source) - log(NCAA factor), ridge on per-cell deviations."""

    def __init__(self, use_history: bool, ridge: float = 100.0, huber_k: float = 1.345,
                 iterations: int = 8, chunk: int = 400_000):
        self.spec = FeatureSpec(use_history)
        self.ridge = ridge
        self.huber_k = huber_k
        self.iterations = iterations
        self.chunk = chunk

    def _chunks(self, n: int):
        for start in range(0, n, self.chunk):
            yield slice(start, min(n, start + self.chunk))

    def fit(self, ex: Examples, std: Standardizer, flat: FlatMultiplier) -> "PooledRegression":
        self.std = std
        self.flat_log = flat.log_ratio
        self.offset_table = ncaa_log_factor_table()
        n = len(ex)
        y = np.log(ex.tgt_cs / ex.src_cs) - self.offset_table[ex.cell]
        w0 = training_weights(ex)
        robust = np.ones(n)
        p = len(self.spec.names())
        pen = np.zeros(p)
        pen[-self.spec.n_penalized():] = self.ridge
        pen[: p - self.spec.n_penalized()] = 1e-6
        beta = np.zeros(p)
        for _ in range(self.iterations):
            xtx = np.zeros((p, p))
            xty = np.zeros(p)
            for sl in self._chunks(n):
                x = design(ex.subset(np.arange(sl.start, sl.stop)), self.spec, std, self.flat_log)
                w = w0[sl] * robust[sl]
                xw = x * w[:, None]
                xtx += xw.T @ x
                xty += xw.T @ y[sl]
            new_beta = np.linalg.solve(xtx + np.diag(pen), xty)
            resid = y - self._linear(ex, new_beta)
            scale = 1.4826 * float(np.median(np.abs(resid))) or 1e-3
            a = np.abs(resid) / (self.huber_k * scale)
            robust = np.where(a <= 1.0, 1.0, 1.0 / np.maximum(a, 1e-12))
            converged = np.max(np.abs(new_beta - beta)) < 1e-6
            beta = new_beta
            if converged:
                break
        self.beta = beta
        self.scale = scale
        return self

    def _linear(self, ex: Examples, beta: np.ndarray) -> np.ndarray:
        out = np.empty(len(ex))
        for sl in self._chunks(len(ex)):
            out[sl] = design(ex.subset(np.arange(sl.start, sl.stop)), self.spec, self.std, self.flat_log) @ beta
        return out

    def predict_log_ratio(self, ex: Examples) -> np.ndarray:
        return self.offset_table[ex.cell] + self._linear(ex, self.beta)

    def predict(self, ex: Examples) -> np.ndarray:
        return ex.src_cs * np.exp(self.predict_log_ratio(ex))

    def coefficients(self) -> dict[str, float]:
        names = self.spec.names()
        keep = len(names) - self.spec.n_penalized() - len(DIRECTIONS) * (2 + self.spec.n_age)
        return {k: round(float(v), 5) for k, v in zip(names[:keep], self.beta[:keep])}


# ---------------------------------------------------------------------------------------------
# Small residual GBM (only kept if it clearly beats the linear model)
# ---------------------------------------------------------------------------------------------


def gbm_features(ex: Examples, std: Standardizer, flat_log: np.ndarray) -> np.ndarray:
    hb = np.log(ex.tb_cs / ex.src_cs) - flat_log[ex.cell]
    tr = np.log(ex.src_cs / ex.sp_cs)
    return np.stack([
        ex.dir.astype(float), ex.ev.astype(float), ex.sex.astype(float), std.z(ex),
        np.where(np.isfinite(ex.age), ex.age, -1.0), ex.gap.astype(float),
        np.where(np.isfinite(hb), hb, -9.0), np.where(np.isfinite(ex.tb_days), ex.tb_days, -1.0),
        np.where(np.isfinite(tr), tr, -9.0), ex.tgt_month.astype(float),
    ], axis=1)


class ResidualGBM:
    """Depth-limited histogram boosting of clipped log residuals (L2 on Huber-clipped targets)."""

    def __init__(self, n_bins: int = 32, depth: int = 3, lr: float = 0.1, max_trees: int = 150,
                 min_leaf: float = 200.0, l2: float = 50.0, patience: int = 15):
        self.n_bins, self.depth, self.lr = n_bins, depth, lr
        self.max_trees, self.min_leaf, self.l2, self.patience = max_trees, min_leaf, l2, patience

    def _bin(self, x: np.ndarray) -> np.ndarray:
        out = np.empty(x.shape, dtype=np.int16)
        for j in range(x.shape[1]):
            out[:, j] = np.searchsorted(self.edges[j], x[:, j], side="right")
        return out

    def _grow(self, xb, r, w, idx, depth):
        g_sum, w_sum = float(np.sum(r[idx] * w[idx])), float(np.sum(w[idx]))
        leaf = {"value": g_sum / (w_sum + self.l2)}
        if depth == 0 or w_sum < 2 * self.min_leaf:
            return leaf
        best = (0.0, None, None)
        parent_score = g_sum * g_sum / (w_sum + self.l2)
        for j in range(xb.shape[1]):
            nb = len(self.edges[j]) + 1
            gh = np.bincount(xb[idx, j], weights=r[idx] * w[idx], minlength=nb)
            wh = np.bincount(xb[idx, j], weights=w[idx], minlength=nb)
            gl, wl = np.cumsum(gh)[:-1], np.cumsum(wh)[:-1]
            gr, wr = g_sum - gl, w_sum - wl
            ok = (wl >= self.min_leaf) & (wr >= self.min_leaf)
            if not ok.any():
                continue
            gain = np.where(ok, gl * gl / (wl + self.l2) + gr * gr / (wr + self.l2) - parent_score, -np.inf)
            b = int(np.argmax(gain))
            if gain[b] > best[0]:
                best = (float(gain[b]), j, b)
        if best[1] is None:
            return leaf
        j, b = best[1], best[2]
        left = idx[xb[idx, j] <= b]
        right = idx[xb[idx, j] > b]
        return {"feature": j, "bin": b, "left": self._grow(xb, r, w, left, depth - 1),
                "right": self._grow(xb, r, w, right, depth - 1)}

    def _apply(self, node, xb, idx, out):
        if "value" in node:
            out[idx] += node["value"]
            return
        mask = xb[idx, node["feature"]] <= node["bin"]
        self._apply(node["left"], xb, idx[mask], out)
        self._apply(node["right"], xb, idx[~mask], out)

    def fit(self, x, r, w, x_val, r_val, scale: float) -> "ResidualGBM":
        self.edges = [np.unique(np.quantile(x[:, j], np.linspace(0, 1, self.n_bins + 1)[1:-1]))
                      for j in range(x.shape[1])]
        xb, xvb = self._bin(x), self._bin(x_val)
        clip = 3.0 * scale
        f, fv = np.zeros(len(r)), np.zeros(len(r_val))
        self.trees: list[dict] = []
        best_mae, best_n, since = float(np.mean(np.abs(r_val))), 0, 0
        all_idx, val_idx = np.arange(len(r)), np.arange(len(r_val))
        for _ in range(self.max_trees):
            tree = self._grow(xb, np.clip(r - f, -clip, clip), w, all_idx, self.depth)
            tree = _scale_tree(tree, self.lr)
            self.trees.append(tree)
            self._apply(tree, xb, all_idx, f)
            self._apply(tree, xvb, val_idx, fv)
            mae = float(np.mean(np.abs(r_val - fv)))
            if mae < best_mae - 1e-7:
                best_mae, best_n, since = mae, len(self.trees), 0
            else:
                since += 1
                if since >= self.patience:
                    break
        self.trees = self.trees[:best_n]
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        xb = self._bin(x)
        out = np.zeros(len(x))
        idx = np.arange(len(x))
        for t in self.trees:
            self._apply(t, xb, idx, out)
        return out


def _scale_tree(node: dict, lr: float) -> dict:
    if "value" in node:
        return {"value": node["value"] * lr}
    return {**node, "left": _scale_tree(node["left"], lr), "right": _scale_tree(node["right"], lr)}


# ---------------------------------------------------------------------------------------------
# Prediction intervals: residual quantiles conditioned on gap x age (x history availability)
# ---------------------------------------------------------------------------------------------


SPEED_BANDS = ((-np.inf, -1.0, "fast"), (-1.0, 1.0, "middle"), (1.0, np.inf, "slow"))


def speed_band_labels(ex: Examples, std: Standardizer) -> np.ndarray:
    """Source speed within (source course, event, sex) across all ages: z < -1 is 'fast'."""
    z = std.z(ex)
    out = np.empty(len(ex), dtype=object)
    for lo, hi, lab in SPEED_BANDS:
        out[(z >= lo) & (z < hi)] = lab
    return out


def interval_keys(ex: Examples, use_history: bool, std: Standardizer) -> list[tuple[str, ...]]:
    """(gap bucket, age band, target-course history?, speed band) per row."""
    gap = [gap_bucket_label(int(g)) for g in ex.gap]
    age = [ET.age_band_label(a if math.isfinite(a) else None) for a in ex.age]
    hist = np.where(np.isfinite(ex.tb_cs), "hist", "nohist") if use_history else np.full(len(ex), "-")
    return list(zip(gap, age, hist.tolist(), speed_band_labels(ex, std).tolist()))


# Fallback order, finest first: drop age, then speed, then history, then everything.
INTERVAL_LEVELS = ((0, 1, 2, 3), (0, 2, 3), (0, 2), (0,), ())


class ResidualQuantileIntervals:
    """Empirical log-residual quantiles per (gap bucket, age band, history?, speed band), falling
    back to coarser keys when a bucket has fewer than MIN_CALIBRATION_ROWS calibration rows."""

    def fit(self, keys: list[tuple[str, ...]], log_resid: np.ndarray) -> "ResidualQuantileIntervals":
        self.tables: list[dict[tuple, tuple[float, float]]] = []
        for level in INTERVAL_LEVELS:
            groups: dict[tuple, list[float]] = {}
            for k, r in zip(keys, log_resid):
                groups.setdefault(tuple(k[i] for i in level), []).append(float(r))
            self.tables.append({
                k: (float(np.quantile(v, Q_LO)), float(np.quantile(v, Q_HI)))
                for k, v in groups.items() if len(v) >= MIN_CALIBRATION_ROWS or not level
            })
        return self

    def bounds(self, keys: list[tuple[str, ...]]) -> tuple[np.ndarray, np.ndarray]:
        lo, hi = np.empty(len(keys)), np.empty(len(keys))
        for i, k in enumerate(keys):
            for level, table in zip(INTERVAL_LEVELS, self.tables):
                kk = tuple(k[j] for j in level)
                if kk in table:
                    lo[i], hi[i] = table[kk]
                    break
        return lo, hi


# ---------------------------------------------------------------------------------------------
# Metrics and swimmer-clustered bootstrap
# ---------------------------------------------------------------------------------------------


def point_metrics(pred: np.ndarray, ex: Examples) -> dict:
    err = (pred - ex.tgt_cs) / 100.0
    ae = np.abs(err)
    return {
        "rows": int(len(ae)),
        "swimmers": int(len(np.unique(ex.swimmer))),
        "mae_s": round(float(np.mean(ae)), 4),
        "median_ae_s": round(float(np.median(ae)), 4),
        "p90_ae_s": round(float(np.quantile(ae, 0.9)), 4),
        "signed_bias_s": round(float(np.mean(err)), 4),
        "mape_pct": round(float(100.0 * np.mean(ae * 100.0 / ex.tgt_cs)), 4),
    }


def reportable(ex: Examples) -> bool:
    return len(ex) >= MIN_REPORT_ROWS and len(np.unique(ex.swimmer)) >= MIN_REPORT_SWIMMERS


def clustered_bootstrap(ex: Examples, preds: dict[str, np.ndarray], comparisons: list[tuple[str, str]],
                        reps: int = 500, seed: int = 20261023) -> dict:
    """Resample swimmers with replacement; 95% percentile CIs for MAE, median AE, and MAE
    differences (a minus b; negative means a is better)."""
    rng = np.random.default_rng(seed)
    _, sw = np.unique(ex.swimmer, return_inverse=True)
    n_sw = int(sw.max()) + 1
    ae = {k: np.abs(v - ex.tgt_cs) / 100.0 for k, v in preds.items()}
    rows_per = np.bincount(sw, minlength=n_sw).astype(float)
    sums = {k: np.bincount(sw, weights=v, minlength=n_sw) for k, v in ae.items()}
    orders = {k: np.argsort(v) for k, v in ae.items()}
    mae_draws = {k: np.empty(reps) for k in ae}
    med_draws = {k: np.empty(reps) for k in ae}
    for b in range(reps):
        counts = np.bincount(rng.integers(0, n_sw, n_sw), minlength=n_sw).astype(float)
        denom = float(counts @ rows_per)
        row_w = counts[sw]
        for k in ae:
            mae_draws[k][b] = float(counts @ sums[k]) / denom
            o = orders[k]
            cw = np.cumsum(row_w[o])
            med_draws[k][b] = ae[k][o][np.searchsorted(cw, cw[-1] / 2.0)]

    def ci(x: np.ndarray) -> list[float]:
        return [round(float(np.quantile(x, 0.025)), 4), round(float(np.quantile(x, 0.975)), 4)]

    out = {
        "reps": reps,
        "clusters": n_sw,
        "mae_ci95_s": {k: ci(v) for k, v in mae_draws.items()},
        "median_ae_ci95_s": {k: ci(v) for k, v in med_draws.items()},
        "mae_difference_ci95_s": {},
    }
    for a, b_ in comparisons:
        d = mae_draws[a] - mae_draws[b_]
        point = float(np.mean(ae[a]) - np.mean(ae[b_]))
        out["mae_difference_ci95_s"][f"{a} - {b_}"] = {"point": round(point, 4), "ci95": ci(d)}
    return out


def coverage_summary(ex: Examples, lo_cs: np.ndarray, hi_cs: np.ndarray) -> dict:
    inside = (ex.tgt_cs >= lo_cs) & (ex.tgt_cs <= hi_cs)
    width = (hi_cs - lo_cs) / 100.0
    return {
        "rows": int(len(ex)),
        "coverage": round(float(np.mean(inside)), 4),
        "below_low": round(float(np.mean(ex.tgt_cs < lo_cs)), 4),
        "above_high": round(float(np.mean(ex.tgt_cs > hi_cs)), 4),
        "mean_width_s": round(float(np.mean(width)), 3),
        "median_width_s": round(float(np.median(width)), 3),
        "median_width_pct": round(float(np.median(100.0 * width * 100.0 / ex.tgt_cs)), 3),
    }


def grouped(ex: Examples, labels: np.ndarray, fn) -> dict:
    out = {}
    for lab in sorted(set(labels.tolist())):
        m = labels == lab
        sub = ex.subset(m)
        out[str(lab)] = fn(sub, m) if reportable(sub) else {"rows": int(m.sum()), "suppressed": True}
    return out


# ---------------------------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------------------------


def temporal_splits(ex: Examples, cutoff: date = CUTOFF, calibration_start: date = CALIBRATION_START,
                    disjoint: bool = True) -> dict[str, np.ndarray]:
    """Boolean row masks. Train/calibration targets are before the cutoff, test targets on or
    after it. Test rows are always test-partition swimmers; `disjoint=False` lets training see
    every partition's pre-cutoff rows, including the test swimmers' own earlier examples."""
    c, cs = day_number(cutoff), day_number(calibration_start)
    before = ex.tgt_day < c
    train_parts = (ex.part == 0) if disjoint else np.ones(len(ex), dtype=bool)
    return {
        "train": before & train_parts,
        "calibration": before & (ex.tgt_day >= cs) & (ex.part == 1),
        "test": (ex.tgt_day >= c) & (ex.part == 2),
    }


# ---------------------------------------------------------------------------------------------
# Worked examples (synthetic inputs only)
# ---------------------------------------------------------------------------------------------


def synthetic_example(direction: str, event: str, sex: str, source_cs: float, age: float, gap_days: int,
                      target_month: int = 7, target_best_cs: float | None = None, target_best_days_before: int | None = None,
                      source_prior_best_cs: float | None = None) -> Examples:
    def a(v, dtype=float):
        return np.array([v], dtype=dtype)

    di, ei, si = DIRECTIONS.index(direction), EVENTS.index(event), SEXES.index(sex)
    return Examples({
        "swimmer": a(-1, np.int64), "part": a(-1, np.int64), "dir": a(di, np.int64), "ev": a(ei, np.int64),
        "sex": a(si, np.int64), "src_cs": a(source_cs), "tgt_cs": a(np.nan), "src_day": a(0, np.int64),
        "tgt_day": a(gap_days, np.int64), "gap": a(gap_days, np.int64), "age": a(age),
        "tgt_month": a(target_month, np.int64), "tb_cs": a(np.nan if target_best_cs is None else target_best_cs),
        "tb_days": a(np.nan if target_best_days_before is None else target_best_days_before),
        "sp_cs": a(np.nan if source_prior_best_cs is None else source_prior_best_cs),
        "cell": a(cell_index(di, ei, si), np.int64),
    })


def format_cs(cs: float) -> str:
    cs = int(math.floor(cs + 1e-6))
    m, rem = divmod(cs, 6000)
    return f"{m}:{rem // 100:02d}.{rem % 100:02d}" if m else f"{rem // 100}.{rem % 100:02d}"


# ---------------------------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------------------------


@dataclass
class FittedPredictor:
    std: Standardizer
    flat: FlatMultiplier
    pooled: PooledRegression
    history: PooledRegression
    intervals: dict[str, ResidualQuantileIntervals]

    def predict_with_interval(self, ex: Examples, model: str = "history") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        m = self.history if model == "history" else self.pooled
        pred = m.predict(ex)
        lo, hi = self.intervals[model].bounds(interval_keys(ex, model == "history", self.std))
        return pred, pred * np.exp(lo), pred * np.exp(hi)


def choose_ridge(train: Examples, calib: Examples, std: Standardizer, flat: FlatMultiplier,
                 grid=(1.0, 10.0, 100.0, 1000.0)) -> tuple[float, dict]:
    scores = {}
    for lam in grid:
        m = PooledRegression(use_history=False, ridge=lam).fit(train, std, flat)
        scores[lam] = float(np.mean(np.abs(m.predict(calib) - calib.tgt_cs))) / 100.0
    best = min(scores, key=scores.get)
    return best, {str(k): round(v, 4) for k, v in scores.items()}


def fit_predictor(train: Examples, calib: Examples, ridge: float) -> FittedPredictor:
    std = Standardizer().fit(train)
    flat = FlatMultiplier().fit(train)
    pooled = PooledRegression(use_history=False, ridge=ridge).fit(train, std, flat)
    history = PooledRegression(use_history=True, ridge=ridge).fit(train, std, flat)
    intervals = {}
    for name, m in (("pooled", pooled), ("history", history)):
        resid = np.log(calib.tgt_cs) - np.log(m.predict(calib))
        intervals[name] = ResidualQuantileIntervals().fit(interval_keys(calib, name == "history", std), resid)
    return FittedPredictor(std, flat, pooled, history, intervals)


def run(duckdb_path: Path, receipt_path: Path, bootstrap_reps: int = 500) -> dict:
    receipt = evaluate_swims(ET.load_swims_from_duckdb(duckdb_path), bootstrap_reps)
    receipt["selection_effects"] = survivorship_summary(duckdb_path)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def evaluate_swims(swims: list[ET.SwimRecord], bootstrap_reps: int = 500) -> dict:
    swims_sha = ET.compute_swims_sha256(swims)
    dedup, hygiene = ET.deduplicate_best_of_meet(swims)
    del swims
    ex = build_examples(dedup)
    del dedup
    print(f"examples: {len(ex)}", flush=True)

    splits = temporal_splits(ex, disjoint=True)
    train, calib, test = (ex.subset(splits[k]) for k in ("train", "calibration", "test"))
    std0, flat0 = Standardizer().fit(train), FlatMultiplier().fit(train)
    ridge, ridge_scores = choose_ridge(train, calib, std0, flat0)
    print(f"ridge {ridge} {ridge_scores}", flush=True)
    fp = fit_predictor(train, calib, ridge)

    preds = {
        "ncaa": predict_ncaa(test),
        "flat": fp.flat.predict(test),
        "pooled": fp.pooled.predict(test),
        "history": fp.history.predict(test),
    }

    # Residual GBM over the history model: fit on a training subsample, early-stop on calibration.
    rng = np.random.default_rng(7)
    sub_idx = np.sort(rng.choice(len(train), size=min(len(train), 1_000_000), replace=False))
    tr_sub = train.subset(sub_idx)
    gx = gbm_features(tr_sub, fp.std, fp.flat.log_ratio)
    gr = np.log(tr_sub.tgt_cs) - np.log(fp.history.predict(tr_sub))
    gvx = gbm_features(calib, fp.std, fp.flat.log_ratio)
    gvr = np.log(calib.tgt_cs) - np.log(fp.history.predict(calib))
    gbm = ResidualGBM().fit(gx, gr, training_weights(tr_sub), gvx, gvr, fp.history.scale)
    preds["gbm"] = preds["history"] * np.exp(gbm.predict(gbm_features(test, fp.std, fp.flat.log_ratio)))
    print(f"gbm trees {len(gbm.trees)}", flush=True)

    # Non-disjoint variant: same test rows, training also sees test swimmers' own earlier rows.
    nd_splits = temporal_splits(ex, disjoint=False)
    nd_train = ex.subset(nd_splits["train"])
    nd_std, nd_flat = Standardizer().fit(nd_train), FlatMultiplier().fit(nd_train)
    nd_history = PooledRegression(use_history=True, ridge=ridge).fit(nd_train, nd_std, nd_flat)
    nd_pooled = PooledRegression(use_history=False, ridge=ridge).fit(nd_train, nd_std, nd_flat)
    nd_preds = {"pooled": nd_pooled.predict(test), "history": nd_history.predict(test)}

    return build_receipt(ex, splits, train, calib, test, fp, preds, nd_preds, gbm, ridge, ridge_scores,
                         hygiene, swims_sha, bootstrap_reps)


def build_receipt(ex, splits, train, calib, test, fp, preds, nd_preds, gbm, ridge, ridge_scores, hygiene,
                  swims_sha, bootstrap_reps) -> dict:
    models = list(preds)
    overall = {k: point_metrics(v, test) for k, v in preds.items()}
    boot = clustered_bootstrap(
        test, preds,
        [("pooled", "ncaa"), ("pooled", "flat"), ("history", "ncaa"), ("history", "flat"),
         ("history", "pooled"), ("gbm", "history"), ("flat", "ncaa")],
        reps=bootstrap_reps,
    )

    gap_lab = np.array([gap_bucket_label(int(g)) for g in test.gap])
    age_lab = np.array([ET.age_band_label(a if math.isfinite(a) else None) for a in test.age])
    dir_lab = np.array([DIRECTIONS[d] for d in test.dir])
    ev_lab = np.array([EVENTS[e] for e in test.ev])
    has_hist = np.where(np.isfinite(test.tb_cs), "with_target_course_history", "no_target_course_history")
    month_lab = np.array([f"{m:02d}" for m in test.tgt_month])
    speed_lab = speed_band_labels(test, fp.std).astype(str)

    def by(labels):
        return grouped(test, labels, lambda sub, m: {
            "rows": int(m.sum()),
            **{f"{k}_mae_s": round(float(np.mean(np.abs(v[m] - sub.tgt_cs))) / 100.0, 4) for k, v in preds.items()},
            "history_median_ae_s": round(float(np.median(np.abs(preds["history"][m] - sub.tgt_cs))) / 100.0, 4),
            "history_bias_s": round(float(np.mean(preds["history"][m] - sub.tgt_cs)) / 100.0, 4),
        })

    intervals = {}
    for name in ("pooled", "history"):
        pred, lo, hi = fp.predict_with_interval(test, name)
        cov = {"overall": coverage_summary(test, lo, hi)}
        for lab_name, labels in (("by_gap", gap_lab), ("by_age_band", age_lab), ("by_direction", dir_lab),
                                 ("by_event", ev_lab), ("by_history", has_hist), ("by_speed_band", speed_lab)):
            cov[lab_name] = grouped(test, labels, lambda sub, m: coverage_summary(sub, lo[m], hi[m]))
        intervals[name] = cov
    # Calibration-set coverage (in-sample for the quantiles) for contrast with the forward test.
    p, lo, hi = fp.predict_with_interval(calib, "history")
    intervals["history"]["calibration_in_sample"] = coverage_summary(calib, lo, hi)

    worked = worked_examples(fp)

    def part_summary(sub: Examples) -> dict:
        return {"rows": int(len(sub)), "swimmers": int(len(np.unique(sub.swimmer))),
                "with_target_course_history_pct": round(100.0 * float(np.mean(np.isfinite(sub.tb_cs))), 2),
                "age_known_pct": round(100.0 * float(np.mean(np.isfinite(sub.age))), 2),
                "by_direction": {DIRECTIONS[d]: int(np.sum(sub.dir == d)) for d in range(len(DIRECTIONS))},
                "by_gap": {lab: int(np.sum(np.array([gap_bucket_label(int(g)) for g in sub.gap]) == lab))
                           for lab in (f"{a}-{b}d" for a, b in GAP_BUCKETS)}}

    elite = train.subset((train.dir == DIRECTIONS.index("SCY->LCM")) & (train.ev == EVENTS.index("1500-FR"))
                         & (train.sex == SEXES.index("men")))
    elite_fast = int(np.sum(elite.src_cs < 93000))  # SCY 1650 under 15:30.00

    return {
        "checkpoint": "national-checkpoint-17",
        "evaluated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "loaded_swims_sha256": swims_sha,
        "privacy": (f"Aggregates only. Groups with < {MIN_REPORT_ROWS} rows or < {MIN_REPORT_SWIMMERS} "
                    "swimmers are suppressed; worked examples use synthetic inputs."),
        "design": {
            "task": "predict the target-course time of a later swim of the same event from an earlier source swim",
            "pairing": ("each target swim is paired, per other course, with the swimmer's most recent "
                        f"earlier swim of the same event, gap 1-{MAX_GAP_DAYS} days"),
            "features_dated_on_or_before_source_swim": True,
            "history_window_days": HISTORY_WINDOW_DAYS,
            "cutoff_target_date": CUTOFF.isoformat(),
            "calibration_targets": f"validation-partition swimmers, targets {CALIBRATION_START.isoformat()} to cutoff",
            "test_targets": "test-partition swimmers, targets on or after cutoff",
            "interval_level": INTERVAL_LEVEL,
            "ridge_selected": ridge,
            "ridge_validation_mae_s": ridge_scores,
        },
        "hygiene": hygiene,
        "examples": {
            "total": int(len(ex)),
            "train_disjoint": part_summary(train),
            "calibration": part_summary(calib),
            "test": part_summary(test),
            "train_non_disjoint_rows": int(np.sum(temporal_splits(ex, disjoint=False)["train"])),
            "elite_support_scy_1650_men_under_15_30_train_rows": elite_fast if elite_fast >= 20 else "<20",
        },
        "swimmer_disjoint_test": {
            "overall": overall,
            "bootstrap": boot,
            "by_gap": by(gap_lab),
            "by_age_band": by(age_lab),
            "by_direction": by(dir_lab),
            "by_event": by(ev_lab),
            "by_history_availability": by(has_hist),
            "by_target_month": by(month_lab),
            "by_speed_band": by(speed_lab),
        },
        "non_disjoint_test": {
            "note": "same test rows; training also includes test swimmers' own pre-cutoff examples",
            "overall": {k: point_metrics(v, test) for k, v in nd_preds.items()},
        },
        "gbm": {
            "trees_kept": len(gbm.trees),
            "max_trees": gbm.max_trees,
            "depth": gbm.depth,
            "passes_keep_rule": bool(
                boot["mae_difference_ci95_s"]["gbm - history"]["ci95"][1] < 0
                and boot["mae_difference_ci95_s"]["gbm - history"]["point"] < -0.05
            ),
            "rule": "keep only if the gbm - history MAE CI excludes 0 and the gain exceeds 0.05 s",
        },
        "intervals_80pct": intervals,
        "coefficients": {"pooled": fp.pooled.coefficients(), "history": fp.history.coefficients()},
        "worked_examples_synthetic": worked,
        "models": models,
    }


def worked_examples(fp: FittedPredictor) -> list[dict]:
    # Synthetic inputs: a March championship swim predicting a summer long-course meet.
    cases = [
        ("Fast distance swimmer (20, men), March SCY 1650 to a June LCM 1500, no LCM history", dict(
            direction="SCY->LCM", event="1500-FR", sex="men", source_cs=85300, age=20, gap_days=90,
            target_month=6)),
        ("Same swimmer with a synthetic LCM 1500 best of 15:05.00 from the previous July", dict(
            direction="SCY->LCM", event="1500-FR", sex="men", source_cs=85300, age=20, gap_days=90,
            target_month=6, target_best_cs=90500, target_best_days_before=240, source_prior_best_cs=85800)),
        ("12-year-old girl, March SCY 100 free to a July LCM 100 free, no LCM history", dict(
            direction="SCY->LCM", event="100-FR", sex="women", source_cs=6500, age=12, gap_days=120,
            target_month=7)),
        ("Same girl with a synthetic LCM 100 free best of 1:17.00 from the previous July", dict(
            direction="SCY->LCM", event="100-FR", sex="women", source_cs=6500, age=12, gap_days=120,
            target_month=7, target_best_cs=7700, target_best_days_before=240, source_prior_best_cs=6700)),
    ]
    out = []
    ncaa = ncaa_log_factor_table()
    for label, kw in cases:
        ex1 = synthetic_example(**kw)
        row = {"case": label, "inputs": {k: (format_cs(v) if k.endswith("_cs") and v else v) for k, v in kw.items()},
               "ncaa_conversion": format_cs(kw["source_cs"] * math.exp(ncaa[ex1.cell[0]]))}
        for model in ("pooled", "history"):
            p, lo, hi = fp.predict_with_interval(ex1, model)
            row[model] = {"likely": format_cs(p[0]), "range_80pct": [format_cs(lo[0]), format_cs(hi[0])]}
        out.append(row)
    return out


def survivorship_summary(duckdb_path: Path) -> dict:
    """Share of SCY swims (mid-2024 to mid-2025, so a full 365-day follow-up is observed) whose
    swimmer races the same event in LCM within 365 days, by speed quartile within event/sex/age."""
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        con.execute("LOAD iceberg")
        rows = con.execute("""
            WITH s AS (
              SELECT source, swimmer_id, stroke, distance, category, race_date, time_cs,
                     floor(age_years) AS age, course
              FROM races WHERE course IN ('SCY', 'LCM') AND category IN ('women', 'men')
            ), src AS (
              SELECT *, ntile(4) OVER (PARTITION BY stroke, distance, category, age ORDER BY time_cs) AS q
              FROM s WHERE course = 'SCY' AND race_date >= DATE '2024-07-01' AND race_date < DATE '2025-07-01'
                AND ((stroke = 'freestyle' AND distance IN (50, 100, 200, 500))
                     OR (stroke != 'freestyle' AND distance IN (100, 200)))
            ), followed AS (
              SELECT src.q, src.age,
                     EXISTS (SELECT 1 FROM s l WHERE l.course = 'LCM' AND l.source = src.source
                             AND l.swimmer_id = src.swimmer_id AND l.stroke = src.stroke
                             AND l.category = src.category
                             AND l.distance = CASE WHEN src.distance = 500 THEN 400 ELSE src.distance END
                             AND l.race_date > src.race_date
                             AND l.race_date <= src.race_date + INTERVAL 365 DAY) AS has_lcm
              FROM src
            )
            SELECT q, avg(has_lcm::INT) AS rate, count(*) AS n FROM followed GROUP BY q ORDER BY q
        """).fetchall()
    finally:
        con.close()
    return {
        "scope": "SCY 50/100/200/500 free and 100/200 stroke swims dated 2024-07-01..2025-06-30",
        "share_with_same_event_lcm_swim_within_365d_by_speed_quartile": {
            f"q{int(q)}{' (fastest)' if q == 1 else ' (slowest)' if q == 4 else ''}": {
                "rate": round(float(r), 4), "rows": int(n)} for q, r, n in rows
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--duckdb", type=Path, default=DEFAULT_DUCKDB)
    ap.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    ap.add_argument("--bootstrap-reps", type=int, default=500)
    args = ap.parse_args()
    receipt = run(args.duckdb, args.receipt, args.bootstrap_reps)
    print(json.dumps({"overall": receipt["swimmer_disjoint_test"]["overall"],
                      "intervals": receipt["intervals_80pct"]["history"]["overall"]}, indent=2))


if __name__ == "__main__":
    main()
