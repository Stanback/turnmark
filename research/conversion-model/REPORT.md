# Equivalent Swimming Times Across Courses: 8.51 Million Races and a Shared-Scale Map

**Status:** Shipped in `turnmark-core` as Turnmark Equivalence (`turnmark-empirical-2026`) alongside `ncaa-2025-27` (default) and `colorado-teamunify-2026`  
**Evaluation Receipt:** [`evaluation-checkpoint-08.json`](./evaluation-checkpoint-08.json) · **Acquisition Receipt:** [`acquisition-checkpoint-06.json`](./acquisition-checkpoint-06.json)  
**Embedded Snapshot:** [`data/empirical.json`](../../data/empirical.json) (schema 3, `14,057` bytes) · **Engine parity fixture:** [`fixtures/empirical-parity.json`](../../fixtures/empirical-parity.json) (`1,008` cases) · **Companion Essay:** [`bristanback.com/posts/what-eight-million-swims-say-about-the-wall`](https://bristanback.com/posts/what-eight-million-swims-say-about-the-wall/)  
**Tables:** every table between `<!-- receipt:… -->` markers is generated from the receipts and the snapshot by [`render_report_tables.py`](./render_report_tables.py); `--check` fails when the report and the receipts disagree.

---

## 1. Summary

Published course-conversion systems reduce the change between a 25-yard pool (`SCY`), a 25-meter pool (`SCM`) and a 50-meter pool (`LCM`) to one static formula per event:

1. **NCAA sample conversion tables (`ncaa-2025-27`; Rules Book Appendix C, printed pages 119–120)** apply a constant multiplier $y = \operatorname{truncate}_{0.01}(x \cdot f_{d,e,g})$.
2. **Colorado Timing / TeamUnify (`colorado-teamunify-2026`)** applies an affine rule $y = \operatorname{truncate}_{0.01}(x \cdot m_{d,e} + b_{d,e})$ with a fixed per-50 stroke offset.

**What Turnmark Equivalence estimates.** The equivalent performance in the other course: the time that sits at the same underlying performance level, not "what will this swimmer swim next" (a forecasting question with a different target, covered by a separate predictor research track). Both swims in a same-swimmer pair are treated as noisy readings of one level. Each `(event, category, course)` gets a map that is linear in log time onto one shared scale, and every conversion composes two of those maps. Inside both courses' training support this gives $y = C x^{b}$, a power law whose ratio $y/x$ changes with the entered time unless $b = 1$ (§5.8).

The report separates three kinds of claim, and each section says which kind it makes:

- **(a) Guarantees by construction (§6).** The map is strictly monotone; converting back is the exact inverse and converting through a third course equals converting directly, before rounding; truncation to hundredths is the only rounding, so a round trip never comes back slower than the entered time.
- **(b) Observed evaluation results (§7).** On `39,314` clean held-out directional conversions from `4,710` test swimmers (swimmer-disjoint from training and validation), pair MAE is `2.7711s` against `3.0414s` for NCAA (difference `−0.2703s`, 95% CI `[−0.3018, −0.2400]`) and `2.8582s` for a fitted flat multiplier per cell (`−0.0871s`, `[−0.1041, −0.0696]`). **This measured improvement over constant-ratio rules is the main evidence for the model.** Percentile maps built on the same scale are about as accurate (`−0.0171s`, Holm $p = 0.22$; `−0.0153s`, Holm $p = 1.0$): the map does not beat percentile matching after Holm correction, and in `LCM→SCY` the age-aware percentile map is more accurate (§7.3). What the parametric map adds over percentile matching is pooling across thin `SCM` cells (it is more accurate from `SCM` to `LCM`, §7.3), a compact snapshot, and stability under hundredth truncation. Both compose through the shared scale and invert exactly before rounding; the percentile maps' steep segments amplify the hundredth that truncation drops between conversions (§6).
- **(c) Assumptions the data cannot establish (§8).** The noise ratio taken from same-course repeats ignores swimmer-specific course aptitude; the less-coupled ability diagnostic assumes its separate swim is independent of the pair's errors; pairs 30 days apart are assumed to reflect one level; and the 0.5–99.5% training support is used as the range of trust.

Both ability diagnostics (§7.5) show a single factor converting the fastest and slowest swimmers in opposite directions by a combined `2–3%`, and this map removing most of that. Neither establishes that the map is free of ability-dependent error: the less-coupled diagnostic still shows a trend and a mid-range bend, and progression, a mis-measured noise ratio and selection into the diagnostic could each produce that pattern.

Where it is weaker, all from the receipt:

- On the two harder holdouts (§7.8) the slow tail converts too fast: coupled decile 10 is `−1.36%` (later season) and `−0.82%` (regions held out). The percentile maps show the same pattern, so it is not specific to this map's form. A single-input converter cannot separate improvement between the two swims from the course change.
- In the 1650/1500 free, NCAA (`28.3018s`) and the flat multiplier (`28.1145s`) beat the map (`28.7135s`) on `66` held-out rows from `27` swimmers.
- Outside the fitted range the conversion extrapolates. A `14:13.00` men's 1650 yd converts to `14:46.57` LCM with the `empirical-out-of-range` caveat; NCAA gives `14:43.93`. That number is extrapolation (§7.10).
- "Equivalent" is not "what you'd swim": grouped by the entered time instead of by ability, conversions of the fastest entries run fast and of the slowest run slow. That follows from the target (§2.2).

Observations from checks run outside the pipeline are collected in §9 and labelled exploratory; no conclusion above rests on them.

---

## 2. Target: Equivalent Performance, Not a Forecast

### 2.1 The Estimand

For a swimmer at performance level $\ell$ in an event and category, each course $c$ has a typical log time $g_c(\ell)$. Turnmark Equivalence estimates, for an entered time $x$ in course $A$, the time $y$ in course $B$ at the same level: $\ln y = g_B(g_A^{-1}(\ln x))$. The shared scale is anchored on SCY: $g_{\text{SCY}}$ is the identity, so a scale value is "the SCY log time of the same level".

This is a property of the population of swimmers who race both courses. It is not a statement about what a given swimmer will do in the other course next week; that depends on their own aptitude, progression and form, which a single entered time does not carry.

### 2.2 Why Ordinary Predictive Regression Answers a Different Question

Fitting $\ln y$ on $\ln x$ by least squares estimates $E[\ln y \mid \ln x]$, the best forecast of the target time given the entered one. Because one swim is a noisy reading of a swimmer's level, that conditional mean is pulled toward the population mean: with $\ln x = \ell + e_A$, the least-squares slope is the structural slope times the reliability $\operatorname{Var}\ell / (\operatorname{Var}\ell + \operatorname{Var} e_A) < 1$. Fast entries are forecast slow and slow entries fast. The reverse fit $E[\ln x \mid \ln y]$ is attenuated the same way, so the two fitted slopes multiply to $r^2 < 1$ and A→B→A does not return A. That is the right answer for forecasting and the wrong one for equivalence.

Deming regression is also regression, of a different kind: an errors-in-variables fit that targets the structural relation between the two courses' levels instead of a conditional mean. It recovers that relation only when the ratio of the two courses' noise variances, $\delta$, is known (A2 in §3). A synthetic test with a known conversion and unequal course noise (`test_linear_map_recovers_a_known_equivalence_under_unequal_course_noise`) checks that the fit recovers it under the model's own assumptions; it does not cover swimmer-specific course aptitude, which the repeat swims cannot measure (§8.1).

---

## 3. Assumptions

| | Assumption | Used for | Kind |
| :--- | :--- | :--- | :--- |
| **A1** | Within an `(event, category)`, each course's log time is a linear function of one shared level plus noise, over the range the data covers. | The map's form (§5.6) | Checked in part: accuracy and the diagnostics (§7) |
| **A2** | Each course's per-swim noise variance equals the variance seen in same-course repeat swims 1–30 days apart, so $\delta$ is their ratio. | Every Deming slope (§5.4) | (c) Not establishable (§8.1) |
| **A3** | A swimmer's two swims in a pair, at most 30 days apart, reflect one level. | Pairing (§5.2) | (c) Not establishable (§8.3) |
| **A4** | Swimmers are independent clusters; within a swimmer, pairs are correlated arbitrarily. | Weights, variances, bootstrap (§5.4, §7.1) | Partial: §7.11 lists what it misses |
| **A5** | The separate swim used by the less-coupled diagnostic is independent of the pair's measurement errors. | Interpreting §7.5 | (c) Not establishable (§8.2) |
| **A6** | The swimmer-weighted 0.5th–99.5th percentile of each course's training pairs bounds where the fitted slope can be trusted; beyond it the edge ratio is held. | Support, extrapolation, `empirical-out-of-range` (§5.7) | (c) A convention (§8.4) |

---

## 4. Notation

| Symbol | Meaning | In the code |
| :--- | :--- | :--- |
| $A, B$ | Source and target course (`SCY`, `SCM`, `LCM`) | `source_course`, `target_course` |
| $x, y$ | Entered time in $A$, converted time in $B$ (seconds) | `time_cs / 100` |
| $\ell$ | Shared-scale value (SCY log seconds of the same level) | `latent` |
| $a$ | Anchor: the SCY log-time centre of the cell's SCY–LCM pairs (else SCY–SCM) | `anchor` in `_reconcile` |
| $m_c, s_c$ | Location and scale of course $c$: its log time at $\ell = a$, and $d \ln t / d\ell$. SCY is $(a, 1)$ | `(location, scale)` returned by `_reconcile` |
| $g_c$ | Course map, $\ell \mapsto \ln t$; $g_c(\ell) = m_c + s_c(\ell - a)$ inside support | `from_latent`; `knot_map(..., inverse=False)` |
| $[u_c^-, u_c^+]$ | Course $c$'s training support on the shared scale | the two knots in `data/empirical.json` |
| $b$, $C$ | Exponent and constant of the conversion, $y = C x^b$ | derived (§5.8) |
| $\sigma_c^2$ | Per-swim log-time noise variance of course $c$ in an event | `noise_variance_log_seconds` |
| $\delta$ | Noise ratio $\sigma_B^2 / \sigma_A^2$ for a line from $A$ to $B$ | `delta` in `EquivalenceModel.fit` |
| $n_{\text{sw}}$ | Effective number of swimmers (Kish) | `effective_swimmers` |
| D1–D10 | Ability deciles within course pair, event and category; D1 fastest | `pair_mean_deciles`, `independent_swim_deciles` |

Errors in §7 are signed percentages $100 \ln(\hat y / y)$: positive means the conversion is slower than the swim it is scored against.

---

## 5. Data, Model and Fitting Procedure

### 5.1 Corpus (`national-checkpoint-17`)

Race records come from publicly linked USA Swimming Local Swimming Committee (LSC) and YMCA National Championship Standard Data Interchange Format (`.sd3`, `.cl2`, `.hy3`) meet exports, held in a gitignored local store. As documented in [`COLLECTION_PLAN.md`](./COLLECTION_PLAN.md) and the acquisition receipt, the 18 archive authorities in 16 frozen export collections reflect public bulk Hy-Tek archive availability (`nationally_representative: false`), not a balanced national probability sample. Archive-by-archive counts are in Appendix A; the local storage the evaluator reads (Iceberg snapshot `4441271835344284414`, input SHA-256 `eb5325f86f28...`) is in Appendix C.

<!-- receipt:corpus -->
| Stage | Count | Definition |
| :--- | ---: | :--- |
| Input race records | 8,520,841 | 6,521 meet archive files in 16 frozen export collections (Appendix A) |
| Cross-archive identical duplicates | 10,550 | Same race identity in overlapping archives; one copy kept |
| Conflicting duplicates excluded | 3,524 | Same swimmer, meet, event and round with conflicting clock strings |
| **Usable distinct individual finishes** | **8,506,767** | Official timed finals, prelims and finals only |
| Source-scoped swimmers | 292,474 | Keyed `HMAC-SHA256` pseudonymous IDs; not a verified person count |
| Distinct meets | 6,071 | Archive years 2010–2026 |
| Round-collapsed candidate swims | 5,902,346 | Fastest plausible round per swimmer, meet, course, event and category |
| Best-of-meet swims in the 14 events | 5,901,538 | After excluding 492 implausible times and 316 swims outside the 14 convertible events |
| 30-day directional pairs | 271,048 | 269,824 clean after the ratio screen; 135,524 undirected pairs from 32,121 swimmers |
| Same-course repeat swims | 1,149,135 | Consecutive best-of-meet swims at different meets 1–30 days apart; the 803,195 from training swimmers estimate noise |
<!-- /receipt:corpus -->

SCM is thin: under 1% of races, and about 10% of the 30-day directional pairs involve it.

<!-- receipt:courses -->
| Course / category | Usable races | Share | 30-day directional pairs from this course |
| :--- | ---: | ---: | :--- |
| `SCY` | 5,734,165 | 67.41% | SCY→LCM 121,114, SCY→SCM 6,534 |
| `LCM` | 2,706,429 | 31.82% | LCM→SCY 121,114, LCM→SCM 7,264 |
| `SCM` | 66,173 | 0.78% | SCM→SCY 6,534, SCM→LCM 7,264 |
| Women | 4,639,864 | 54.54% |  |
| Men | 3,866,903 | 45.46% |  |
<!-- /receipt:courses -->

### 5.2 Pairing and Hygiene

1. **Plausibility screen and best-of-meet reduction (`deduplicate_best_of_meet`).** Swims in the 14 convertible events (`canonical_event_key`, which rejects SCY 400 free and 800/1500 yd free) are screened against physical floors and ceilings and collapsed to the fastest valid finish per meet, so prelim/final doubles do not overweight multi-round swimmers.
2. **Directional pairing (`build_directional_pairs`).** Within each swimmer and event, best-of-meet swims in different courses within $|\Delta t| \le 30$ days are matched greedily one-to-one by nearest date. Each matched pair is evaluated in both directions.
3. **Ratio screen (`is_pair_ratio_outlier`).** A pair is flagged when its target time differs by more than 18% from a fixed geometry reference (distance in meters, turn count and a surface factor), or when a same-distance LCM swim beats its SCY partner. The screen is decided once per matched pair and applies to both directions (`1,224` flagged rows, `0.45%`). All methods are scored on both the clean and the untrimmed test set.
4. **Swimmer-disjoint 70/15/15 split (`swimmer_partition`).** Swimmers are partitioned by `SHA-256` of `json.dumps([source, swimmer_id])`. In the main evaluation only Train fits anything, Validation is used only for the curvature question in §7.6, and Test only for §7; the holdouts in §7.8 define their own swimmer-disjoint splits.

<!-- receipt:partitions -->
| Partition | Clean directional rows | Clean pairs | Swimmers | Untrimmed |
| :--- | ---: | ---: | ---: | :--- |
| Train | 189,046 | 94,523 | 22,425 | 189,896 rows, 22,512 swimmers |
| Validation | 41,464 | 20,732 | 4,859 | 41,658 rows, 4,881 swimmers |
| Test | 39,314 | 19,657 | 4,710 | 39,494 rows, 4,728 swimmers |
<!-- /receipt:partitions -->

### 5.3 Noise Variances from Same-Course Repeats (`estimate_course_noise`)

For each `(course, event)`, $\sigma_c^2$ is half the swimmer-weighted variance of $\ln(t_2 / t_1)$ over consecutive best-of-meet swims by the same swimmer in the same course at different meets 1–30 days apart, after the same 18% screen. Each swimmer's repeats in a cell carry equal total weight. A course is measured on its own where at least 200 swimmers have repeats; otherwise it takes the mean of the measured courses for that event. In the main evaluation only training swimmers' repeats are used.

The table shows the per-swim noise as a standard deviation in percent, $100\,\sigma_c$, and the ratios that become $\delta$. SCM is measured on its own only for the 50 free; elsewhere it is pooled, so its ratios carry no SCM-specific information. What these numbers can and cannot see is in §8.1.

<!-- receipt:noise -->
| Event | SCY σ (%) | LCM σ (%) | SCM σ (%) | LCM/SCY | SCM/SCY | SCM/LCM |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `50-FR` | 2.78 | 2.47 | 3.48 | 0.79 | 1.57 | 1.99 |
| `100-FR` | 2.50 | 2.32 | 2.41 (pooled) | 0.86 | 0.93 (pooled) | 1.08 (pooled) |
| `200-FR` | 2.07 | 2.00 | 2.04 (pooled) | 0.94 | 0.97 (pooled) | 1.03 (pooled) |
| `400-FR` | 1.79 | 1.84 | 1.81 (pooled) | 1.05 | 1.03 (pooled) | 0.98 (pooled) |
| `800-FR` | 1.62 | 1.81 | 1.72 (pooled) | 1.25 | 1.13 (pooled) | 0.90 (pooled) |
| `1500-FR` | 1.62 | 1.69 | 1.65 (pooled) | 1.08 | 1.04 (pooled) | 0.96 (pooled) |
| `100-BK` | 2.39 | 2.42 | 2.40 (pooled) | 1.03 | 1.01 (pooled) | 0.99 (pooled) |
| `200-BK` | 1.98 | 1.95 | 1.96 (pooled) | 0.97 | 0.99 (pooled) | 1.01 (pooled) |
| `100-BR` | 2.23 | 2.22 | 2.22 (pooled) | 0.99 | 1.00 (pooled) | 1.00 (pooled) |
| `200-BR` | 1.99 | 1.97 | 1.98 (pooled) | 0.98 | 0.99 (pooled) | 1.01 (pooled) |
| `100-FL` | 2.50 | 2.54 | 2.52 (pooled) | 1.03 | 1.02 (pooled) | 0.98 (pooled) |
| `200-FL` | 2.27 | 2.29 | 2.28 (pooled) | 1.02 | 1.01 (pooled) | 0.99 (pooled) |
| `200-IM` | 1.93 | 1.92 | 1.93 (pooled) | 0.99 | 0.99 (pooled) | 1.01 (pooled) |
| `400-IM` | 1.67 | 1.66 | 1.67 (pooled) | 0.99 | 1.00 (pooled) | 1.00 (pooled) |
<!-- /receipt:noise -->

### 5.4 Deming Lines per Course Pair (`fit_pair_line`)

For each canonical course pair (`SCY→LCM`, `SCY→SCM`, `SCM→LCM`), event and category, and for each course pair and event with categories pooled, a Deming line is fitted through the clean training pairs in log seconds, $(\ln x_i, \ln y_i)$, with weight $w_i = 1/k_i$ where $k_i$ is the number of pairs swimmer $i$ contributes to that cell, so each swimmer carries equal total weight. With weighted moments $s_{xx}, s_{yy}, s_{xy}$ and $\delta = \sigma_B^2/\sigma_A^2$ from §5.3,
$$\hat\beta = \frac{s_{yy} - \delta s_{xx} + \sqrt{(s_{yy} - \delta s_{xx})^2 + 4\delta s_{xy}^2}}{2 s_{xy}},$$
and the line passes through the weighted centre $(\bar x, \bar y)$, giving a shift $\bar y - \bar x$ at that centre.

Each line's sampling variances count swimmers, not rows. The shift variance is a swimmer-clustered sandwich estimate with a small-sample factor $m/(m-1)$ over $m$ swimmers. The slope variance is the approximation $(1 - r^2) / n_{\text{sw}}$ on the log slope, with $n_{\text{sw}} = (\sum_i W_i)^2 / \sum_i W_i^2$ over swimmer totals $W_i$ (Kish's formula, which equals the swimmer count under equal weighting). **It is not a cluster variance, and it runs high when swimmers contribute several pairs**; it feeds the shrinkage weights in §5.5 and the reconciliation weights in §5.6. Repeating a swimmer's rows leaves the line, its variances, the shrinkage, the support, the noise estimate and the flat baseline unchanged (`test_repeated_rows_add_no_evidence_influence_or_confidence`).

