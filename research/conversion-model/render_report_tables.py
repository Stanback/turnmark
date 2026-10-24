"""Rebuild the numerical tables in REPORT.md from the committed receipts.

Each table sits between `<!-- receipt:NAME -->` and `<!-- /receipt:NAME -->` comments and is
rendered from evaluation-checkpoint-08.json, acquisition-checkpoint-06.json or the engine snapshot
data/empirical.json. Numbers are rounded half away from zero from the receipt's own decimal values,
so a table shows exactly what the receipt says at the displayed precision. `--check` exits non-zero
when any block differs from what the receipts produce, or when a block and a renderer do not match
one to one. Aggregates only: the receipts hold no swimmer-level records.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "REPORT.md"
EVALUATION = HERE / "evaluation-checkpoint-08.json"
ACQUISITION = HERE / "acquisition-checkpoint-06.json"
SNAPSHOT = HERE.parents[1] / "data" / "empirical.json"

BLOCK = re.compile(r"(<!-- receipt:([a-z0-9-]+) -->\n)(.*?)(<!-- /receipt:\2 -->)", re.DOTALL)
MINUS = "−"
CANDIDATE = "turnmark_equivalence"
METHODS = (
    ("colorado_2026", "Colorado Timing"),
    ("ncaa_2025_27", "NCAA"),
    ("flat_empirical_multiplier", "Flat multiplier per cell"),
    ("percentile_same_input", "Percentile, same input"),
    ("percentile_age_aware", "Percentile, age-aware"),
    (CANDIDATE, "Turnmark Equivalence"),
)
LABEL = dict(METHODS)
COURSE_PAIRS = (("SCY", "LCM"), ("SCY", "SCM"), ("SCM", "LCM"))
ABILITY_ORDER = ("ncaa_2025_27", "colorado_2026", "flat_empirical_multiplier", "percentile_same_input", "percentile_age_aware", CANDIDATE)
DIRECTIONS = ("SCY->LCM", "LCM->SCY", "SCY->SCM", "SCM->SCY", "SCM->LCM", "LCM->SCM")


# Formatting: the receipt stores rounded decimals; Decimal(repr(x)) keeps those digits exactly.


def fixed(x: float, digits: int) -> str:
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)
    return str(q).replace("-", MINUS)


def signed(x: float, digits: int) -> str:
    text = fixed(x, digits)
    return text if text.startswith(MINUS) or Decimal(text) == 0 else "+" + text


def count(n: int) -> str:
    return f"{n:,}"


def clock(cs: int) -> str:
    """Hundredths as a swim clock: 59.29, 1:02.95."""
    seconds = f"{(cs // 100) % 60:02d}.{cs % 100:02d}" if cs >= 6000 else f"{cs // 100}.{cs % 100:02d}"
    return f"{cs // 6000}:{seconds}" if cs >= 6000 else seconds


def thousands(x: float, digits: int) -> str:
    whole, _, frac = fixed(x, digits).partition(".")
    return f"{int(whole):,}" + (f".{frac}" if frac else "")


def pct_share(share: float, digits: int = 1) -> str:
    return fixed(100.0 * share, digits) + "%"


def code(text: str) -> str:
    return f"`{text}`"


def interval(entry: dict, digits: int = 2, unit: str = "%") -> str:
    """`−0.86%` (`[−1.27, −0.45]`) from an {estimate, ci95_low, ci95_high} entry."""
    lo, hi = signed(entry["ci95_low"], digits), signed(entry["ci95_high"], digits)
    return f"{code(signed(entry['estimate'], digits) + unit)} ({code(f'[{lo}, {hi}]')})"


def ci_only(entry: dict, digits: int = 4) -> str:
    return code(f"[{signed(entry['ci95_low'], digits)}, {signed(entry['ci95_high'], digits)}]")


def holm(p: float) -> str:
    if p < 0.001:
        return code("<0.001")
    if p >= 0.995:
        return code("1.0")
    return code(fixed(p, 3 if p < 0.01 else 2))


def table(header: list[str], align: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(align) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def bold_if(name: str, cells: list[str]) -> list[str]:
    return [f"**{c}**" if name == CANDIDATE and c else c for c in cells]


def label_row(name: str, label: str | None = None) -> str:
    text = label or LABEL[name]
    return f"**{text}**" if name == CANDIDATE else text


# Renderers. Each takes the three loaded documents and returns the block's markdown.


def corpus(ev: dict, acq: dict, snap: dict) -> str:
    union, hyg = acq["union_counts"], ev["hygiene_and_pairing"]
    sources = acq["frozen_sources"]
    rows = [
        ["Input race records", count(union["input_race_records"]), f"{count(sum(s['archives'] for s in sources))} meet archive files in {len(sources)} frozen export collections (Appendix A)"],
        ["Cross-archive identical duplicates", count(union["cross_archive_identical_duplicates"]), "Same race identity in overlapping archives; one copy kept"],
        ["Conflicting duplicates excluded", count(union["conflicting_races_excluded"]), "Same swimmer, meet, event and round with conflicting clock strings"],
        ["**Usable distinct individual finishes**", f"**{count(union['usable_distinct_races'])}**", "Official timed finals, prelims and finals only"],
        ["Source-scoped swimmers", count(acq["source_scoped_swimmers"]), "Keyed `HMAC-SHA256` pseudonymous IDs; not a verified person count"],
        ["Distinct meets", count(acq["meets"]), "Archive years 2010–2026"],
        ["Round-collapsed candidate swims", count(hyg["round_collapsed_candidate_swims"]), "Fastest plausible round per swimmer, meet, course, event and category"],
        ["Best-of-meet swims in the 14 events", count(hyg["best_of_meet_swims"]), f"After excluding {count(hyg['excluded_implausible_time'])} implausible times and {count(hyg['excluded_non_ncaa_event'])} swims outside the 14 convertible events"],
        ["30-day directional pairs", count(hyg["directional_pairs_30d"]), f"{count(hyg['clean_directional_pairs_30d'])} clean after the ratio screen; {count(hyg['unique_undirected_pairs_30d'])} undirected pairs from {count(hyg['swimmers_with_pairs_30d'])} swimmers"],
        ["Same-course repeat swims", count(hyg["same_course_repeat_swims_30d"]), f"Consecutive best-of-meet swims at different meets 1–30 days apart; the {count(ev['model_metadata']['repeat_swims_for_noise'])} from training swimmers estimate noise"],
    ]
    return table(["Stage", "Count", "Definition"], [":---", "---:", ":---"], rows)


def courses(ev: dict, acq: dict, snap: dict) -> str:
    races = acq["cohorts"]["course"]
    total = acq["union_counts"]["usable_distinct_races"]
    pairs = ev["hygiene_and_pairing"]["by_direction_30d"]
    rows = []
    for course in ("SCY", "LCM", "SCM"):
        partners = ", ".join(f"{d.replace('->', '→')} {count(pairs[d])}" for d in DIRECTIONS if d.startswith(course))
        rows.append([f"`{course}`", count(races[course]), fixed(100.0 * races[course] / total, 2) + "%", partners])
    cats = acq["cohorts"]["category"]
    for cat in ("women", "men"):
        rows.append([cat.capitalize(), count(cats[cat]), fixed(100.0 * cats[cat] / total, 2) + "%", ""])
    return table(["Course / category", "Usable races", "Share", "30-day directional pairs from this course"], [":---", "---:", "---:", ":---"], rows)


def partitions(ev: dict, acq: dict, snap: dict) -> str:
    rows = []
    for name in ("train", "validation", "test"):
        p = ev["partitions_30d"][name]
        rows.append([
            name.capitalize(),
            count(p["clean_directional_pairs"]),
            count(p["clean_underlying_pairs"]),
            count(p["clean_swimmers"]),
            f"{count(p['directional_pairs'])} rows, {count(p['swimmers'])} swimmers",
        ])
    return table(["Partition", "Clean directional rows", "Clean pairs", "Swimmers", "Untrimmed"], [":---", "---:", "---:", "---:", ":---"], rows)


def noise(ev: dict, acq: dict, snap: dict) -> str:
    var = ev["model_metadata"]["noise_variance_log_seconds"]
    events = sorted({k.split("|")[1] for k in var}, key=lambda e: list(ev["swimmer_disjoint_holdout"]["by_event"]).index(e))
    rows = []
    for e in events:
        scy, lcm, scm = (var[f"{c}|{e}"] for c in ("SCY", "LCM", "SCM"))
        # A course without enough repeat swimmers takes the mean of the measured courses.
        pooled = abs(scm - (scy + lcm) / 2.0) < 1e-7
        sd = lambda v: fixed(100.0 * math.sqrt(v), 2)  # noqa: E731
        rows.append([
            code(e), sd(scy), sd(lcm), sd(scm) + (" (pooled)" if pooled else ""),
            fixed(lcm / scy, 2), fixed(scm / scy, 2) + ("" if not pooled else " (pooled)"), fixed(scm / lcm, 2) + ("" if not pooled else " (pooled)"),
        ])
    return table(
        ["Event", "SCY σ (%)", "LCM σ (%)", "SCM σ (%)", "LCM/SCY", "SCM/SCY", "SCM/LCM"],
        [":---", "---:", "---:", "---:", "---:", "---:", "---:"],
        rows,
    )


def _knot_map(knots: list, x: float, inverse: bool) -> float:
    """The engine's map with slope 1 beyond the outer knots (same rule as evaluate_and_train.knot_map)."""
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


