# Likely-time predictor (research POC)

This answers: *a swimmer swam X in course A; what will they most likely swim in the same event
in course B on a later date, and within what 80% range?* It is a forward **prediction**: age,
progression, the gap to the target meet, season and the swimmer's own history all count. That
makes it separate from the converter's symmetric course **equivalence**. It is not wired into
any app.

**Bottom line.** On a forward, swimmer-disjoint 2026 test, the history model's MAE is
**3.32 s against 3.88 s for an age- and gap-adjusted NCAA conversion** (4.97 s for raw NCAA;
the 3.88 s baseline is a reviewer measurement, see below).
About two-thirds of the gain over raw NCAA comes from correcting NCAA for age, gap and season,
which a lookup table also does; the model adds a further 0.5 s (about 13%), mostly for young
swimmers. Both need the swimmer's age and the target meet date.

- Code: [`predictor_poc.py`](predictor_poc.py)
- Tests: [`test_predictor_poc.py`](test_predictor_poc.py) (invented records only)
- Receipt: [`predictor-receipt-checkpoint-17.json`](predictor-receipt-checkpoint-17.json)
  (aggregates only)

```bash
# Rerun against the local national checkpoint (~7 minutes)
python research/conversion-model/predictor/predictor_poc.py

# Run the tests
python -m unittest discover -s research/conversion-model/predictor -v
```

The CI job in `conversion-research.yml` does not cover this folder: unittest discovery doesn't
recurse into a directory without `__init__.py`.

## Method

**Examples.** The script reuses `load_swims_from_duckdb`, `deduplicate_best_of_meet`,
`swimmer_partition` and the NCAA functions from `evaluate_and_train.py`, read-only. On
national checkpoint 17 that gives 5.90M best-of-meet swims. Each target swim is paired, once
per other course, with the swimmer's **most recent earlier** swim of the same event, with a gap
of 1–365 days. Dates are always strictly forward. That yields 2.77M examples.

**Features, all known on the source date:**

- log source time, standardized within (source course, event, sex)
- direction, event and sex
- age recorded on the source swim. Examples whose source swim has no age are dropped (1,828 of
  2.77M), never backfilled from the target meet or imputed; the app would collect age anyway.
- gap in days
- target month for each target course. This is the season and taper term; the app knows it once
  the swimmer names the target meet.
- Own history ("My times"), used only by the history models:
  - best time in the target course within the 365 days up to the source date, and how old it is
  - the source time against the best source-course time in the 365 days before it

**Split.**

- **Temporal.** Models train on targets before 2026-01-01. The test set is targets on or after
  that date.
- **Swimmer-disjoint (headline).** Training uses the 70% train partition. Interval calibration
  uses the 15% validation partition on 2025 targets. The test set is the 15% test partition.
- **Non-disjoint (the real use case).** Training also includes the test swimmers' own
  pre-cutoff examples. It is scored on the same 59,404 test rows (4,422 swimmers).

**Models, simplest first:**

1. `ncaa`: the NCAA 2025-27 factor.
2. `flat`: the median ratio per (direction, event, sex) cell.
3. `pooled`: Huber IRLS on log(target/source), offset by the NCAA log factor. It has
   unpenalized direction-level intercept, speed and age terms, plus per-cell intercept and
   speed deviations shrunk toward NCAA with ridge λ=100, chosen on validation. Global terms cover
   age, gap, age×gap, gap×speed and target month.
4. `history`: `pooled` plus the own-history features.
5. `gbm`: a depth-3 histogram residual booster on top of `history` (150 trees at 0.1, early stop
   on validation). It is only worth keeping if it clearly wins.

**Intervals.** The 80% range comes from empirical 10th and 90th percentile log residuals on the
calibration set. Buckets are gap bucket × age band × target-course history (yes/no) × speed
band, falling back to coarser keys when a bucket has fewer than 300 rows.

## Results (forward test, swimmer-disjoint, 59,404 rows)

| Model | MAE s (95% CI) | Median AE s (95% CI) | Signed bias s |
|---|---|---|---|
| NCAA factor | 4.97 (4.88–5.08) | 2.81 (2.76–2.88) | +2.50 |
| Flat multiplier | 4.49 (4.41–4.59) | 2.56 (2.51–2.62) | +1.21 |
| Pooled regression (age, gap, season) | 3.46 (3.39–3.53) | 2.00 (1.96–2.04) | −0.12 |
| + own history | **3.32 (3.25–3.40)** | **1.91 (1.87–1.94)** | −0.07 |
| + residual GBM | 3.27 (3.19–3.34) | 1.88 (1.84–1.92) | −0.04 |

**Fair forecasting baselines.** NCAA is a conversion, not a forecast, so beating it overstates
the model. An independent review (scripts outside this folder, training rows only) built cheap
forecasts on the test rows: the NCAA conversion times the median ratio of actual to NCAA for each
lookup cell. These baselines and the margins below were measured before examples required a
source-date age (on 59,510 test rows, 106 more than now); the receipt does not recompute them.