### 5.5 Empirical-Bayes Shrinkage (`shrink_toward`)

Two levels, for shift and log slope separately, per course pair:

1. Event lines (categories pooled) shrink toward pool geometry for the shift and toward slope 1 (a flat multiplier) for the log slope.
2. Category cells shrink toward their event line's posterior.

Each posterior weights its own estimate by $(\text{prior var} + \tau^2)/(\text{prior var} + \tau^2 + \text{sampling var})$, with the between-cell variance $\tau^2$ a moment estimate around the priors (`between_cell_variance` in the receipt). A cell with no line takes its prior. Thin cells therefore lean on their event, and thin events on geometry and slope 1.

### 5.6 Reconciliation into Per-Course Maps (`_reconcile`)

The three course-pair posteriors for an `(event, category)` overdetermine two course maps, and reconciliation makes them consistent. Under A1 the structural slope from course $A$ to course $B$ is $s_B / s_A$, so with $s_{\text{SCY}} = 1$:
$$\ln s_L = \beta_{\text{SL}}, \qquad \ln s_M = \beta_{\text{SM}}, \qquad \ln s_L - \ln s_M = \beta_{\text{ML}},$$
where $\beta$ are the shrunk log slopes. Weighted least squares with weights $1/\text{var}$ solves for $(\ln s_L, \ln s_M)$. The locations $(m_L, m_M)$ are solved the same way from the three shrunk shifts, each line passing through its own pair centre, with the SCY anchor $a$ at the SCY centre of the SCY–LCM pairs (else of the SCY–SCM pairs). `_reconcile` returns `{"SCY": (a, 1), "SCM": (m_M, s_M), "LCM": (m_L, s_L)}`, and from then on all six directions use these same per-course parameters.