WORKED_CELL, WORKED_SOURCE, WORKED_TARGET = "100-BK|men", "SCM", "LCM"
WORKED_TIMES_CS = (5626, 5999, 6500, 8000, 14000)


def worked_example(ev: dict, acq: dict, snap: dict) -> str:
    cell = snap["cells"][WORKED_CELL]
    src, dst = cell[WORKED_SOURCE]["knots"], cell[WORKED_TARGET]["knots"]

    def scale(knots: list) -> float:
        (u0, v0), (u1, v1) = knots[0], knots[-1]
        return (v1 - v0) / (u1 - u0)

    s_a, s_b = scale(src), scale(dst)
    b = s_b / s_a
    # ln y = alpha + b ln x inside both supports; alpha from the source course's lower knot.
    u0, v0 = src[0]
    alpha = _knot_map(dst, u0, inverse=False) - b * v0
    rows = [
        [f"Scale $s_{{\\text{{{WORKED_SOURCE}}}}}$", code(fixed(s_a, 4))],
        [f"Scale $s_{{\\text{{{WORKED_TARGET}}}}}$", code(fixed(s_b, 4))],
        ["Exponent $b = s_B / s_A$ inside both supports", code(fixed(b, 4))],
        ["Constant $C = e^{\\alpha}$ inside both supports", code(fixed(math.exp(alpha), 4))],
        [f"{WORKED_SOURCE} support on the shared scale (SCY-equivalent s)", code(f"{fixed(math.exp(src[0][0]), 2)}–{fixed(math.exp(src[-1][0]), 2)}")],
        [f"{WORKED_TARGET} support on the shared scale (SCY-equivalent s)", code(f"{fixed(math.exp(dst[0][0]), 2)}–{fixed(math.exp(dst[-1][0]), 2)}")],
    ]
    differ = sum(
        cells[a]["knots"][0][0] != cells[b]["knots"][0][0] or cells[a]["knots"][-1][0] != cells[b]["knots"][-1][0]
        for cells in snap["cells"].values()
        for a, b in COURSE_PAIRS
    )
    rows.append(["Course-pair cells whose two course supports differ (all events)", code(f"{differ} of {len(snap['cells']) * len(COURSE_PAIRS)}")])
    out = table(["Men's 100 back, SCM→LCM", "Value"], [":---", "---:"], rows)
    conv_rows = []
    for t in WORKED_TIMES_CS:
        ln_x = math.log(t / 100.0)
        u = _knot_map(src, ln_x, inverse=True)
        y = math.floor(math.exp(_knot_map(dst, u, inverse=False)) * 100.0 + 1e-8)  # engine truncate()
        a_in = src[0][0] <= u <= src[-1][0]
        b_in = dst[0][0] <= u <= dst[-1][0]
        local = (s_b if b_in else 1.0) / (s_a if a_in else 1.0)
        regime = {(True, True): "both inside", (False, True): f"{WORKED_SOURCE} beyond its edge", (True, False): f"{WORKED_TARGET} beyond its edge", (False, False): "both beyond"}[(a_in, b_in)]
        conv_rows.append([
            code(clock(t)),
            code(clock(y)),
            code(fixed(y / t, 4)),
            regime,
            code(fixed(local, 4)),
            "`empirical-out-of-range`" if not (a_in and b_in) else "",
        ])
    out += "\n" + table(
        ["Entered SCM", "Converted LCM", "Ratio", "Regime", "Local exponent $b$", "Range caveat"],
        ["---:", "---:", "---:", ":---", "---:", ":---"],
        conv_rows,
    )
    return out


