# Conversion-model research

Research checked October 19, 2026. This is a development experiment, separate
from Turnmark's shipped calculator. A private local pilot of public meet exports
has been collected; no swimmer-level dataset is included in the repository, and
no trained predictive model is approved for the app.

## Question and scope

Can a small model predict a comparable, nearby-date swim in another course more
accurately than the existing NCAA and legacy Colorado methods on unseen
swimmers and later meets? Start with SCY → LCM 50/100/200 freestyle. Expand
directions, strokes, distances or populations only after measuring their own
coverage and errors. Do not invert a fitted predictor and assume its reverse
direction has the same statistical properties.

Keep NCAA as the production default. General swim-logger expansion, cloud sync
and coach dashboards remain outside the product plan. A reusable local meet
archive/query experiment supports local model evaluation and training. Operating
a hosted meet-results aggregator, running a national search service and migrating
Turnmark to a cloud backend are explicit project anti-goals. The hypothetical
hosted architecture and cost model are public references for curious readers,
preserving the reasoning should that scope boundary ever be deliberately
reconsidered. They are not deployment plans or roadmap commitments. Local history
already in the product remains supported.

The immediate directory/archive objective is **local model training and
evaluation**. The [public research catalog](../research/conversion-model/team-directory/README.md)
publishes organization/facility facts, provenance, format contracts and explicit
coverage gaps so others can reuse the groundwork, or the owner can revisit it
later. Like the conceptual lakehouse reference, this preserves future options
without becoming a Turnmark deployment plan. The [collection plan](../research/conversion-model/DIRECTORY_PLAN.md)
keeps the general archive and a five-million-race checkpoint and later 10–30-million-race exploration separate
from the first paired-swim pilot; volume alone does not establish completeness.

## Altitude follow-up

[Altitude policies and empirical research](ALTITUDE_RESEARCH.md) records verified
USA Swimming/NCAA policy differences and a separate, same-course matched-swim
experiment. This does not change the initial cross-course pilot or claim a
trained altitude model. Policy choice and course-conversion method must remain
independent; any future prediction interval requires held-out calibration.

[Venue context and cohort audit](VENUE_RESEARCH.md) now implements an offline
sidecar for facilities, physical basins, dated course configurations and explicit
race mappings. It preserves raw/adjusted/unknown clock basis and frozen pairs.
The first real-pair replay reports missing reviewed linkage; no actual venue
mappings or empirical altitude model are claimed.

## What the original paper establishes