### 5.7 Support, Knots and the Conversion Rule (`_course_tables`, `knot_map`, `engine_equivalence`)

Course $c$'s map onto the shared scale and back is
$$\ell = a + \frac{\ln t - m_c}{s_c}, \qquad \ln t = m_c + s_c(\ell - a).$$
Its training support $[u_c^-, u_c^+]$ is the swimmer-weighted 0.5th and 99.5th percentile of the pair-mean scale value $\tfrac12(\ell_A + \ell_B)$ over every training pair the course appears in (that category only). The snapshot stores each course map as two knots, $(u_c^\pm, g_c(u_c^\pm))$, rounded to six decimals. Beyond the outer knots the map continues with slope 1 in $(\ell, \ln t)$: the course's ratio to the shared scale is held at its edge instead of extrapolating $s_c$.

A conversion from $A$ to $B$ is
$$\ell = g_A^{-1}(\ln x), \qquad y = \operatorname{truncate}_{0.01}\!\big(\exp g_B(\ell)\big),$$
flagged `empirical-out-of-range` when $\ell$ lies outside either course's support. Truncation is the only rounding. The Python `engine_equivalence` and Rust `empirical_equivalent` implement the same rule and are checked against each other on the parity fixture (§10).

### 5.8 The Conversion in Closed Form

**Inside both supports.** Substitute the source map into the target map:
$$\ln y = m_B + s_B\left(\frac{\ln x - m_A}{s_A}\right) = \underbrace{\left(m_B - \frac{s_B}{s_A} m_A\right)}_{\alpha} + \underbrace{\frac{s_B}{s_A}}_{b}\,\ln x,$$
so before truncation
$$y = C x^{b}, \qquad C = e^{\alpha}, \qquad b = \frac{s_B}{s_A}, \qquad \frac{y}{x} = C x^{b - 1}.$$
When $b = 1$ this is an ordinary multiplier, the form NCAA uses. Estimating $b$ lets the ratio vary with the entered time: with $b < 1$ slower entries convert with a smaller ratio, with $b > 1$ a larger one. From SCY, $s_A = 1$ and $b = s_B$. The parameters compose: $b_{BA} = 1/b_{AB}$ and $b_{AC} = b_{AB}\, b_{BC}$, which is why §6's properties hold.

**Beyond a support edge.** Each course map has slope 1 beyond its edges, so the local exponent $d \ln y / d \ln x$ depends on which maps are inside their supports at $\ell$:

| Source map at $\ell$ | Target map at $\ell$ | Local exponent | Ratio $y/x$ |
| :--- | :--- | :---: | :--- |
| inside | inside | $s_B / s_A$ | varies unless $s_A = s_B$ |
| beyond its edge | inside | $s_B$ | varies unless $s_B = 1$ |
| inside | beyond its edge | $1 / s_A$ | varies unless $s_A = 1$ |
| beyond its edge | beyond its edge | $1$ | constant |

The combined ratio is constant when both maps are beyond their edges, and, because the SCY map has slope 1 throughout, a conversion to or from SCY is constant once the other course's map is beyond its edge. The `empirical-out-of-range` flag can come on before either: in men's 200 breast SCY→SCM the SCY support ends at `230.26s` while the SCM map stays inside to about `277s`, and flagged conversions there still change ratio (`1.108` at `231.26s`, `1.102` at `260.00s`). Because the two courses' supports differ in most cells, there is usually a band where only one map is beyond its edge and the ratio keeps changing. Men's 100 back SCM→LCM, from the shipped snapshot:

<!-- receipt:worked-example -->
| Men's 100 back, SCM→LCM | Value |
| :--- | ---: |
| Scale $s_{\text{SCM}}$ | `0.9743` |
| Scale $s_{\text{LCM}}$ | `0.9331` |
| Exponent $b = s_B / s_A$ inside both supports | `0.9577` |
| Constant $C = e^{\alpha}$ inside both supports | `1.2474` |
| SCM support on the shared scale (SCY-equivalent s) | `54.12–141.92` |
| LCM support on the shared scale (SCY-equivalent s) | `48.63–132.32` |
| Course-pair cells whose two course supports differ (all events) | `80 of 84` |

| Entered SCM | Converted LCM | Ratio | Regime | Local exponent $b$ | Range caveat |
| ---: | ---: | ---: | :--- | ---: | :--- |
| `56.26` | `59.29` | `1.0539` | SCM beyond its edge | `0.9331` | `empirical-out-of-range` |
| `59.99` | `1:02.95` | `1.0493` | SCM beyond its edge | `0.9331` | `empirical-out-of-range` |
| `1:05.00` | `1:07.94` | `1.0452` | both inside | `0.9577` |  |
| `1:20.00` | `1:22.89` | `1.0361` | both inside | `0.9577` |  |
| `2:20.00` | `2:21.66` | `1.0119` | both inside | `0.9577` |  |
<!-- /receipt:worked-example -->

The first two entries are below the SCM support, so the SCM map is held at its edge and the local exponent is $s_{\text{LCM}}$, not 1: both are flagged, and their ratios still differ.

### 5.9 Evidence Caveats

Two engine-owned caveats mark conversions the data supports weakly:

- **`empirical-out-of-range`**: $\ell$ lies outside either course's training support (§5.7). Takes precedence.
- **`empirical-low-evidence`**: the course-pair cell has fewer than `100` effective swimmers, **or** $\ell$ falls outside the range where the swimmer-bootstrap 95% interval of the conversion is within 1% (`preciseLatentRanges`, from 200 refits on 41 points across the joint support). A directional key with no such range carries the caveat for every entered time.

The threshold of 100 effective swimmers and the 1% width limit are judgment calls, not fitted values.

<!-- receipt:caveats -->
| Caveat evidence | Value |
| :--- | ---: |
| Test conversions with no caveat | `95.0%` |
| Test conversions `empirical-low-evidence` | `3.6%` |
| Test conversions `empirical-out-of-range` | `1.4%` |
| Course-pair cells under 100 effective swimmers | `30 of 84` |
| Directional keys in `lowEvidenceCells` | `60` |
| Directional keys with no precise range | `36 of 168` |
| Bootstrap refits behind `preciseLatentRanges` / width limit | `200 / 1%` |
<!-- /receipt:caveats -->

### 5.10 Baselines