def snapshot_arithmetic(ev: dict, acq: dict, snap: dict) -> str:
    a = ev["snapshot_arithmetic"]
    n = a["roundtrip_conversions_checked"]
    rt, tr = a["roundtrip_error_hundredths_distribution"], a["transitivity_difference_hundredths_distribution"]
    rows = [
        ["Conversions checked per property", code(count(n)), "Every hundredth across each cell's plausible range, all six directions"],
        ["Largest unrounded round-trip error (log s)", code(f"{a['unrounded_roundtrip_max_abs_log_error']:.1e}"), "Exact inverse up to floating point"],
        ["Monotonicity violations", code(count(a["monotonicity_violations"])), ""],
        ["Round trip after truncation: exact", code(pct_share(a["roundtrip_exact_share"])), ""],
    ]
    for k in sorted(rt, key=int):
        rows.append([f"Round trip after truncation: {fixed(int(k) / 100, 2)}s fast", code(pct_share(rt[k] / n)), code(count(rt[k]))])
    for k in sorted(tr, key=int):
        what = "exact" if k == "0" else f"off by {fixed(int(k) / 100, 2)}s"
        rows.append([f"Via third course vs direct: {what}", code(pct_share(tr[k] / n)), code(count(tr[k]))])
    return table(["Property (exported snapshot)", "Result", "Count / note"], [":---", "---:", ":---"], rows)