| Baseline | MAE s |
|---|---|
| NCAA × lookup by age × gap × event group | 4.01 |
| NCAA × lookup by age × gap × event group × direction × target month | 3.88 |
| NCAA × lookup by age × gap × 14 events × direction × sex | 3.80 |
| Latest prior target-course time + age drift, blended with the lookup | 3.81 |

The history model beats the direction-and-month lookup by 0.56 s (0.52–0.60) and the blended
persistence baseline by 0.50 s (0.46–0.54). The margin is similar with full 2024 and 2025 test
years (0.52 s and 0.49 s against the finest lookup). It is largest for 10-and-unders (3.84 s
against 4.55 s) and small for 17–18-year-olds (2.59 s against 2.70 s).

The CIs come from a swimmer-clustered bootstrap with 500 reps. Reruns reproduce
these to about 0.01 s, not bit for bit, because of floating-point order in threaded BLAS. MAE differences:

- pooled − NCAA: −1.50 s (−1.58 to −1.43)
- history − pooled: −0.14 s (−0.16 to −0.12)
- gbm − history: −0.055 s (−0.066 to −0.045)

**Why NCAA does worse here than in the equivalence receipt.** That receipt reports NCAA test MAE
3.05 s, but it paired swims ≤30 days apart. Real prediction gaps are mostly 3–12 months, and
young swimmers improve over that time, so NCAA's +2.5 s bias is mostly unmodelled progression.
Error by gap, in MAE seconds:

| Gap | NCAA | Pooled | History |
|---|---|---|---|
| 1–30 d | 3.30 | 3.04 | 2.79 |
| 31–90 d | 3.90 | 3.14 | 2.96 |
| 91–180 d | 4.60 | 3.48 | 3.36 |
| 181–365 d | 6.10 | 3.68 | 3.55 |

NCAA error nearly doubles across the year. The predictor's error grows only about 25%.

**Age carries most of the lift.** For 10-and-unders, NCAA MAE is 6.72 s against 3.84 s for the
history model. For 17–18-year-olds the gap shrinks to 3.40 s against 2.59 s.

**Own history.** It adds a modest, real gain: −0.14 s overall. Rows with a recent target-course
best (75% of test rows) score 2.90 s MAE, against 4.57 s without one. Most of that difference is
because swimmers with history are easier to predict, not because of the feature itself. The
non-disjoint variant scores the same as the disjoint one (3.320 s against 3.321 s). A pooled
model with about 430 parameters doesn't memorize swimmers: their history helps through features,
not through training on them.

**Season and taper.** Without target-month terms, the history model's signed bias swung about
±1 s by month, too slow at the March and July–August championships (an ablation run before the
source-age requirement). With them, the largest residual monthly bias is 0.84 s (April). Adding
the month terms also halved the GBM's edge.

**GBM verdict.** It passes the keep rule set before the first run: the CI excludes 0 and the gain
is over 0.05 s. But the gain is 0.055 s, or 1.7%, it hit the 150-tree cap, and it is opaque. The
recommendation is the linear `history` model. Revisit the GBM only if a product needs the last
2%.

### 80% interval coverage (history model, forward test)

| Slice | Coverage | Median width |
|---|---|---|
| Overall | **80.8%** (9.2% below, 10.0% above) | 7.5 s / 8.7% |
| Calibration set (in-sample) | 80.0% | 8.6% |
| Gap 1–30 d / 31–90 / 91–180 / 181–365 | 76.4 / 80.3 / 81.4 / 81.0% | 7.4–9.4% |
| Age 10u / 11-12 / 13-14 / 15-16 / 17-18 / 19+ | 80.5 / 80.3 / 80.8 / 81.1 / 82.2 / 79.0% | 12.0% → 7.8% |
| Speed fast / middle / slow | 81.8 / 80.9 / 79.6% | 6.5 / 8.5 / 13.3% |
| SCY→LCM / LCM→SCY | 81.2 / 81.1% | 8.3 / 9.0% |
| SCM directions | 69–77% (under-covers) | 8.5–9.8% |
| Events | 100 FL 75.6% to 1500 FR 92.6% | about 8.5–8.8% |

Calibration carries forward in time (a full 2025 test year covers 79.3%, 2024 78.8%; this and
the two other side experiments in this paragraph were run before the source-age requirement).
The weak spots are SCM directions, short gaps and the 100-stroke events (75–79%) because the
buckets are not conditioned on event or course. Distance free events over-cover. A single global 10th/90th
percentile pair already reaches 80.2%, so the current buckets add little. Calibrating on half the
validation swimmers after choosing λ on the other half gives 80.4%, so sharing the validation set
does not inflate coverage.