- **`ncaa_2025_27`** and **`colorado_2026`**: the published rules, exactly as the engine computes them.
- **`flat_empirical_multiplier`**: one fitted ratio per `(direction, event, category)` (the swimmer-weighted median of geometry-normalized ratios, shrunk toward event, stroke and geometry), the fair "single factor" comparison. Each direction is fitted separately, so it neither inverts nor composes exactly.
- **`percentile_same_input`** and **`percentile_age_aware`** (`AnchoredPercentileModel`): quantile maps $F_B^{-1}(F_A(x))$ built on the same SCY-anchored scale from the SCY–LCM and SCY–SCM populations, so they compose through SCY. The age-aware version adds an age-band table where one exists.

---

## 6. Guarantees by Construction (a)

These follow from the form in §5.7–5.8, not from the data. The checks below confirm the implementation, not the claims' truth for swimmers.

1. **Monotone.** Every piece of every course map has positive slope ($s_c = \exp(\cdot) > 0$ inside, 1 beyond), so each conversion is strictly increasing before truncation and non-decreasing after it.
2. **Exact inverse before rounding.** $B \to A$ applies $g_A \circ g_B^{-1}$ to $g_B \circ g_A^{-1}$, which is the identity.
3. **Three-course composition before rounding.** $A \to M \to B$ is $g_B \circ g_M^{-1} \circ g_M \circ g_A^{-1} = g_B \circ g_A^{-1}$, the direct conversion.
4. **Truncation.** The only rounding is the final truncation to hundredths. Since both legs of a round trip round down and the maps increase, a round trip never returns a time slower than the one entered.
5. **Evidence accounting.** Duplicating a swimmer's rows changes no fitted quantity (§5.4), and a synthetic population with known conversion and unequal noise is recovered under A1–A3 (§2.2).

How large the truncation residue is, and how often composition survives it, is observed rather than guaranteed. On the exported snapshot:

<!-- receipt:snapshot-arithmetic -->
| Property (exported snapshot) | Result | Count / note |
| :--- | ---: | :--- |
| Conversions checked per property | `10,119,368` | Every hundredth across each cell's plausible range, all six directions |
| Largest unrounded round-trip error (log s) | `1.8e-15` | Exact inverse up to floating point |
| Monotonicity violations | `0` |  |
| Round trip after truncation: exact | `0.0%` |  |
| Round trip after truncation: 0.01s fast | `96.9%` | `9,807,415` |
| Round trip after truncation: 0.02s fast | `3.1%` | `311,953` |
| Via third course vs direct: exact | `50.0%` | `5,059,684` |
| Via third course vs direct: off by 0.01s | `49.8%` | `5,043,885` |
| Via third course vs direct: off by 0.02s | `0.2%` | `15,799` |
<!-- /receipt:snapshot-arithmetic -->

The same properties on the held-out test swims, for comparison with baselines that lack them by construction:

<!-- receipt:roundtrip -->
| Method (39,314 test conversions) | Round trip mean / max | Via third course mean / max |
| :--- | ---: | ---: |
| Colorado Timing | `0.010s` / `0.02s` | `3.859s` / `202.43s` |
| NCAA | `0.011s` / `0.02s` | `0.005s` / `0.02s` |
| Flat multiplier per cell | `0.011s` / `0.83s` | `0.922s` / `16.84s` |
| Percentile, same input | `0.012s` / `2.79s` | `0.015s` / `3.43s` |
| Percentile, age-aware | `0.016s` / `2.61s` | `0.020s` / `4.20s` |
| **Turnmark Equivalence** | **`0.011s` / `0.02s`** | **`0.005s` / `0.02s`** |
<!-- /receipt:roundtrip -->

NCAA composes because it is one multiplier per course against a common reference. The flat multiplier fits each direction separately, so it neither inverts nor composes exactly. The percentile maps also compose through the shared scale and invert exactly before rounding, but their piecewise-linear quantile maps have steep segments that amplify the hundredth truncation drops between conversions, which is where their worst-case round trips of `2.79s` and `2.61s` come from. This map's slopes stay near 1, so the same truncation moves a round trip by at most `0.02s`. (An exploratory refit of the same-input percentile map with 101 to 1,001 quantile knots, run outside the pipeline, left the worst round trip between `1.22s` and `2.95s`: finer tables do not remove it.)

---

## 7. Evaluation Results (b)

### 7.1 Protocol

All results are on the swimmer-disjoint test partition unless stated otherwise. Errors are scored against the swimmer's actual time in the target course, which is itself a noisy reading of their level, so no method can reach zero error and differences between methods are what carry information. Comparisons resample whole swimmers ($B = 2{,}000$). For each comparison, p-values are Holm-adjusted across all 26 reported families (overall, five event groups and all SCM directions, six directions, 14 events). Intervals that cross zero mean the sample cannot distinguish the methods; they do not show equivalence. §7.11 lists what the intervals do not cover.

### 7.2 Overall Accuracy

<!-- receipt:accuracy -->
| Method | MAE (s) | Median AE (s) | RMSE (s) | P90 AE (s) | Signed bias (s) | MAPE | Within ±1% | Swimmer-eq MAE (s) | Untrimmed MAE (s) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Colorado Timing | `3.6528` | `2.23` | `6.5657` | `8.23` | `−0.0789` | `3.36%` | `19.89%` | `3.3821` | `3.7345` |
| NCAA | `3.0414` | `1.82` | `5.0297` | `7.03` | `−0.0032` | `2.93%` | `24.02%` | `2.9186` | `3.1251` |
| Flat multiplier per cell | `2.8582` | `1.70` | `4.7648` | `6.61` | `−0.0002` | `2.76%` | `25.92%` | `2.7418` | `2.9428` |
| Percentile, same input | `2.7882` | `1.67` | `4.7293` | `6.38` | `−0.0003` | `2.68%` | `25.94%` | `2.6893` | `2.8747` |
| Percentile, age-aware | `2.7864` | `1.66` | `4.7565` | `6.38` | `+0.0111` | `2.67%` | `26.26%` | `2.7068` | `2.8724` |
| **Turnmark Equivalence** | **`2.7711`** | **`1.66`** | **`4.6412`** | **`6.35`** | **`−0.0057`** | **`2.68%`** | **`26.09%`** | **`2.6759`** | **`2.8553`** |
<!-- /receipt:accuracy -->

<!-- receipt:mae-differences -->
| Turnmark Equivalence minus… | Estimate | 95% CI | Holm $p$ |
| :--- | ---: | :--- | ---: |
| NCAA | `−0.2703s` | `[−0.3018, −0.2400]` | `<0.001` |
| Colorado | `−0.8817s` | `[−0.9545, −0.8129]` | `<0.001` |
| Flat multiplier | `−0.0871s` | `[−0.1041, −0.0696]` | `<0.001` |
| Percentile, same input | `−0.0171s` | `[−0.0299, −0.0043]` | `0.22` (not established) |
| Percentile, age-aware | `−0.0153s` | `[−0.0364, +0.0054]` | `1.0` (not established) |
<!-- /receipt:mae-differences -->

The improvement over NCAA and over a fitted single factor per cell holds on the swimmer-equalized MAE and the untrimmed set as well. Against the two percentile maps the differences are small and not established after Holm correction.

### 7.3 By Direction

MAE with signed bias in parentheses (seconds):

<!-- receipt:by-direction -->
| Direction | Rows | NCAA (bias) | Flat | Percentile (same / age) | **Equivalence** (bias) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `SCY->LCM` | `17,693` | `3.2147` (`−0.427`) | `3.0209` | `2.8694` / `2.8907` | **`2.8525`** (`−0.065`) |
| `LCM->SCY` | `17,693` | `2.8794` (`+0.420`) | `2.6916` | `2.6609` / `2.6031` | **`2.6632`** (`+0.054`) |
| `SCY->SCM` | `934` | `3.2452` (`−0.426`) | `3.2410` | `3.3036` / `3.4469` | **`3.2245`** (`−0.050`) |
| `SCM->SCY` | `934` | `2.9552` (`+0.399`) | `2.9422` | `3.0022` / `3.1431` | **`3.0008`** (`+0.040`) |
| `SCM->LCM` | `1,030` | `2.9416` (`+0.985`) | `2.7110` | `2.8781` / `3.0670` | **`2.6951`** (`+0.040`) |
| `LCM->SCM` | `1,030` | `2.8388` (`−0.951`) | `2.6458` | `2.8264` / `2.9409` | **`2.6814`** (`−0.051`) |
<!-- /receipt:by-direction -->

Difference in MAE (Turnmark Equivalence minus each baseline, seconds) with swimmer-bootstrap 95% CI and Holm $p$:

<!-- receipt:mae-differences-by-direction -->
| Direction | Rows / swimmers | vs NCAA | vs flat | vs percentile (same) | vs percentile (age) |
| :--- | ---: | :--- | :--- | :--- | :--- |
| `SCY->LCM` | 17,693 / 4,260 | `−0.362` `[−0.398, −0.327]`, $p$ `<0.001` | `−0.168` `[−0.189, −0.147]`, $p$ `<0.001` | `−0.017` `[−0.031, −0.003]`, $p$ `0.39` | `−0.038` `[−0.061, −0.015]`, $p$ `0.03` |
| `LCM->SCY` | 17,693 / 4,260 | `−0.216` `[−0.251, −0.183]`, $p$ `<0.001` | `−0.028` `[−0.046, −0.010]`, $p$ `0.03` | `+0.002` `[−0.012, +0.017]`, $p$ `1.0` | `+0.060` `[+0.038, +0.082]`, $p$ `<0.001` |
| `SCY->SCM` | 934 / 374 | `−0.021` `[−0.091, +0.054]`, $p$ `1.0` | `−0.017` `[−0.064, +0.028]`, $p$ `1.0` | `−0.079` `[−0.197, +0.041]`, $p$ `1.0` | `−0.223` `[−0.372, −0.069]`, $p$ `0.07` |
| `SCM->SCY` | 934 / 374 | `+0.046` `[−0.023, +0.121]`, $p$ `0.91` | `+0.059` `[+0.016, +0.099]`, $p$ `0.08` | `−0.001` `[−0.093, +0.096]`, $p$ `1.0` | `−0.142` `[−0.263, −0.020]`, $p$ `0.34` |
| `SCM->LCM` | 1,030 / 358 | `−0.247` `[−0.352, −0.155]`, $p$ `<0.001` | `−0.016` `[−0.060, +0.027]`, $p$ `1.0` | `−0.183` `[−0.295, −0.086]`, $p$ `0.02` | `−0.372` `[−0.513, −0.240]`, $p$ `<0.001` |
| `LCM->SCM` | 1,030 / 358 | `−0.157` `[−0.260, −0.068]`, $p$ `0.01` | `+0.036` `[−0.009, +0.079]`, $p$ `1.0` | `−0.145` `[−0.257, −0.044]`, $p$ `0.17` | `−0.260` `[−0.395, −0.124]`, $p$ `0.005` |
<!-- /receipt:mae-differences-by-direction -->

Against NCAA the gain in `SCY↔LCM` comes mostly from its ability trend (§7.5), and in `SCM↔LCM` also from a level bias (signed `+0.985s` SCM→LCM, `−0.951s` LCM→SCM). `SCY↔SCM` is not distinguishable from NCAA at this sample size. In `LCM→SCY` the age-aware percentile map is more accurate than this map (`+0.060s`, Holm $p < 0.001$); in `SCM→LCM` and `LCM→SCM` this map is more accurate than both percentile maps in most comparisons.

### 7.4 By Event and Age Band

<!-- receipt:by-event -->
| Event | Rows / swimmers | NCAA | Colorado | Flat | Percentile (same / age) | **Equivalence** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `50-FR` 50 Free (50Y / 50M) | 8,010 / 2,747 | `1.1531` | `1.0634` | `1.0739` | `1.0585` / `1.0631` | **`1.0610`** |
| `100-FR` 100 Free (100Y / 100M) | 6,960 / 2,458 | `2.2402` | `2.2661` | `2.2046` | `2.1705` / `2.1848` | **`2.1688`** |
| `200-FR` 200 Free (200Y / 200M) | 3,550 / 1,301 | `4.1775` | `4.5272` | `4.0858` | `3.8988` / `3.8737` | **`3.8868`** |
| `400-FR` 500Y / 400M Free | 1,536 / 570 | `7.8880` | `11.4907` | `7.0265` | `6.9056` / `6.8724` | **`6.8825`** |
| `800-FR` 1000Y / 800M Free | 182 / 77 | `16.6937` | `22.0641` | `15.5107` | `15.6623` / `15.8625` | **`15.4964`** |
| `1500-FR` 1650Y / 1500M Free | 66 / 27 | `28.3018` | `37.9067` | `28.1145` | `29.6126` / `30.1742` | **`28.7135`** |
| `100-BK` 100 Back (100Y / 100M) | 4,394 / 1,600 | `2.7760` | `3.3334` | `2.5318` | `2.3637` / `2.3381` | **`2.3520`** |
| `200-BK` 200 Back (200Y / 200M) | 1,168 / 459 | `3.8082` | `6.3298` | `3.7945` | `3.6949` / `3.7304` | **`3.6674`** |
| `100-BR` 100 Breast (100Y / 100M) | 4,216 / 1,494 | `2.6870` | `3.2143` | `2.5874` | `2.4599` / `2.4397` | **`2.4348`** |
| `200-BR` 200 Breast (200Y / 200M) | 1,274 / 488 | `4.9693` | `6.1187` | `4.0156` | `4.0536` / `4.0479` | **`3.9931`** |
| `100-FL` 100 Fly (100Y / 100M) | 3,446 / 1,196 | `2.3784` | `2.7628` | `2.1731` | `2.1800` / `2.1761` | **`2.1674`** |
| `200-FL` 200 Fly (200Y / 200M) | 714 / 273 | `4.5192` | `5.5385` | `3.9370` | `4.0160` / `4.0255` | **`3.9471`** |
| `200-IM` 200 IM (200Y / 200M) | 3,190 / 1,161 | `4.1028` | `5.1983` | `4.0594` | `3.9214` / `3.8823` | **`3.9020`** |
| `400-IM` 400 IM (400Y / 400M) | 608 / 245 | `6.6968` | `9.2641` | `5.9428` | `6.0045` / `6.2575` | **`5.8527`** |
<!-- /receipt:by-event -->

The 1650/1500 free is the one event where NCAA and the flat multiplier beat the map, on very few rows.

<!-- receipt:by-age -->
| Age band | Rows | NCAA | Flat | Percentile (same / age) | **Equivalence** (bias) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `10u` | `6,407` | `3.5482` | `3.4432` | `3.2281` / `3.2223` | **`3.2103`** (`+0.003`) |
| `11-12` | `7,780` | `2.8548` | `2.7075` | `2.6422` / `2.6454` | **`2.6188`** (`+0.007`) |
| `13-14` | `10,494` | `2.9879` | `2.8084` | `2.8462` / `2.8401` | **`2.8073`** (`−0.009`) |
| `15-16` | `9,808` | `2.9577` | `2.7157` | `2.6393` / `2.6243` | **`2.6500`** (`−0.007`) |
| `17-18` | `4,500` | `2.9447` | `2.7008` | `2.5818` / `2.6118` | **`2.5699`** (`−0.025`) |
| `19+` | `325` | `3.1058` | `3.0152` | `3.0880` / `3.1430` | **`3.0289`** (`−0.027`) |
<!-- /receipt:by-age -->

### 7.5 Errors by Ability: Two Imperfect Diagnostics

Mean signed error by decile of an ability measure within each course pair, event and category, forward directions (SCY→LCM, SCY→SCM, SCM→LCM). Shape $\chi^2_9$ is a Wald test, with the bootstrap covariance, that all ten forward deciles equal their mean (5% critical value `16.92`). "D2–5 minus D7–9" measures a mid-range bend.

- **Coupled (pair mean).** Deciles of the pair's own mean log time. The bin variable shares the pair's measurement errors: with independent noise $\ln x = \ell + e_A$, $\ln y = \ell + c + e_B$, $\operatorname{cov}(\ln y - \ln x, \tfrac12(\ln x + \ln y)) = \tfrac12(\sigma_B^2 - \sigma_A^2)$, so a correct map trends here whenever the courses' noise differs.
- **Less coupled (separate swim, `independent_swim_deciles`).** Deciles of a separate swim: the swimmer's swim of the same event in the pair's canonical source course (SCY for SCY–LCM and SCY–SCM, SCM for SCM–LCM) at a meet other than either pair meet, at most 90 days from the pair's swim in that course and at least 31 days from both pair swims, the nearest such swim (ties: the earlier date, then the lower meet ID). It shares no swim with the pair, and the minimum gap reduces shared form and taper. It does not remove all coupling (§8.2), and only swimmers who race often have one.

<!-- receipt:ability -->
| Method | Less coupled D1−D10 (95% CI) | D2–5 minus D7–9 | Shape $\chi^2_9$ | Coupled D1−D10 (95% CI) | D2–5 minus D7–9 | Shape $\chi^2_9$ |
| :--- | :--- | ---: | ---: | :--- | ---: | ---: |
| NCAA | `−2.80%` (`[−3.24, −2.37]`) | `−1.37%` | `263.3` | `−2.17%` (`[−2.50, −1.85]`) | `−1.36%` | `379.0` |
| Colorado | `−1.85%` (`[−2.28, −1.42]`) | `−0.96%` | `135.4` | `−1.10%` (`[−1.44, −0.78]`) | `−0.91%` | `162.4` |
| Flat multiplier | `−2.80%` (`[−3.22, −2.38]`) | `−1.37%` | `306.6` | `−2.17%` (`[−2.50, −1.86]`) | `−1.36%` | `440.5` |
| Percentile, same input | `−0.72%` (`[−1.15, −0.31]`) | `−0.15%` | `21.8` | `−0.26%` (`[−0.59, +0.06]`) | `+0.02%` | `14.6` |
| Percentile, age-aware | `−0.57%` (`[−1.00, −0.14]`) | `−0.05%` | `15.8` | `−0.28%` (`[−0.62, +0.05]`) | `+0.03%` | `17.2` |
| **Turnmark Equivalence** | **`−0.86%` (`[−1.27, −0.45]`)** | **`−0.60%`** | **`53.6`** | **`+0.11%` (`[−0.22, +0.41]`)** | **`−0.48%`** | **`55.6`** |
<!-- /receipt:ability -->

Forward decile biases (%) for NCAA, the same-input percentile map and this map:

<!-- receipt:deciles -->
| Decile | Less coupled: NCAA | Less coupled: Percentile, same input | Less coupled: Equivalence | Coupled: NCAA | Coupled: Percentile, same input | Coupled: Equivalence |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| D1 (fastest) | `−1.38` | `−0.43` | `−0.50` | `−0.80` | `−0.02` | `+0.10` |
| D2 | `−1.26` | `−0.25` | `−0.57` | `−0.91` | `+0.08` | `−0.24` |
| D3 | `−0.91` | `+0.01` | `−0.32` | `−0.80` | `+0.04` | `−0.29` |
| D4 | `−1.00` | `−0.26` | `−0.53` | `−0.55` | `+0.06` | `−0.18` |
| D5 | `−0.68` | `−0.14` | `−0.32` | `−0.53` | `−0.20` | `−0.32` |
| D6 | `−0.46` | `−0.25` | `−0.27` | `−0.18` | `−0.14` | `−0.14` |
| D7 | `+0.02` | `−0.04` | `+0.04` | `+0.26` | `−0.08` | `+0.10` |
| D8 | `+0.26` | `−0.15` | `+0.04` | `+0.72` | `+0.03` | `+0.30` |
| D9 | `+0.95` | `+0.17` | `+0.43` | `+1.01` | `−0.02` | `+0.27` |
| D10 (slowest) | `+1.42` | `+0.30` | `+0.36` | `+1.37` | `+0.23` | `−0.01` |
<!-- /receipt:deciles -->

<!-- receipt:ability-coverage -->
| Coverage and sensitivity | Value |
| :--- | ---: |
| Test rows | `39,314` |
| Rows with a separate swim | `17,076` |
| Rows in less-coupled deciles | `16,902` (`43%`) |
| Separate-swim gap from both pair swims | `31–90 days` |
| Coupled diagnostic, meet-clustered: Equivalence D1−D10 | `+0.11%` (`[−0.32, +0.48]`) |
| Coupled diagnostic, meet-clustered: Equivalence shape $\chi^2_9$ | `42.4` |
<!-- /receipt:ability-coverage -->

What these support: a single factor converts the fastest and slowest swimmers in opposite directions by a combined `2–3%`, and the equivalence and percentile maps remove most of that on both diagnostics. On the less-coupled diagnostic this map's remaining trend is a little larger than the percentile maps' and its mid-range bend clearly larger. That agrees with the accuracy result in §7.2, which is the stronger evidence. The coupled diagnostic's expected trend under a correct map depends on $\sigma_B^2 - \sigma_A^2$, which is itself only estimated (§8.1), so it is not an upper bound on confounding in the real data. **Neither diagnostic shows that the remaining pattern is, or is not, ability-dependent conversion error.**

### 7.6 Validation: Is There Curvature Left?

The map is linear in log time and fixed for this revision. Whether a nonlinear stage deserves another experiment is examined on the validation partition only (`validation_curvature` in the receipt), so the test partition stays out of that decision.

<!-- receipt:validation -->
| Validation (41,464 rows) | MAE | Less-coupled D1−D10 | Less-coupled D2–5 minus D7–9 | Coupled D1−D10 | Coupled D2–5 minus D7–9 |
| :--- | ---: | :--- | :--- | :--- | :--- |
| NCAA | `2.9698s` | `−2.38%` (`[−2.78, −2.01]`) | `−1.32%` (`[−1.54, −1.10]`) | `−2.07%` (`[−2.34, −1.76]`) | `−1.41%` (`[−1.57, −1.25]`) |
| Flat multiplier | `2.8034s` | `−2.39%` (`[−2.80, −1.98]`) | `−1.32%` (`[−1.52, −1.12]`) | `−2.07%` (`[−2.35, −1.76]`) | `−1.41%` (`[−1.55, −1.26]`) |
| **Turnmark Equivalence** | **`2.7177s`** | **`−0.43%` (`[−0.84, −0.02]`)** | **`−0.54%` (`[−0.73, −0.34]`)** | **`+0.17%` (`[−0.09, +0.48]`)** | **`−0.53%` (`[−0.66, −0.40]`)** |

Less-coupled coverage on validation: `17,880` of `41,464` rows.
<!-- /receipt:validation -->

Both diagnostics leave a bend: the fast half converts slightly fast and the slower deciles slightly slow. Progression between swims, uneven racing frequency and a mis-measured noise ratio can each produce that pattern as well as curvature can, so it is a reason to test a nonlinear stage against known truth with those effects built in, not a reason to fit one. Choosing a nonlinear stage's strength to flatten the coupled diagnostic is not a valid selection rule: with unequal course noise that diagnostic trends even for the true map, so a fitted shape can make conversions less accurate while the diagnostic improves.

### 7.7 Percentile Preservation

Mean absolute shift, in percentile points, between the entered time's percentile among the source-course times and the converted time's percentile among the actual target-course times, within each direction, event and category of the held-out pairs:

<!-- receipt:percentile-preservation -->
| NCAA | Colorado | Flat | Percentile (same input) | Percentile (age-aware) | **Equivalence** |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `2.50` | `4.47` | `1.54` | `0.83` | `1.35` | **`0.96`** |

Evaluated rows: `39,074`.
<!-- /receipt:percentile-preservation -->

Percentile maps preserve percentiles by construction, so this is a check on the other methods.

### 7.8 Harder Holdouts and Pairing Window

Both holdouts are swimmer-disjoint. The temporal holdout trains on swims through 2025 by training-partition swimmers and tests on 2026 swims by test-partition swimmers. The regional holdout tests every 30-day pair from five archives held out together (`SE`, `AD`, `SD`, `PV`, `MW`) and removes every swimmer with a pair there from training.

<!-- receipt:holdouts -->
| Holdout | Train rows / swimmers | Test rows / swimmers | NCAA | Flat | Percentile (same) | Percentile (age) | **Equivalence** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Later season (2026) | 166,652 / 20,168 | 4,572 / 912 | `3.1792` | `3.0261` | `3.0336` | `2.9984` | **`2.9706`** |
| Regions held out | 196,790 / 23,126 | 34,402 / 4,694 | `3.2905` | `3.2167` | `3.2607` | `3.3278` | **`3.1377`** |
<!-- /receipt:holdouts -->

<!-- receipt:holdout-diagnostics -->
| Holdout | Method | Coupled D10 | Coupled D1−D10 | Coupled D1–D7 range | Less-coupled D1−D10 |
| :--- | :--- | ---: | :--- | :--- | :--- |
| Later season (2026) | **Turnmark Equivalence** | `−1.36%` | `+1.26%` (`[+0.30, +2.32]`) | `−0.44 to +0.03%` | `+0.41%` (`[−0.71, +1.53]`); `2,260` rows |
| Later season (2026) | Percentile, same input | `−0.90%` | `+1.12%` (`[+0.14, +2.21]`) | `−0.52 to +0.30%` | `+0.62%` (`[−0.50, +1.73]`); `2,260` rows |
| Later season (2026) | Percentile, age-aware | `−0.92%` | `+1.14%` (`[+0.15, +2.22]`) | `−0.55 to +0.28%` | `+0.63%` (`[−0.47, +1.67]`); `2,260` rows |
| Regions held out | **Turnmark Equivalence** | `−0.82%` | `+1.24%` (`[+0.86, +1.60]`) | `+0.42 to +0.63%` | `+0.19%` (`[−0.36, +0.81]`); `8,428` rows |
| Regions held out | Percentile, same input | `−0.36%` | `+0.93%` (`[+0.54, +1.29]`) | `+0.25 to +0.82%` | `+0.13%` (`[−0.44, +0.79]`); `8,428` rows |
| Regions held out | Percentile, age-aware | `−0.16%` | `+0.80%` (`[+0.38, +1.18]`) | `+0.46 to +0.98%` | `+0.13%` (`[−0.48, +0.85]`); `8,428` rows |
<!-- /receipt:holdout-diagnostics -->

The slowest decile converts too fast in both holdouts, and in the regional holdout deciles 1–7 also sit at a level offset of roughly `+0.4%` to `+0.6%`. The anchored percentile maps show the same slow-tail pattern, smaller in the regional holdout. Improvement between the two swims of a pair is absorbed as a course effect, and a map with no age input cannot separate the two (A3, §8.3). The less-coupled spreads cross zero on these smaller samples.

<!-- receipt:window -->
| Pairing window | Test rows / swimmers | NCAA | Colorado | Flat | Percentile (same) | Percentile (age) | **Equivalence** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `14d` | 19,374 / 2,985 | `2.7429` | `3.3151` | `2.5834` | `2.5242` | `2.5300` | **`2.5095`** |
| `30d` (main) | 39,314 / 4,710 | `3.0414` | `3.6528` | `2.8582` | `2.7882` | `2.7864` | **`2.7711`** |
| `60d` | 86,704 / 7,468 | `3.3758` | `3.9886` | `3.1632` | `3.0610` | `3.0567` | **`3.0542`** |
<!-- /receipt:window -->

MAE rises with the window for every method, consistent with more change in level between swims further apart. The ordering of methods is the same in all three windows.

### 7.9 Venue Cohorts (descriptive)

`same_matched_facility` and `different_matched_facility` compare the facility record each meet's locality resolved to (Appendix B), a proxy rather than a verified building. `altitude_proxy_meet_involved` flags a pair when either meet is in a mountain state, a listed high-elevation city or postal prefix, declares a `B1` altitude of at least 3,000 ft, or comes from the Utah or Montana archive. The cohorts differ in swimmers, events and pace, so these differences are descriptive, not measured effects of travel or altitude.