def roundtrip(ev: dict, acq: dict, snap: dict) -> str:
    r = ev["swimmer_disjoint_holdout"]["roundtrip_and_transitivity_on_test_swims"]
    rows = []
    for name, _ in METHODS:
        c, t = r[name]["roundtrip_closure"], r[name]["transitivity_via_third_course"]
        cells = [
            code(fixed(c["mean_abs_seconds"], 3) + "s") + " / " + code(fixed(c["max_abs_seconds"], 2) + "s"),
            code(fixed(t["mean_abs_seconds"], 3) + "s") + " / " + code(fixed(t["max_abs_seconds"], 2) + "s"),
        ]
        rows.append([label_row(name)] + bold_if(name, cells))
    n = r[CANDIDATE]["roundtrip_closure"]["evaluated"]
    return table([f"Method ({count(n)} test conversions)", "Round trip mean / max", "Via third course mean / max"], [":---", "---:", "---:"], rows)


def accuracy(ev: dict, acq: dict, snap: dict) -> str:
    h = ev["swimmer_disjoint_holdout"]
    rows = []
    for name, _ in METHODS:
        m, u = h["clean_test"][name], h["untrimmed_test"][name]
        cells = [
            code(fixed(m["mae_seconds"], 4)), code(fixed(m["median_ae_seconds"], 2)), code(fixed(m["rmse_seconds"], 4)),
            code(fixed(m["p90_ae_seconds"], 2)), code(signed(m["signed_bias_seconds"], 4)), code(fixed(m["mape_percent"], 2) + "%"),
            code(fixed(m["within_1_0_pct"], 2) + "%"), code(fixed(m["swimmer_equalized_mae_seconds"], 4)), code(fixed(u["mae_seconds"], 4)),
        ]
        rows.append([label_row(name)] + bold_if(name, cells))
    return table(
        ["Method", "MAE (s)", "Median AE (s)", "RMSE (s)", "P90 AE (s)", "Signed bias (s)", "MAPE", "Within ±1%", "Swimmer-eq MAE (s)", "Untrimmed MAE (s)"],
        [":---"] + ["---:"] * 9,
        rows,
    )


def _comparisons(family: dict) -> list[tuple[str, dict]]:
    return [(name, family[f"comparisons_vs_{name}"][CANDIDATE]) for name, _ in METHODS if name != CANDIDATE]


def mae_differences(ev: dict, acq: dict, snap: dict) -> str:
    fam = ev["swimmer_disjoint_holdout"]["bootstrap_mae"]["swimmer_clustered"]["overall_clean_test"]
    order = ("ncaa_2025_27", "colorado_2026", "flat_empirical_multiplier", "percentile_same_input", "percentile_age_aware")
    comps = dict(_comparisons(fam))
    rows = []
    for name in order:
        c = comps[name]
        verdict = "" if c["significant_after_holm_0_05"] else " (not established)"
        rows.append([LABEL[name].replace(" per cell", "").replace(" Timing", ""), code(signed(c["estimate"], 4) + "s"), ci_only(c), holm(c["holm_p_value"]) + verdict])
    return table(["Turnmark Equivalence minus…", "Estimate", "95% CI", "Holm $p$"], [":---", "---:", ":---", "---:"], rows)


def mae_differences_by_direction(ev: dict, acq: dict, snap: dict) -> str:
    fams = ev["swimmer_disjoint_holdout"]["bootstrap_mae"]["swimmer_clustered"]
    refs = ("ncaa_2025_27", "flat_empirical_multiplier", "percentile_same_input", "percentile_age_aware")
    rows = []
    for d in DIRECTIONS:
        f = fams[f"dir_{d.replace('->', '_to_')}"]
        cells = []
        for ref in refs:
            c = f[f"comparisons_vs_{ref}"][CANDIDATE]
            cells.append(f"{code(signed(c['estimate'], 3))} {ci_only(c, 3)}, $p$ {holm(c['holm_p_value'])}")
        rows.append([code(d), f"{count(f['evaluated_pairs'])} / {count(f['clusters'])}"] + cells)
    return table(
        ["Direction", "Rows / swimmers", "vs NCAA", "vs flat", "vs percentile (same)", "vs percentile (age)"],
        [":---", "---:", ":---", ":---", ":---", ":---"],
        rows,
    )


def ability(ev: dict, acq: dict, snap: dict) -> str:
    h = ev["swimmer_disjoint_holdout"]
    less = h["ability_bias_by_independent_swim_decile"]["swimmer_clustered"]
    coupled = h["ability_bias_by_pair_mean_decile"]["swimmer_clustered"]
    rows = []
    for name in ABILITY_ORDER:
        cells = []
        for diag in (less[name], coupled[name]):
            cells += [interval(diag["tail_spread_forward_D1_minus_D10"]), code(signed(diag["forward_D2_5_minus_D7_9"]["estimate"], 2) + "%"), code(fixed(diag["forward_shape_wald_chi2_9"], 1))]
        rows.append([label_row(name).replace(" per cell", "").replace(" Timing", "")] + bold_if(name, cells))
    return table(
        ["Method", "Less coupled D1−D10 (95% CI)", "D2–5 minus D7–9", "Shape $\\chi^2_9$", "Coupled D1−D10 (95% CI)", "D2–5 minus D7–9", "Shape $\\chi^2_9$"],
        [":---", ":---", "---:", "---:", ":---", "---:", "---:"],
        rows,
    )