**80% across users is not 80% per user.** Errors cluster by swimmer. In a reviewer experiment
run before the source-age requirement, coverage weighted by swimmer was 77.4%, and among swimmers
with at least 5 test rows, 12.1% were covered less than 60% of the time, against about 3.7% if
errors were independent. Some regular users would see the
range miss most of the time.

### Worked examples (synthetic inputs, history model)

| Case | NCAA | Likely | 80% range |
|---|---|---|---|
| Man, 20, 14:13.00 SCY 1650 in March, LCM 1500 in June, no LCM history | 14:43.93 | **14:58.96** | 14:17.35 – 15:44.05 |
| Same, with a synthetic 15:05.00 LCM best from the previous July | 14:43.93 | **14:59.48** | 14:32.88 – 15:37.07 |
| Girl, 12, 1:05.00 SCY 100 free in March, LCM in July, no LCM history | 1:14.37 | **1:12.10** | 1:08.96 – 1:15.68 |
| Same, with a synthetic 1:17.00 LCM best from the previous July | 1:14.37 | **1:12.68** | 1:09.61 – 1:15.61 |

How to read these:

- **The 1650 swimmer.** The model is about 15 s slower than NCAA. The synthetic history agrees
  with the model, so it narrows the range without moving the point. Training has only 129 men's
  SCY→LCM 1650 examples under 15:30, and 1500-FR test MAE is 23 s with a −5.4 s bias, so treat
  elite distance predictions as weakly supported.
- **The 12-year-old.** The model expects about 2 s of improvement beyond the NCAA conversion over
  four months. Her older, slower long-course best pulls the prediction back by about 0.6 s.

## Productizing it

**Inputs the app would need:**

- age, or birth year, at the source swim. Required: it is the biggest lift.
- source date and target meet date. Gives gap and season.
- sex, event and course, as today.
- optionally, the "My times" history: dated swims in both courses for the past year.

Without dates and age, this collapses into a slightly better flat multiplier.

**Presentation.** Show the result as "Likely time" with the 80% range, separate from the
converter's equivalent time. Never feed it back into equivalence. Describe the range as
covering 80% of swims across swimmers, not as an 80% range for this swimmer.

**Before shipping, the work left:**

1. Condition intervals on course family and event, so SCM and 100 fly cover properly.
2. Export a small coefficient table (about 430 numbers plus a few hundred interval quantile
   pairs) for the engine.
3. A rolling re-fit and recalibration cadence, because progression and season shift by year.
4. A minimum-support guard: decline, or widen sharply, for sparse cells such as elite distance,
   19+ and SCM, instead of extrapolating.
5. Handle best-time inputs: ask for the most recent swim, or train on best-time sources (see
   pairing choice below).

## Risks and limits

- **Leakage.** Features come only from swims dated on or before the source, and the source is
  strictly before the target. The only target-side inputs are the target date (gap and month,
  which the user supplies) and the target time as the label. Tests check all of this: a target
  is never in its own history, changing any other target-record field (age, meet, region) leaves
  every feature unchanged, and a source swim without an age yields no example.
  Two residual risks remain:
  - λ selection and interval calibration share the validation set (one scalar; small).
  - Target month is an input the user must supply, not something the model observes after the
    fact.
- **Survivorship.** Pairs exist only for swimmers who race again in the other course. Among SCY
  swims from 2024-07 to 2025-06, the share with a same-event LCM swim within 365 days is 64% for
  the fastest within-age quartile and 32% for the slowest. The test set over-represents
  committed, improving swimmers, and errors for someone who stops training are unmeasured. The
  64% / 32% figure counts raw rows (prelims and finals both). A reviewer check run before the
  source-age requirement, counted once per swimmer and event (season best), found 54% against
  23%, a 2.4× skew, and that most of the slowest quartile (79%) do race again within a year,
  just not in long course.
- **Taper and meet level.** Season terms absorb the average taper. Whether a specific source or
  target meet is a taper meet is not observed, because `meet_class` is mostly "unknown". This is
  a large part of the remaining error.
- **Population.** USA Swimming LSC exports: age-group heavy, few swimmers 19+ (162 test rows),
  SCM thin (about 2.8k test rows across four directions), and no NCAA-only meets. The headline
  numbers describe age-group swimmers.
- **Pairing choice.** Each target uses the most recent earlier source. In side experiments run
  before the source-age requirement, rebuilt as "first target after each source" (my next meet),
  the history model scored 3.38 s; with the source set to the swimmer's fastest swim of the prior
  year, it scored 3.37 s but predicted 0.43 s too fast, because a best time is a lucky high
  point. A user who enters a best time instead of a recent
  swim needs that correction.
- **Swimmer identity.** Swimmer-disjoint splits assume one person carries one `swimmer_id`. If a
  club or LSC change can issue a second ID, one person could straddle partitions; this depends on
  how the ID is derived upstream.
- **Privacy.** The receipt holds aggregates only. Any group with fewer than 50 rows or 20
  swimmers is suppressed, and the worked examples use invented inputs.