<!-- receipt:venue-cohorts -->
| Cohort | Rows / swimmers | NCAA | Flat | Percentile (same) | **Equivalence** |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `altitude_proxy_meet_involved` | 3,648 / 423 | `4.1203` | `4.0080` | `3.8924` | **`3.8669`** |
| `different_matched_facility` | 26,550 / 3,597 | `3.1602` | `2.9919` | `2.9525` | **`2.9219`** |
| `no_altitude_flag_both_meets` | 35,518 / 4,336 | `2.9383` | `2.7472` | `2.6811` | **`2.6644`** |
| `same_matched_facility` | 7,138 / 1,208 | `2.4981` | `2.2791` | `2.2114` | **`2.2078`** |
<!-- /receipt:venue-cohorts -->

### 7.10 Extrapolation: the Fast-Swimmer Example

<!-- receipt:fast-swimmer -->
| 14:13.00 1650 yd SCY freestyle (men) → 1500 m LCM | Converted | Converted back |
| :--- | ---: | ---: |
| NCAA | `14:43.93` | `14:12.99` |
| Colorado Timing | `14:30.06` | `14:13.00` |
| Flat multiplier per cell | `14:44.33` | `14:12.98` |
| Percentile, same input | `14:57.54` | `14:12.99` |
| Percentile, age-aware (age 17-18) | `14:57.54` | `14:12.99` |
| Percentile, age-aware (age 19+) | `14:57.54` | `14:12.99` |
| **Turnmark Equivalence** | **`14:46.57` (`empirical-out-of-range`)** | **`14:12.99`** |
<!-- /receipt:fast-swimmer -->

The entered time lies beyond the fast edge of the men's 1650 support, so this conversion is the map's ratio held at that edge (§5.8), which the caveat says. It is extrapolation and should be read that way: the cell has `86` training pairs (`78` swimmers) and is itself low-evidence. §9 records an exploratory check suggesting the held ratio is slightly too large here.

### 7.11 What the Intervals Do Not Cover

Bootstrap intervals resample swimmers (primary) or one meet per pair (sensitivity) with the fitted models held fixed. They do not cover model-selection uncertainty: the shrinkage priors and noise ratios were estimated once, and the 30-day window and the outlier screen chosen once; none is re-estimated or re-chosen inside each replicate. They also do not remove residual dependence: a pair joins two meets but is clustered on one, swimmers share clubs, coaches and taper cycles, and same-day conditions (pool, timing system, altitude) correlate errors across swimmers in ways neither clustering captures. Treat them as lower bounds on uncertainty.

---

## 8. Assumptions the Data Cannot Establish (c)

### 8.1 The Noise Ratio and Unmeasured Course Aptitude (A2)

This is the model's weakest identifying assumption. Same-course repeats see timing, race-day and short-term form noise. They cannot see a swimmer's aptitude for one course over another (a strong underwater kicker who gains more in short course), which adds spread to the cross-course pairs but not to the repeats. If swimmer $i$'s target-course time carries an aptitude term $\gamma_i$, the effective noise ratio in the pairs is $(\sigma_B^2 + \operatorname{Var}\gamma)/\sigma_A^2$, not $\sigma_B^2/\sigma_A^2$, and the Deming slope inherits the error. Nothing in a single pair separates $\gamma_i$ from level, so the fitted $\delta$ is an estimate under A2, not a measurement of the right $\delta$. SCM ratios are weaker still: outside the 50 free they are pooled (§5.3). The synthetic recovery test confirms the estimator under A2, not A2 itself.

### 8.2 Independence of the Separate Swim (A5)

The less-coupled diagnostic is only as clean as its separate swim is independent of the pair's errors. Form persists beyond a month; progression between the separate swim and the pair correlates the bin with the pair's residual; and the swimmers who have such a swim (`43%` of test rows) race more often than those who do not. Each of these can produce a trend or bend for a correct map. The 31-day minimum gap reduces the first, not the others.

### 8.3 One Level per Pair (A3)

A pair's two swims are up to 30 days apart, and young swimmers improve measurably in that time. Improvement between the swims is indistinguishable, in one pair, from the course effect, and the direction of the bias depends on which course came first. The window table in §7.8 is consistent with level change growing with the gap; the slow-tail holdout bias is consistent with it concentrating in fast-improving swimmers. Neither establishes how much of the remaining error it explains.

### 8.4 The Support as a Range of Trust (A6)

The 0.5th–99.5th percentile bounds are a convention. Inside them the fitted slope is trusted; beyond them the edge ratio is held, which is a choice of extrapolation, not an estimate. Times beyond the edges are sparse in training, not absent, and nothing tests whether holding the edge ratio is better than extending the slope. The `empirical-out-of-range` caveat marks every conversion that depends on this choice (`1.4%` of test conversions).

### 8.5 Sample Composition

The archives are those with public bulk exports, not a probability sample of US swimmers (Appendix A): Pacific and North Carolina supply over half the races and about two-thirds of the 30-day pairs, SCM and adult swims are sparse, and source-scoped swimmer IDs are not a verified person count. The map describes swimmers who race both courses within a month in these archives.

---

## 9. Exploratory Observations (not reproduced by the pipeline)

These come from checks run outside the evaluation pipeline, by the owner's reviewer or ad hoc against this snapshot. They are not in any receipt, there is no script in this repository that reproduces them, and some were run against an earlier revision. **No conclusion in §1, §6 or §7 rests on them**; each is recorded as a lead, with what it would mean if it holds.

| | Observation | Status | If it holds |
| :--- | :--- | :--- | :--- |
| **E1** | Cross-course spread was `1.05–1.34` times what the repeat noise predicts in the SCY–LCM cells checked and up to `1.79` times in SCM cells; in simulation, unmeasured aptitude tilts conversions in the same direction as the less-coupled trend. | Reviewer check, under an earlier row-weighted noise estimate | A2 is violated in the direction that could explain part of the §7.5 trend (§8.1) |
| **E2** | With separate swims 0–30 days from the pair's source-course swim (instead of at least 31 days from both), this map's less-coupled spread was `−1.45%` on test and `−1.24%` on validation. | Ad hoc rerun of the diagnostic | Near swims share form with the pair, which is why the 31-day minimum exists (§8.2) |
| **E3** | In a breakdown of an earlier revision with the same holdout pattern, the slow tail was mostly 10-and-unders converting SCY→LCM, whose bias depended on which swim came first, and held-out South Dakota supplied most of the regional slowest-decile rows. | Reviewer breakdown, earlier revision | The §7.8 slow-tail bias is progression (A3), concentrated in one age band and one archive |
| **E4** | The archive has no men's 1650 yd under `14:20` and no 1500 m LCM under `14:40`; one of the `86` men's 1650 training pairs is under `15:00`; fastest-decile LCM/SCY ratios are about `1.033–1.035`, which would give a faster conversion than `14:46.57`, and NCAA's `14:43.93` sits inside the range those pairs imply. | Reviewer archive query | The edge-ratio extrapolation in §7.10 is slightly slow for elite distance swimmers |
| **E5** | `2,213` of the `189,046` clean training rows fall outside their cell's support. | Ad hoc count against this snapshot | Out-of-range times are sparse, not absent (§8.4) |
| **E6** | A nonlinear stage whose strength was chosen to flatten the coupled diagnostic gained `0.007s` of test MAE. | Earlier evaluation; not part of the model | Supports the selection-rule argument in §7.6 |

---

## 10. Production Integration in `turnmark-core`

`evaluate_and_train.py --export-empirical-json data/empirical.json` writes the fitted snapshot to [`data/empirical.json`](../../data/empirical.json) (schema 3, `14,057` bytes):

- `cells`: for each of the `28` `(event, category)` keys, one two-knot table per course, `[scale value, course log seconds]` at the edges of its training support (SCY is the identity);
- `lowEvidenceCells`: the `60` directional keys whose course-pair cell has fewer than `100` effective swimmers;
- `preciseLatentRanges`: for each of the `168` directional keys, the scale range where the bootstrap 95% interval is within 1%, or `null`;
- `source`: SHA-256 provenance for the cells, the evaluator script, the loaded swims and the lakehouse snapshot.

The same run writes [`fixtures/empirical-parity.json`](../../fixtures/empirical-parity.json): `1,008` exact-hundredth reference conversions with their expected caveat, tied to the snapshot by its cell hash. The Python reference evaluates them exactly as the engine does.

1. **Rust core (`crates/turnmark-core`).** `ConversionMethod::Empirical` (`"turnmark-empirical-2026"`) embeds the snapshot at compile time. `empirical_equivalent` in [`engine.rs`](../../crates/turnmark-core/src/engine.rs) maps the entered log time through the source course's knots to the shared scale, then out through the target course's knots, continuing with slope 1 beyond the outer knots, and truncates to hundredths once. It does not consult the NCAA table. Conversions carry `empirical-out-of-range` or `empirical-low-evidence` as in §5.9. When pool elevation is supplied, the sea-level deduction (`usa-swimming-altitude-2026` or `ncaa-altitude-2026-27-d1`) is computed in whole hundredths and applied to the entered swim before conversion, so the only rounding is the final truncation. `tests/conformance.rs` checks every parity case to the hundredth and its caveat, plus round trip, three-course composition, monotonicity and the altitude ordering.
2. **Consumers.** The SDK (`@turnmark/sdk`), web app (`src/`), embed widget (`apps/embed/`), iOS (`apps/ios/`), Android (`apps/android/`) and MCP server and app (`packages/mcp/`) label the method "Turnmark Equivalence", describe its result as an estimated equivalent time, and show both caveats. `NCAA (default)` stays the default rule.