def deciles(ev: dict, acq: dict, snap: dict) -> str:
    h = ev["swimmer_disjoint_holdout"]
    less = h["ability_bias_by_independent_swim_decile"]["swimmer_clustered"]
    coupled = h["ability_bias_by_pair_mean_decile"]["swimmer_clustered"]
    names = ("ncaa_2025_27", "percentile_same_input", CANDIDATE)
    rows = []
    for d in range(1, 11):
        cells = [code(signed(src[n]["forward"][f"D{d}"]["estimate"], 2)) for src in (less, coupled) for n in names]
        rows.append([f"D{d}" + (" (fastest)" if d == 1 else " (slowest)" if d == 10 else "")] + cells)
    head = [f"{diag}: {LABEL[n].replace('Turnmark Equivalence', 'Equivalence')}" for diag in ("Less coupled", "Coupled") for n in names]
    return table(["Decile"] + head, [":---"] + ["---:"] * 6, rows)


def ability_sensitivity(ev: dict, acq: dict, snap: dict) -> str:
    h = ev["swimmer_disjoint_holdout"]
    cov = h["ability_bias_by_independent_swim_decile"]["coverage"]
    meet = h["ability_bias_by_pair_mean_decile"]["meet_clustered"][CANDIDATE]
    rows = [
        ["Test rows", code(count(cov["rows"]))],
        ["Rows with a separate swim", code(count(cov["rows_with_independent_swim"]))],
        ["Rows in less-coupled deciles", f"{code(count(cov['rows_in_deciles']))} ({code(pct_share(cov['rows_in_deciles'] / cov['rows'], 0))})"],
        ["Separate-swim gap from both pair swims", code(f"{cov['min_days']}–{cov['max_days']} days")],
        ["Coupled diagnostic, meet-clustered: Equivalence D1−D10", interval(meet["tail_spread_forward_D1_minus_D10"])],
        ["Coupled diagnostic, meet-clustered: Equivalence shape $\\chi^2_9$", code(fixed(meet["forward_shape_wald_chi2_9"], 1))],
    ]
    return table(["Coverage and sensitivity", "Value"], [":---", "---:"], rows)


def validation(ev: dict, acq: dict, snap: dict) -> str:
    v = ev["model_metadata"]["validation_curvature"]
    less, coupled = v["ability_bias_by_independent_swim_decile"], v["ability_bias_by_pair_mean_decile"]
    rows = []
    for name in ("ncaa_2025_27", "flat_empirical_multiplier", CANDIDATE):
        cells = [code(fixed(v["mae_seconds"][name], 4) + "s")]
        for diag in (less[name], coupled[name]):
            cells += [interval(diag["tail_spread_forward_D1_minus_D10"]), interval(diag["forward_D2_5_minus_D7_9"])]
        rows.append([label_row(name).replace(" per cell", "")] + bold_if(name, cells))
    n = ev["partitions_30d"]["validation"]["clean_directional_pairs"]
    return table(
        [f"Validation ({count(n)} rows)", "MAE", "Less-coupled D1−D10", "Less-coupled D2–5 minus D7–9", "Coupled D1−D10", "Coupled D2–5 minus D7–9"],
        [":---", "---:", ":---", ":---", ":---", ":---"],
        rows,
    ) + f"\nLess-coupled coverage on validation: {code(count(less['coverage']['rows_in_deciles']))} of {code(count(less['coverage']['rows']))} rows.\n"


def percentile_preservation(ev: dict, acq: dict, snap: dict) -> str:
    p = ev["swimmer_disjoint_holdout"]["percentile_preservation"]
    order = ("ncaa_2025_27", "colorado_2026", "flat_empirical_multiplier", "percentile_same_input", "percentile_age_aware", CANDIDATE)
    head = ["NCAA", "Colorado", "Flat", "Percentile (same input)", "Percentile (age-aware)", "**Equivalence**"]
    row = [f"**{code(fixed(p[n]['mean_abs_shift_points'], 2))}**" if n == CANDIDATE else code(fixed(p[n]["mean_abs_shift_points"], 2)) for n in order]
    return table(head, ["---:"] * 6, [row]) + f"\nEvaluated rows: {code(count(p[CANDIDATE]['evaluated']))}.\n"


