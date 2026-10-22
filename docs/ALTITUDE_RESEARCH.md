# Altitude policies and an empirical research track

Policy sources checked October 19, 2026. **The empirical altitude study remains
research, not a validated predictive model.** Both published altitude policies
are now implemented in Turnmark; [the current altitude contract](ALTITUDE.md)
records the shipped behavior. The implementation design below is retained as
its rationale. NCAA remains the
default _course conversion_ method; altitude policy is a separate choice.

## Verified policy baselines

USA Swimming still links its April 14, 2022 **Times & Recognition Policy Manual**
from its [Times index](https://www.usaswimming.org/times/). Section 4.7, printed
page 7, contains the posted table. The retrieved manual is not dated January 2013. [Official PDF](https://www.usaswimming.org/docs/default-source/timesdocuments/general-docs/times-and-recognition-policy-manual.pdf#page=7).

The **2026–27 NCAA Division I qualifying document**, PDF page 3, and **Division II
men's document**, PDF page 2, publish the same altitude values. These are
championship-specific sources, not proof that every meet accepts these policies.
[Division I](https://ncaaorg.s3.amazonaws.com/championships/sports/swimdive/d1/2026-27D1XSW_QUALSTANDARDS.pdf#page=3) ·
[Division II](https://ncaaorg.s3.amazonaws.com/championships/sports/swimdive/d2/2026-27D2MSW_QualStandards.pdf#page=2).

Deductions below are seconds from the original swim, not percentages:

| Individual event distance | Policy       | 3,000–4,250 ft | 4,251–6,500 ft | Above 6,500 ft |
| ------------------------- | ------------ | -------------: | -------------: | -------------: |
| 100 yd/m                  | USA Swimming |     Not listed |     Not listed |     Not listed |
| 100 yd/m                  | NCAA         |           0.00 |           0.10 |           0.15 |
| 200 yd/m                  | Both         |           0.50 |           1.20 |           1.60 |
| 500 yd / 400 m            | Both         |           2.50 |           5.00 |           7.00 |
| 1000 yd / 800 m           | USA Swimming |           5.00 |          10.00 |          15.00 |
| 1000 yd / 800 m           | NCAA         |           6.30 |          11.40 |          18.50 |
| 1650 yd / 1500 m          | USA Swimming |          11.00 |          23.00 |          32.50 |
| 1650 yd / 1500 m          | NCAA         |          11.00 |          20.00 |          32.50 |

USA Swimming separately lists an 800 freestyle relay adjustment of
2.00/4.80/6.40s. NCAA specifies relay adjustments as four times the appropriate
individual allowance. The app's individual-swim type cannot represent a relay;
do not apply the individual 800 allowance to an 800 relay. Neither table
personalizes by swimmer age, category, acclimatization or training history.

USA Swimming distinguishes entry/seeding adjustments from records and
recognition. The NCAA documents also carry course and entry constraints.
Display the policy and edition; never turn a sea-level estimate into an official
performance, personal best, or blanket statement of entry eligibility.

Source checksums (SHA-256, retrieved October 19, 2026):

- USA Swimming: `959fa9f6ea29e067204be86864dd9559e9383122d43c392606029e60a06f1b0b`
- NCAA Division I: `259c76ba10df6f72314a677df6aea1becc6d7d9b4400b5f0f95d4d33e88bf7ab`
- NCAA Division II men: `5864b9e84fdd2eed08d2e0283e2bc1424e7293a5be87636a08b295549d844852`

The downloaded tables were checked as rendered PDF pages, not just extracted
text. Keep policy snapshots separate from official course-conversion factors.

## UI and engine contract (now implemented)

- Keep **Altitude adjustment** optional and initially off. Keep USA Swimming as
  its existing default; selecting NCAA/Colorado course conversion must not
  silently switch the altitude policy.
- Show original clock, entered elevation and unit, selected altitude policy,
  deduction, and resulting same-course sea-level estimate. In expanded detail,
  show USA Swimming and NCAA side by side with the same original input. Call
  their gap a **policy difference**, not an accuracy or uncertainty range.
- Then convert the selected sea-level estimate using the selected course
  method. Quietly compare NCAA and Colorado against that _same adjusted input_;
  do not mix changes in altitude policy and course method into a single gap.
- Preserve unsupported events, explicit zero allowance, below-threshold
  elevation, invalid input and unavailable policy outcomes as distinct states.
  Source tables use integer-foot labels with a 4,250/4,251 boundary. Specify and
  test fractional feet, meter conversion and exact boundaries explicitly;
  do not imply the source specifies a rounding convention it does not give.
- Apply each supported adjustment once. Reject nonpositive adjusted clocks;
  preserve source and rounding provenance. Show the raw and adjusted clock in
  exports/share context. Benchmarks stay tied to the original swim unless a
  separately labeled, policy-specific entry-preparation workflow is added.
- Numerical rules live in Rust with source metadata and fixtures. Add one
  shared policy API, regenerate native bindings, and implement native, web,
  widget and MCP presentations using returned outcomes. Do not maintain
  independent UI coefficient tables. Test disagreement examples, boundary
  elevations, course/distance mapping and unchanged original performances.

There is also an important _course-conversion_ distinction: the 2027 Division I
qualifying document explicitly overrides the generic NCAA rulebook's SCM-to-SCY
factors (for example 0.906 rather than 0.896 for other events). This is not an
altitude difference. Keep the existing generic rulebook method accurately named;
consider a separately editioned championship policy only after scope and
maintenance review. A generic “Meet entry mode” would hide this distinction.

## Is an empirical altitude model feasible?

It is a reasonable local research question, not an assumption of improvement.
First audit how many independent swimmers and meets actually have verified
facility elevation and nearby-date swims across elevations. One million race
rows do not establish useful high-altitude coverage. Do not infer a pool's
height from a club's mailing address or a meet's name; retain facility/date
resolution, elevation source, precision and missingness. Do not silently treat
missing elevation as sea level.

Start with **same-course, same-event** matched swims across elevations so course
conversion does not confound the first altitude experiment. Keep race dates,
age precision, competition category, event, clock, verified facility elevation,
meet identity and timing/result status. If observed reliably, separately record
start type, prelim/final/time-trial round and indoor/outdoor venue. Keep relay
splits, disqualifications, seeds and already-adjusted clocks out of the pilot.
Do not fabricate acclimatization, travel, taper, training load, illness, water
temperature or physiological traits from absent data.

Compare no correction, both applicable published policies, and a simple
regularized baseline before boosted trees. Test policy residual correction as
well as direct prediction; avoid double-correcting the target. Cluster by
swimmer and meet, with distinct swimmer-disjoint and future-meet/region holdouts
and a separate calibration set. Freeze the split and matching rules before
model selection. Sparse elevation/event/category cohorts should abstain rather
than borrow a confident-looking interval from a different population.

Report original/adjusted sample counts, independent swimmers and meets, paired
date gaps, errors in seconds and relative error, signed bias by elevation and
event, and sensitivity to matching windows and repeated-race weighting. Keep
same-meet and swimmer leakage out of evaluation. Observational associations are
not causal effects of altitude: training progress, selection, travel and
acclimatization can remain unobserved confounders.

Only display an empirical prediction interval after checking its coverage and
width on untouched swimmers and later meets, including the supported elevation
cohorts. Cluster-aware bootstrap or conformal/quantile approaches are candidates
to evaluate, not a promised confidence percentage. Monte Carlo simulations are
useful sensitivity tools but cannot establish calibration by themselves.
If evidence is insufficient, publish the coverage audit and retain the policy
comparison without a model. No new user input, model artifact, or inference
runtime belongs in production before that evidence exists.

This is part of the [local conversion-model research](CONVERSION_RESEARCH.md).
Raw results, linkage keys, facility-enrichment datasets and trained artifacts
remain gitignored. The public contribution is the protocol, source provenance,
synthetic fixtures and aggregate findings; no hosted results service is planned.

The [venue sidecar and cohort audit](VENUE_RESEARCH.md) now provide the first
implemented metadata layer for this research. They do not change clocks, train
an altitude model or turn a missing pool location into a sea-level assumption.