[Alec Vercruysse's paper](https://www.menloschool.org/live/files/3097-alec-vercruysse)
is a useful baseline and motivation, not a production model card:

- It analyzed approximately one million scraped **links**, not a claim that all
  six million discovered links had been processed. Its best-time dataset has
  688,868 swims, primarily youth aged 5–18 (printed pages 4–5 and 9).
- It weights pairs by the time between swims, falling linearly to zero at
  1.5 years, and explicitly acknowledges that progress between dates confounds
  course conversion (pages 11–12).
- The often-quoted −9.16 centiseconds/year and +27.98 centiseconds male
  coefficient are from the **freestyle** extended WLS fit. Table 6 gives
  different coefficients and even different age-effect signs for other strokes.
  These associations do not establish muscle, endurance or developmental causes.
- Table 6 covers strokes other than IM, distances below 400 and SCY/LCM.
  IM, longer events and SCM were left for future work. It does not demonstrate
  a broadly validated conversion method for all events.
- The reported residual summaries are not a swimmer-disjoint, future-meet
  validation benchmark. The paper explicitly declines prediction intervals from
  its non-normal residuals. A parameter confidence interval is not a prediction
  interval for an individual swim.

The paper's Table 1 and the original converter/current TeamUnify documentation
also differ in some distance-event formulas. Pin an explicit source and edition
for each baseline; do not combine coefficients from different implementations
under one vague “Colorado Timing” label.

## Distribution-matching prior art

[Swimulator's January 2018 explanation](https://swimswam.com/swimming-real-time-converter/)
describes fitting skew-normal distributions by event, course, age and gender.
It maps a source time's percentile to the corresponding percentile in the
destination distribution. The author explicitly targets comparable competitive
standing across populations, rather than predicting the same swimmer's time.
The [current converter](https://swimswam.com/swimming-times-conversion-tool/?type=swimulator)
notes that 800 m/1000 yd uses an open-age conversion because age-specific data is
insufficient. These pages were checked October 20, 2026; data freshness and
current fitted parameters have not been established.

Include a distribution/percentile-matching baseline in the local experiment,
alongside NCAA, documented Colorado and linear/WLS baselines. Fit distributions
using training data only, and evaluate all eligible methods on the same held-out
pairs. Report competitive-equivalence diagnostics separately from individual
prediction errors. The original author also notes sparse-event coverage and
selection differences between course populations; a good distribution fit does
not establish individual predictive accuracy or calibrated prediction intervals.
This reference does not add their algorithm, parameters or data to Turnmark.

The article's four [published examples](../research/conversion-model/references/swimulator-2018.json)
are retained as illustrative elite-edge cases:

| Published input                   | Course comparison | Published equivalent |
| --------------------------------- | ----------------- | -------------------- |
| Simone Manuel · 100 Free · 45.56  | SCY → LCM         | 51.76                |
| Will Licon · 200 Breast · 1:47.91 | SCY → LCM         | 2:03.86              |
| Sarah Sjostrom · 100 Free · 51.71 | LCM → SCY         | 45.52                |
| Ryan Lochte · 200 IM · 1:49.63    | SCM → LCM         | 1:53.36              |

Licon's output is printed as `2:03:86` in the source; the fixture normalizes its
punctuation to `2:03.86` and preserves the literal. Ages/settings are not supplied.
These are historical outputs of an equivalence method, not observed target races
or accuracy labels. Do not require NCAA, Colorado or a learned predictor to match
them. Breaststroke, IM and SCM also sit outside the initial freestyle pilot.

## Points-equivalence follow-up

A same-score comparison is another research baseline, distinct from predicting
a swimmer's next performance. Keep the scoring system and edition explicit.
[World Aquatics](https://www.worldaquatics.com/swimming/points) publishes its cubic
formula and the inverse-time procedure, with separate SCM/LCM base times by
category and edition. It does not supply SCY base times or age-specific tables.
The existing World Aquatics scoring feature is not a USA Swimming Power Points
implementation. [USA Swimming's Data Hub overview](https://www.usaswimming.org/times/popular-resources/)
lists its Power Point Calculator, but that link alone does not establish a
versioned offline formula/table for Turnmark. Verify the authoritative parameters,
coverage and rounding before adding a USA Swimming points-equivalence method.
No additional points-based converter is shipped by this research note.

## Dataset acquisition

The first working source is [Pacific Swimming's publicly linked meet-result
exports](https://www.pacswim.org/swim-meet-results?year=2025). Downloading one ZIP
per meet gives substantially more useful records per request than profile-page
crawling. The local collector caches originals and metadata, spaces requests
10–14 seconds apart, uses one connection at a time, obeys robots decisions and
persistent per-origin budgets, and stops on access/rate challenges. Missing
404/410 files are logged as gaps and skipped. The collector itself is gitignored
under `research/conversion-model/local/`, as requested.

The adapter reads actual individual SDIF results, excludes seeds, splits,
relays, invalid times and ambiguous/missing full registration IDs, and keeps
whole-year ages without storing names or birth dates in normalized data. Full
source IDs are HMAC-pseudonymized with a local private key. Original archives can
contain identifying information and remain private. Duplicate exports of the
same logical race are deduplicated; conflicting results are excluded, not
resolved by selecting the faster result. Some SDIF files omit races present in
other formats: there is no claim of complete meet coverage.

A checkpoint of 106,053 usable races spans 80 meets, 2024–2026, both categories
and several meet levels. It is still one regional archive, with very little SCM
and adult coverage. Raw race count is not evidence of independent cross-course
training examples or national representativeness. The aggregate audit reports
empty cells, swimmer/meet counts and matched-pair coverage before model work.
No real data or source-specific scraper is part of this PR.

Other source leads and current outcomes:

| Source                                                                                                                                                                               | Research status                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [USA Swimming Data Hub](https://www.usaswimming.org/times/popular-resources/)                                                                                                        | Official results/rankings discovery and Power Point Calculator; no public bulk feed has been established for this project                              |
| [USA Swimming February 2026 notes](https://www.usaswimming.org/docs/default-source/technology/technical-release-notes/technical-release-notes-february-4-2026.pdf?sfvrsn=d5d21e32_1) | Confirms Snowflake-backed dashboards, not a public database connection or an enterprise API entitlement                                                |
| [Potomac Valley Swimming](https://www.pvswim.org/) and other LSC/organizer archives                                                                                                  | Public regional meet-result archives (SDIF `.sd3`/`.cl2` and Hy-Tek `.zip`); adapters verify each format and source before combining records            |

No contracted data feed, account session or owner outreach is required for the
current local pilot. Public accessibility does not itself establish permission
to redistribute records. Keep source URLs, retrievals, checksums and reuse notes;
do not claim a public training-data license. Preserve sources' actual coverage
and identity limitations rather than joining different providers by name.

The [local lakehouse experiment](MEET_LAKEHOUSE_EXPERIMENT.md) wires DuckDB,
Parquet, Iceberg snapshots and an indexed SQLite serving projection. It records
a possible inexpensive Cloudflare architecture without deploying it.

## Import and matching contract

Import actual individual race results, not seeds, converted times, qualifying
cuts, interpolated results or personal-best summaries. Retain source record and
meet IDs, course, actual event distance, stroke, published competition category,
date, time in integer centiseconds and result status. Disqualifications, DNS,
relays and relay splits are excluded from the initial pilot.

Use a stable source-scoped swimmer key for matching; names and full birth dates
are not model features. Pseudonymous keys remain linkable data, not a claim of
anonymity. Keep raw records and derived datasets outside version control and out
of app bundles. Capture source URL, retrieval date, input hash, permission/reuse
notes, and the age precision the source actually supplies. Do not fabricate
decimal age from a whole-year age or call it a measurement of maturation.

Pair the same swimmer, category and event family across courses within a fixed
initial 30-day window. Store both race dates and IDs, the signed date gap and the
matching policy. Avoid Cartesian all-pairs expansion and prevent a race from
appearing in several matched pairs. Report exclusions and sensitivity to the
matching window; even nearby races differ in taper, effort, injury and conditions.
Do not label a pair as a counterfactual ground truth or physiological potential.

## Evaluation before deployment

1. Freeze a deterministic swimmer-disjoint train/validation/test split. Every
   race, pair and reverse direction for one swimmer stays in one partition.
   Fit encoders and preprocessing on training data only; no swimmer ID as a
   predictive feature. Early stopping uses validation, never the test set.
2. Add a later-meet temporal evaluation, keeping both dates on the appropriate
   side of its cutoff. Report how many swimmers, meets and pairs remain. A random
   row split is unsuitable because repeated swimmers and races leak information.
3. Compare NCAA and the pinned Colorado baseline on exactly the same eligible
   test pairs. Include simple linear/WLS baselines before XGBoost. Report seconds
   MAE, median absolute error, signed bias and tail errors, plus relative error
   and coverage. Break out age, category, event, course direction, speed range
   and date-gap cohorts; publish counts and uncertainty rather than tiny-cohort
   leaderboards. Weight swimmers equally in a secondary summary.
4. Keep optional age missing when unknown. Category is the dataset's published
   competition table, not an inferred biological variable. Do not invent zero
   altitude for unknown pools or apply an official altitude correction twice.
   Initially omit altitude unless both source and destination metadata support
   a consistent definition. Age-group cutoffs are not physiological discontinuities.
5. Limit trees/depth and tuning budget, fix seeds and versions, and export the
   [supported JSON/UBJSON model format](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html).
   The proposed depth-7/1,000-tree configuration is a hypothesis, not an optimum.
   [Quantile objectives](https://xgboost.readthedocs.io/en/stable/python/examples/quantile_regression.html)
   can cross and do not by themselves establish calibrated individual coverage.
6. No “95% of equivalent swimmers” or confidence tier without a separate
   calibration set and measured held-out coverage, including cohort checks.
   Reserve the test set from model selection and calibration. Point predictions
   and empirical prediction intervals must be labeled distinctly from entry rules.

## Client-side feasibility gate

Do not migrate the production core to an experimental predictor. First measure
an offline Python model. If it improves meaningful held-out metrics, evaluate a
small generated Rust representation or a validated tree interpreter with no
network dependency. Preserve feature order, missing branches, comparison
semantics, base score, objective transform and early-stopping tree range.

The pasted example is illustrative code, not trained XGBoost inference; its
leaf adding a multiple of the input is not an ordinary constant-leaf tree.
Do not assume m2cgen supports Rust or that a compiler handles every XGBoost
feature. Choose an exporter only after checking current supported targets.
Compare Python/native/Wasm predictions on missing values, boundary inputs and
held-out rows, then measure artifact size, startup, latency and memory on actual
target devices. No model artifact belongs in production until those gates pass.

Stop after a bounded pilot if usable data access is unavailable or the model
does not improve held-out errors enough to justify maintenance. An honest
method comparison is useful even when NCAA or Colorado wins.

## Comparing methods and uncertainty in a future UI

A future comparison may show NCAA, documented Colorado and an experimental
predictor together. Keep NCAA as the default and put the method choice in a
quiet setting. A user following a meet's published conversion policy can select
that method explicitly; do not imply that a calculator certifies entry
acceptance. The experimental predictor is for exploratory performance guidance.
Original-course actual swims remain the basis of published benchmark comparisons.

If a model earns an uncertainty display, call it a prediction range for a future
comparable swim, not a confidence interval for the fitted mean. Estimate and
validate coverage on swimmer-disjoint and later-meet holdouts, including age,
category, event, speed, region and season subgroups. Quantile or residual-based
methods are candidates, not a promised calibrated output. A Monte Carlo
simulation can propagate an empirically justified error model; randomly sampling
converter disagreements or invented Gaussian noise cannot establish coverage.
Do not add a 95% label until actual out-of-sample coverage supports it. Outside
trained coverage, show unavailable or the explicitly selected standard method.