def by_direction(ev: dict, acq: dict, snap: dict) -> str:
    r = ev["swimmer_disjoint_holdout"]["by_direction"]
    rows = []
    for d in DIRECTIONS:
        m = r[d]
        rows.append([
            code(d), code(count(m[CANDIDATE]["evaluated_pairs"])),
            f"{code(fixed(m['ncaa_2025_27']['mae_seconds'], 4))} ({code(signed(m['ncaa_2025_27']['signed_bias_seconds'], 3))})",
            code(fixed(m["flat_empirical_multiplier"]["mae_seconds"], 4)),
            f"{code(fixed(m['percentile_same_input']['mae_seconds'], 4))} / {code(fixed(m['percentile_age_aware']['mae_seconds'], 4))}",
            f"**{code(fixed(m[CANDIDATE]['mae_seconds'], 4))}** ({code(signed(m[CANDIDATE]['signed_bias_seconds'], 3))})",
        ])
    return table(["Direction", "Rows", "NCAA (bias)", "Flat", "Percentile (same / age)", "**Equivalence** (bias)"], [":---"] + ["---:"] * 5, rows)


def by_event(ev: dict, acq: dict, snap: dict) -> str:
    r = ev["swimmer_disjoint_holdout"]["by_event"]
    rows = []
    for key, e in r.items():
        m = e["models"]
        rows.append([
            f"{code(key)} {e['display_label']}", f"{count(e['evaluated_pairs'])} / {count(e['evaluated_swimmers'])}",
            code(fixed(m["ncaa_2025_27"]["mae_seconds"], 4)), code(fixed(m["colorado_2026"]["mae_seconds"], 4)),
            code(fixed(m["flat_empirical_multiplier"]["mae_seconds"], 4)),
            f"{code(fixed(m['percentile_same_input']['mae_seconds'], 4))} / {code(fixed(m['percentile_age_aware']['mae_seconds'], 4))}",
            f"**{code(fixed(m[CANDIDATE]['mae_seconds'], 4))}**",
        ])
    return table(["Event", "Rows / swimmers", "NCAA", "Colorado", "Flat", "Percentile (same / age)", "**Equivalence**"], [":---"] + ["---:"] * 6, rows)


def by_age(ev: dict, acq: dict, snap: dict) -> str:
    r = ev["swimmer_disjoint_holdout"]["by_age_band"]
    rows = []
    for band, m in r.items():
        rows.append([
            code(band), code(count(m[CANDIDATE]["pairs"])), code(fixed(m["ncaa_2025_27"]["mae_seconds"], 4)),
            code(fixed(m["flat_empirical_multiplier"]["mae_seconds"], 4)),
            f"{code(fixed(m['percentile_same_input']['mae_seconds'], 4))} / {code(fixed(m['percentile_age_aware']['mae_seconds'], 4))}",
            f"**{code(fixed(m[CANDIDATE]['mae_seconds'], 4))}** ({code(signed(m[CANDIDATE]['signed_bias_seconds'], 3))})",
        ])
    return table(["Age band", "Rows", "NCAA", "Flat", "Percentile (same / age)", "**Equivalence** (bias)"], [":---"] + ["---:"] * 5, rows)


HOLDOUTS = (("temporal_2026_holdout", "Later season (2026)"), ("leave_regions_out_holdout", "Regions held out"))


def holdouts(ev: dict, acq: dict, snap: dict) -> str:
    rows = []
    for key, label in HOLDOUTS:
        h = ev[key]
        m = h["clean_test"]
        rows.append([
            label, f"{count(h['training_set']['clean_directional_pairs'])} / {count(h['training_set']['clean_swimmers'])}",
            f"{count(h['test_set']['clean_directional_pairs'])} / {count(h['test_set']['clean_swimmers'])}",
            *[code(fixed(m[n]["mae_seconds"], 4)) for n in ("ncaa_2025_27", "flat_empirical_multiplier", "percentile_same_input", "percentile_age_aware")],
            f"**{code(fixed(m[CANDIDATE]['mae_seconds'], 4))}**",
        ])
    return table(
        ["Holdout", "Train rows / swimmers", "Test rows / swimmers", "NCAA", "Flat", "Percentile (same)", "Percentile (age)", "**Equivalence**"],
        [":---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"],
        rows,
    )


def holdout_diagnostics(ev: dict, acq: dict, snap: dict) -> str:
    rows = []
    for key, label in HOLDOUTS:
        h = ev[key]
        coupled = h["ability_bias_by_pair_mean_decile"]["swimmer_clustered"]
        less = h["ability_bias_by_independent_swim_decile"]
        for name in (CANDIDATE, "percentile_same_input", "percentile_age_aware"):
            c = coupled[name]
            dec = [c["forward"][f"D{d}"]["estimate"] for d in range(1, 8)]
            rows.append([
                label, label_row(name),
                code(signed(c["forward"]["D10"]["estimate"], 2) + "%"),
                interval(c["tail_spread_forward_D1_minus_D10"]),
                code(f"{signed(min(dec), 2)} to {signed(max(dec), 2)}%"),
                interval(less["swimmer_clustered"][name]["tail_spread_forward_D1_minus_D10"]) + f"; {code(count(less['coverage']['rows_in_deciles']))} rows",
            ])
    return table(
        ["Holdout", "Method", "Coupled D10", "Coupled D1−D10", "Coupled D1–D7 range", "Less-coupled D1−D10"],
        [":---", ":---", "---:", ":---", ":---", ":---"],
        rows,
    )