---

## 11. Reproducibility Commands

```bash
# 1. Run the research unit tests (synthetic recovery, known truth under the model's assumptions,
#    duplication invariance, provenance, lakehouse, and that this report matches its receipts)
TURNMARK_LAKEHOUSE_TESTS=1 PYTHONPATH=research/conversion-model:research/conversion-model/local \
  target/lakehouse-py312/bin/python -m unittest discover -s research/conversion-model -p "test_*.py" -v

# 2. Rebuild this report's tables from the receipts, or check that they match
python research/conversion-model/render_report_tables.py
python research/conversion-model/render_report_tables.py --check

# 3. Rebuild the meet-to-facility locality join (requires the local SDIF cache)
PYTHONPATH=research/conversion-model:research/conversion-model/local \
  target/lakehouse-py312/bin/python research/conversion-model/local/build_meet_venue_join.py \
  --output research/conversion-model/data/national-checkpoint-17

# 4. Materialize and probe the SQLite + Parquet lakehouse
target/lakehouse-py312/bin/python research/conversion-model/lakehouse.py build \
  research/conversion-model/data/national-checkpoint-17/results.csv \
  --manifest research/conversion-model/data/national-checkpoint-17/manifest.json \
  --output target/lakehouse-national-17 \
  --max-rows 10000000
target/lakehouse-py312/bin/python research/conversion-model/lakehouse.py probe \
  target/lakehouse-national-17

# 5. Fit, evaluate and export data/empirical.json and fixtures/empirical-parity.json in one run
#    (refuses to run if snapshot.json disagrees with the opened Iceberg view or the venue CSV is missing)
target/lakehouse-py312/bin/python research/conversion-model/evaluate_and_train.py \
  --duckdb target/lakehouse-national-17/queries.duckdb \
  --input-label national-checkpoint-17 \
  --venues-csv research/conversion-model/data/national-checkpoint-17/meet_venues.csv \
  --output-dir target/conversion-model-eval-17 \
  --public-summary research/conversion-model/evaluation-checkpoint-08.json \
  --export-empirical-json data/empirical.json
```

---

## Appendix A. Corpus by Archive

Usable races by archive authority (after deduplication) and the 30-day directional pairs each contributes (— where the receipt lists none):

<!-- receipt:archives -->
| Archive authority | Usable races | Share | 30-day directional pairs |
| :--- | ---: | ---: | ---: |
| Pacific Swimming | 2,590,738 | 30.46% | 120,278 |
| North Carolina Swimming | 1,955,332 | 22.99% | 58,693 |
| Southeastern Swimming | 1,056,077 | 12.41% | 5,641 |
| Michigan Swimming | 892,772 | 10.49% | 32,041 |
| Adirondack Swimming | 648,545 | 7.62% | 10,327 |
| South Dakota Swimming | 349,255 | 4.11% | 16,165 |
| Potomac Valley Swimming | 210,123 | 2.47% | 1,180 |
| Oregon Swimming | 186,477 | 2.19% | 11,114 |
| Florida Gold Coast Swimming | 127,773 | 1.50% | 2,057 |
| Niagara Swimming | 126,843 | 1.49% | 7,233 |
| Midwestern Swimming | 96,294 | 1.13% | 1,089 |
| Utah Swimming | 79,656 | 0.94% | 1,123 |
| Montana Swimming | 78,275 | 0.92% | 2,055 |
| Kentucky Swimming | 35,285 | 0.41% | 31 |
| Indiana Swimming | 33,356 | 0.39% | — |
| Southern California Swimming | 21,045 | 0.25% | 673 |
| YMCA National Championships | 17,719 | 0.21% | 124 |
| South Texas Swimming | 1,202 | 0.01% | — |
<!-- /receipt:archives -->

Input records by frozen export collection (before deduplication). `southeastern-exports` also carries the Utah and Montana archives:

<!-- receipt:collections -->
| Frozen export collection | Archive files | Input race records |
| :--- | ---: | ---: |
| `adirondack-exports` | 575 | 650,217 |
| `florida-gold-coast-exports` | 100 | 127,773 |
| `indiana-exports` | 27 | 33,356 |
| `kentucky-exports` | 21 | 35,285 |
| `michigan-exports` | 736 | 892,772 |
| `midwestern-exports` | 137 | 96,307 |
| `niagara-exports` | 178 | 126,843 |
| `north-carolina-exports` | 1,230 | 1,955,341 |
| `oregon-exports` | 185 | 186,477 |
| `pacific-exports` | 1,589 | 2,597,334 |
| `pvs-exports` | 513 | 210,128 |
| `socal-exports` | 15 | 21,073 |
| `south-dakota-exports` | 285 | 349,255 |
| `south-texas-exports` | 3 | 1,202 |
| `southeastern-exports` | 919 | 1,216,483 |
| `ymca-nationals-exports` | 8 | 20,995 |
| **Total** | **6,521** | **8,520,841** |
<!-- /receipt:collections -->

Coverage years: Pacific 2013–2026 (including Northern Nevada/Tahoe altitude, SCM, Speedo/US Open nationals and adult `19+` swims); North Carolina 2020–2026; Southeastern 2010–2026; Michigan 2016–2026; Adirondack 2010–2026; South Dakota 2018–2026 (including Black Hills altitude and SCM); Potomac Valley 2010–2026; Oregon 2023–2026; Florida Gold Coast 2022–2026; Niagara 2019–2026; Midwestern 2019–2026; Utah 2018–2026 (Wasatch Front altitude); Montana 2021–2026; Kentucky 2026; Indiana 2025–2026; Southern California 2024–2026; YMCA National Championships 2025–2026; South Texas 2026. Only Adirondack, Potomac Valley and Southeastern begin in 2010. The acquisition receipt's `limitations` list the exclusions (seeds, relays, splits, invalid and DQ slots; missing or ambiguous registration IDs; no name-based joins).

## Appendix B. Meet-to-Venue Locality Join

Venue cohorts (§7.9) use the committed public catalog in [`team-directory/`](./team-directory/CATALOG.md): facility records in [`catalog/facilities.csv`](./team-directory/catalog/facilities.csv), pool basins in [`catalog/pool_basins.csv`](./team-directory/catalog/pool_basins.csv), and program listings in [`snapshot/programs.csv`](./team-directory/snapshot/programs.csv). `local/build_meet_venue_join.py` extracts SDIF `B1` meet headers and joins each meet to a facility record in two deterministic passes, 5-digit postal code first, then `(city, state)`, counted once per unique meet (`meet_locality_matches` in the evaluation receipt):

<!-- receipt:venue-join -->
| Meet-to-venue locality join | Meets |
| :--- | ---: |
| Unique meets with SDIF `B1` headers | 6,059 |
| Matched by 5-digit postal code | 4,837 |
| Matched by `(city, state)` | 612 |
| **Matched to a facility record** | **5,449** (89.9%) |
| With locality coordinates | 5,383 |
| Unmatched | 610 |
<!-- /receipt:venue-join -->

The join picks a likely facility in a postal code or city. It does not verify a facility name or address, and a shared `facility_id` is not evidence that two meets were swum in the same building, basin or bulkhead position.

## Appendix C. Local Lakehouse

[`lakehouse.py`](./lakehouse.py) materializes a dual-store local lakehouse from the canonical ingest store: an indexed SQLite store for point lookups by swimmer and date and by meet and event (swimmer, meet and event keys are stored once in dimension tables; the race table's `athlete_history(swimmer, race_day)` and `meet_results(meet, event, time_cs)` indexes hold only integers, and `lakehouse.py rebuild-hot` replaces the store from the committed snapshot), and an Iceberg table of Zstandard Parquet files, identity-partitioned by year and course, for the longitudinal self-joins; DuckDB reads it through the committed Iceberg metadata rather than a file glob. The design and its hosted counterparts are in [`MEET_LAKEHOUSE_EXPERIMENT.md`](../../docs/MEET_LAKEHOUSE_EXPERIMENT.md); serving costs are in [`LAKEHOUSE_COST_MODEL.md`](../../docs/LAKEHOUSE_COST_MODEL.md). Measured for this checkpoint (acquisition receipt `lakehouse_storage`):

<!-- receipt:lakehouse -->
| Lakehouse (`target/lakehouse-national-17`) | Measured |
| :--- | ---: |
| Iceberg snapshot | `4441271835344284414` |
| Hot SQLite store | 1,101.6 MB (129.5 bytes/row) |
| Parquet warehouse | 366.8 MB (43.1 bytes/row) |
| Point lookup by swimmer, first / repeat median | 0.311 ms / 0.020 ms |
| Filtered DuckDB aggregate, first / repeat median | 3.58 ms / 2.80 ms |
<!-- /receipt:lakehouse -->

The evaluator measures the scanned Iceberg snapshot itself (honoring `snapshot_from_id`) and refuses to run if it disagrees with `snapshot.json` or a referenced file is missing. `lakehouse.py probe` checks that both stores hold the same rows with no duplicates and return one swimmer's latest 50 rows identically; its output is not part of a receipt.
