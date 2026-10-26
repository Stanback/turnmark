# Category evidence-sharing experiment

October 26, 2026. Research only; no production snapshot, bindings, defaults or
consumer behavior changed. The experiment does not establish a better replacement
for the shipped model.

The committed [aggregate receipt](sharing-experiment-01.json) records all validation
settings, the frozen shortlist, held-out results and invented query probes. It
omits the full validation subgroup tables available in the local output.

## Question and design

Does pulling men's and women's estimates toward a pooled event estimate suppress
useful category differences? Vary that sharing while retaining the current pairing,
noise estimates, event-to-geometry regularization, course reconciliation and
hundredth truncation.

[`sharing_experiment.py`](sharing_experiment.py) independently multiplies the
category prior's precision for level and log slope by
`0, 0.1, 0.25, 0.5, 1, 2, 4, 10, infinity`: **81 combinations**. One reproduces the
current fit; zero uses the raw category estimate where one exists. Infinite prior
precision uses the pooled event parameters but retains category-specific centers.
A separate **82nd control** removes category centers too and uses a common event
curve and pooled support for both categories. Thus that control actually returns
the same conversion for men and women at the same entered time.

The training data and its SHA-256 are checked against evaluation checkpoint 08.
The reconstructed baseline's exported cells must exactly equal the shipped
`data/empirical.json`, and vectorized predictions must match every scalar baseline
prediction on validation and main test swimmers.

All 81 settings are compared on 41,464 validation conversions. Before candidate
test scoring, the script writes a frozen shortlist: the three lowest overall
validation MAEs, category-specific validation winners, and predeclared endpoint
and one-parameter controls. The common-curve endpoint is an additional diagnostic
control, not a candidate selected by test performance. No settings are chosen per
event or from test results. For the harder holdouts, each configuration is refitted
on that holdout's existing training split.

## Results

Average absolute error, seconds; lower is better:

| Setting | Validation | Main test | Later-season test | Regions held out |
| --- | ---: | ---: | ---: | ---: |
| Current sharing (`1, 1`) | 2.717701 | **2.771090** | **2.970586** | 3.137734 |
| No category shrinkage (`0, 0`) | 2.728731 | 2.775502 | 2.984357 | 3.149313 |
| Validation winner (`4, 10`) | **2.715088** | 2.771877 | 2.970993 | **3.135407** |
| One common event curve | 2.718275 | 2.774387 | 2.976008 | 3.137566 |

The no-shrinkage setting is worse on all three test sets, by 0.0044, 0.0138 and
0.0116 seconds. The validation winner improves validation by just 0.0026 seconds;
on the main test it is 0.0008 seconds worse, with a swimmer-bootstrap 95% interval
for that difference of [-0.0017, +0.0030]. It is also essentially tied on the
later-season test. Its regional gain is 0.0023 seconds, concentrated in men; that
single holdout does not establish an overall improvement.

Removing category shrinkage raises main-test MAE by 0.0033 seconds for men and
0.0054 seconds for women. On the regional holdout those increases are 0.0143 and
0.0094 seconds. There is no aggregate indication that the current sharing is
harming one category while helping the other. This does not exclude local
category/event/pace weaknesses.

More sharing also produces event tradeoffs. For the validation winner on the main
test, women's 200 breast MAE increases by 0.0172 seconds and women's 200 fly by
0.0117; men's 200 fly improves by 0.0088. The longest freestyle has much larger
changes in opposing directions but just 42 men's and 24 women's test conversions.
Those small cells do not justify event-specific tuning.

## Does sharing create the near-equal category outputs?

These are invented query times, not individual swimmer records. Every output is
SCY to LCM, seconds, truncated by the model's normal arithmetic:

| Entered event/time | Current men | Current women | No-shrinkage men | No-shrinkage women |
| --- | ---: | ---: | ---: | ---: |
| 100 free, 70.00 | 80.10 | 80.19 | 80.13 | 80.21 |
| 100 back, 75.00 | 87.08 | 87.29 | 87.12 | 87.32 |
| 200 breast, 135.00 | 159.98 | 159.75 | 160.24 | 159.51 |
| 200 fly, 150.00 | 176.36 | 175.10 | 177.25 | 175.29 |

Similarity persists without category shrinkage, especially in the well-covered
100 free and 100 back. Pooling narrows some differences, particularly 200 breast
and 200 fly, but does not account for the whole pattern. These probes hold clock
time fixed, not age or competitive standing, and do not establish a physiological
explanation. The category-independent noise estimates and modeling assumptions
remain in place even in the no-shrinkage setting.

## Interpretation and limits

Keep the current settings. They are in a broad, nearly flat region of performance;
neither removing category sharing nor increasing it establishes a worthwhile,
consistent improvement. Retaining some sharing and some category-specific
information is supported by this experiment, without establishing that the current
strength is optimal.

The bootstrap uses 2,000 swimmer resamples with fitted models held fixed. Intervals
and normal-approximation p-values in the receipt are unadjusted for multiple
comparisons and do not include refitting or selection uncertainty. The existing
test sets have been examined in earlier research; validation-only selection here
does not make them newly untouched data. The original youth-heavy, sparse-SCM,
source-scoped identity and thin elite-distance limitations all remain. Errors
combined across both directions can hide signed bias; the receipt includes
direction-specific metrics and these aggregate tables should not be read as a
calibration claim within every category/event/pace cell.

## Reproduce and inspect

```sh
target/lakehouse-py312/bin/python -m unittest discover \
  -s research/conversion-model -p test_sharing_experiment.py -v
target/lakehouse-py312/bin/python research/conversion-model/sharing_experiment.py
```

The local pinned lakehouse is required. The script writes an aggregate
[`receipt.json`](../../target/sharing-experiment/receipt.json) and validation-only
[`selection.json`](../../target/sharing-experiment/selection.json) under ignored
`target/sharing-experiment/`. A private fitted-object cache in that same ignored
directory contains swimmer-level pairs and must remain local. Neither the script
nor this report publishes those rows.