def window(ev: dict, acq: dict, snap: dict) -> str:
    w = ev["window_sensitivity_test"]
    rows = []
    for k, m in w.items():
        rows.append([
            code(k) + (" (main)" if int(k[:-1]) == ev["matching_window_days"] else ""),
            f"{count(m['evaluated_pairs'])} / {count(m['evaluated_swimmers'])}",
            *[code(fixed(m[f"{n}_mae_s"], 4)) for n in ("ncaa_2025_27", "colorado_2026", "flat_empirical_multiplier", "percentile_same_input", "percentile_age_aware")],
            f"**{code(fixed(m[f'{CANDIDATE}_mae_s'], 4))}**",
        ])
    return table(
        ["Pairing window", "Test rows / swimmers", "NCAA", "Colorado", "Flat", "Percentile (same)", "Percentile (age)", "**Equivalence**"],
        [":---"] + ["---:"] * 7,
        rows,
    )


def caveats(ev: dict, acq: dict, snap: dict) -> str:
    shares = ev["swimmer_disjoint_holdout"]["caveat_shares_on_test"]
    meta = ev["model_metadata"]
    support = meta["cell_support"]
    precise = snap["preciseLatentRanges"]
    rows = [
        ["Test conversions with no caveat", code(pct_share(shares["none"]))],
        ["Test conversions `empirical-low-evidence`", code(pct_share(shares["empirical-low-evidence"]))],
        ["Test conversions `empirical-out-of-range`", code(pct_share(shares["empirical-out-of-range"]))],
        ["Course-pair cells under 100 effective swimmers", code(f"{support['cells_low_evidence']} of {meta['course_pair_cells']}")],
        ["Directional keys in `lowEvidenceCells`", code(count(meta["low_evidence_directional_cells"]))],
        ["Directional keys with no precise range", code(f"{sum(v is None for v in precise.values())} of {len(precise)}")],
        ["Bootstrap refits behind `preciseLatentRanges` / width limit", code(f"{meta['precision_bootstrap']['bootstrap_refits']} / {fixed(meta['precision_bootstrap']['limit_pct'], 0)}%")],
    ]
    return table(["Caveat evidence", "Value"], [":---", "---:"], rows)


def venue_cohorts(ev: dict, acq: dict, snap: dict) -> str:
    r = ev["swimmer_disjoint_holdout"]["by_venue_cohort"]
    rows = []
    for k, c in r.items():
        m = c["models"]
        rows.append([
            code(k), f"{count(c['evaluated_pairs'])} / {count(c['evaluated_swimmers'])}",
            code(fixed(m["ncaa_2025_27"]["mae_seconds"], 4)), code(fixed(m["flat_empirical_multiplier"]["mae_seconds"], 4)),
            code(fixed(m["percentile_same_input"]["mae_seconds"], 4)), f"**{code(fixed(m[CANDIDATE]['mae_seconds'], 4))}**",
        ])
    return table(["Cohort", "Rows / swimmers", "NCAA", "Flat", "Percentile (same)", "**Equivalence**"], [":---"] + ["---:"] * 5, rows)


def fast_swimmer(ev: dict, acq: dict, snap: dict) -> str:
    f = ev["swimmer_disjoint_holdout"]["fast_swimmer_example"]
    rows = []
    for key, c in f["converted"].items():
        name, _, qual = key.partition(" ")
        label = label_row(name) + (f" {qual}" if qual else "")
        caveat = f" ({code(f['turnmark_equivalence_caveat'])})" if name == CANDIDATE else ""
        rows.append([label] + bold_if(name, [code(c["time"]) + caveat, code(c["converted_back"])]))
    return table([f"{f['input']} → {f['target']}", "Converted", "Converted back"], [":---", "---:", "---:"], rows)


def archives(ev: dict, acq: dict, snap: dict) -> str:
    races = acq["cohorts"]["region"]
    pairs = ev["hygiene_and_pairing"]["by_region_30d"]
    total = acq["union_counts"]["usable_distinct_races"]
    rows = [
        [name, count(n), fixed(100.0 * n / total, 2) + "%", count(pairs[name]) if name in pairs else "—"]
        for name, n in sorted(races.items(), key=lambda kv: -kv[1])
    ]
    return table(["Archive authority", "Usable races", "Share", "30-day directional pairs"], [":---", "---:", "---:", "---:"], rows)


def collections(ev: dict, acq: dict, snap: dict) -> str:
    rows = [[code(s["source"]), count(s["archives"]), count(s["rows"])] for s in acq["frozen_sources"]]
    rows.append(["**Total**", f"**{count(sum(s['archives'] for s in acq['frozen_sources']))}**", f"**{count(sum(s['rows'] for s in acq['frozen_sources']))}**"])
    return table(["Frozen export collection", "Archive files", "Input race records"], [":---", "---:", "---:"], rows)


def venue_join(ev: dict, acq: dict, snap: dict) -> str:
    v = ev["meet_locality_matches"]
    rows = [
        ["Unique meets with SDIF `B1` headers", count(v["unique_meets"])],
        ["Matched by 5-digit postal code", count(v["matched_by_postal_code"])],
        ["Matched by `(city, state)`", count(v["matched_by_city_state"])],
        ["**Matched to a facility record**", f"**{count(v['matched_facility'])}** ({fixed(100.0 * v['matched_facility'] / v['unique_meets'], 1)}%)"],
        ["With locality coordinates", count(v["with_locality_coordinates"])],
        ["Unmatched", count(v["unmatched"])],
    ]
    return table(["Meet-to-venue locality join", "Meets"], [":---", "---:"], rows)


def lakehouse(ev: dict, acq: dict, snap: dict) -> str:
    s = acq["lakehouse_storage"]
    n = acq["union_counts"]["usable_distinct_races"]
    rows = [
        ["Iceberg snapshot", code(str(s["iceberg_snapshot_id"]))],
        ["Hot SQLite store", f"{thousands(s['hot_sqlite_bytes'] / 1e6, 1)} MB ({fixed(s['hot_sqlite_bytes'] / n, 1)} bytes/row)"],
        ["Parquet warehouse", f"{fixed(s['parquet_bytes'] / 1e6, 1)} MB ({fixed(s['parquet_bytes'] / n, 1)} bytes/row)"],
        ["Point lookup by swimmer, first / repeat median", f"{fixed(s['point_lookup_first_ms'], 3)} ms / {fixed(s['point_lookup_repeat_median_ms'], 3)} ms"],
        ["Filtered DuckDB aggregate, first / repeat median", f"{fixed(s['duckdb_scan_first_ms'], 2)} ms / {fixed(s['duckdb_scan_repeat_median_ms'], 2)} ms"],
    ]
    return table([f"Lakehouse (`{s['checkpoint_dir']}`)", "Measured"], [":---", "---:"], rows)


RENDERERS = {
    "corpus": corpus,
    "courses": courses,
    "partitions": partitions,
    "noise": noise,
    "worked-example": worked_example,
    "snapshot-arithmetic": snapshot_arithmetic,
    "roundtrip": roundtrip,
    "accuracy": accuracy,
    "mae-differences": mae_differences,
    "mae-differences-by-direction": mae_differences_by_direction,
    "ability": ability,
    "deciles": deciles,
    "ability-coverage": ability_sensitivity,
    "validation": validation,
    "percentile-preservation": percentile_preservation,
    "by-direction": by_direction,
    "by-event": by_event,
    "by-age": by_age,
    "holdouts": holdouts,
    "holdout-diagnostics": holdout_diagnostics,
    "window": window,
    "caveats": caveats,
    "venue-cohorts": venue_cohorts,
    "fast-swimmer": fast_swimmer,
    "archives": archives,
    "collections": collections,
    "venue-join": venue_join,
    "lakehouse": lakehouse,
}


def load_documents() -> tuple[dict, dict, dict]:
    return tuple(json.loads(p.read_text(encoding="utf-8")) for p in (EVALUATION, ACQUISITION, SNAPSHOT))


def render(text: str, docs: tuple[dict, dict, dict]) -> str:
    """Replace every receipt block with its rendering. Refuses a block without a renderer, a
    renderer without a block, and a name used twice, so no table silently stops being checked."""
    names = [m.group(2) for m in BLOCK.finditer(text)]
    unknown = sorted(set(names) - set(RENDERERS))
    missing = sorted(set(RENDERERS) - set(names))
    repeated = sorted({n for n in names if names.count(n) > 1})
    if unknown or missing or repeated:
        raise ValueError(f"receipt blocks: unknown {unknown}, missing {missing}, repeated {repeated}")
    return BLOCK.sub(lambda m: m.group(1) + RENDERERS[m.group(2)](*docs) + m.group(4), text)


def stale_blocks(text: str, rendered: str) -> list[str]:
    before = {m.group(2): m.group(3) for m in BLOCK.finditer(text)}
    after = {m.group(2): m.group(3) for m in BLOCK.finditer(rendered)}
    return [name for name in before if before[name] != after[name]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if REPORT.md differs from the receipts")
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    text = args.report.read_text(encoding="utf-8")
    rendered = render(text, load_documents())
    if args.check:
        stale = stale_blocks(text, rendered)
        if stale:
            print(f"{args.report.name} is out of date with the receipts: {', '.join(stale)}", file=sys.stderr)
            print(f"Run: python {Path(__file__).name}", file=sys.stderr)
            return 1
        print(f"{args.report.name}: {len(RENDERERS)} receipt blocks up to date")
        return 0
    if rendered != text:
        args.report.write_text(rendered, encoding="utf-8")
        print(f"Rewrote {', '.join(stale_blocks(text, rendered))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
