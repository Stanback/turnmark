# Benchmark expansion shortlist

Updated October 19, 2026. Futures, Junior Nationals and NISCA All-America
time thresholds are implemented in the [national benchmarks follow-up](NATIONAL_BENCHMARKS.md).
Custom targets and additional points systems remain candidates. Existing USA
Swimming youth standards, USMS NQTs and World Aquatics points remain available.

## Small additions with a useful payoff

| Candidate                     | Why it is useful                                                                        | Maintenance and recommendation                                                                                                                                                     |
| ----------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Custom target time            | A local meet cut, personal goal or coach-supplied target without maintaining every meet | Lowest data maintenance. One explicit time/course/event context; store locally if desired. Label it user-provided, never official by inference                                     |
| USA Swimming Futures          | A recognizable national-meet benchmark beyond the motivational ladder                   | Bundled 2027 individual-event tables; separate 18-and-under / 19-and-over cuts, with source editions and missing-event handling                                                    |
| USA Swimming Junior Nationals | A further national threshold in the same publisher's standards index                    | Bundled 2027 main individual-event standards; bonus and relay standards excluded. Winter Juniors remains a separate unbundled edition                                              |
| NISCA All-America standards   | A useful high-school comparison                                                         | Bundled 2026–2027 SCY/SCM individual-event thresholds. Consideration and All-America time columns remain distinct; a time does not itself award status                             |
| USA Swimming Power Points     | Another way to compare performances; possibly the “national points” mentioned           | Investigate next. The official Data Hub lists a calculator, but an authoritative versioned offline table/formula and reproducible examples have not yet been verified for Turnmark |
| NISCA Power Points            | High-school event-quality scoring, distinct from USA Swimming and World Aquatics points | Later candidate after validating the official table edition, scope and reproducible scoring behavior                                                                               |

Official sources:

- [USA Swimming time-standards index](https://www.usaswimming.org/Times/time-standards)
  lists 2026 and 2027 editions, including Futures and Junior Nationals. Import
  a specific reviewed edition, not “the latest” guessed from a URL.
- [USA Swimming Data Hub](https://www.usaswimming.org/times/popular-resources/)
  lists its Power Point Calculator. A hosted calculator is not itself an offline
  implementation contract; do not infer its formula from another website.
- [NISCA All-America time standards](https://niscaonline.org/index.php/award-programs/all-america-swimming/aa-time-standards)
  requires a completed application in addition to an appropriate performance.
  Preserve that distinction in labels and links.
- [NISCA National Dual Meet rules](https://www.niscaonline.org/images/Documents/AllAmerica/NatlDualMeet/Power_Point_Rules.pdf)
  describes its Power Point tables and high-school scope. The linked document
  references a 2014 table edition; confirm the current applicable scoring source
  before implementing anything.
- [USA Swimming IMX/IMR](https://www.usaswimming.org/times/imx-imr) combines a
  program of events. It is not a replacement score for one entered swim and
  would add unnecessary workflow/storage scope at this stage.

Do not start by maintaining all state, sectional, zone, team and meet cuts.
A custom target covers those cases without a sprawling source list. Historical
rank percentiles and age-graded adult ladders would need their own defensible
dataset/methodology and maintenance; they are not cheap static add-ons.

## USA Swimming Power Points source check

Checked October 19, 2026. The official [Data Hub index](https://www.usaswimming.org/times/popular-resources/)
lists a Power Point Calculator. The older
[calculator route](https://data.usaswimming.org/datahub/powerpointcalculator)
redirected to the new Programs calculator route; an anonymous browser session
showed a login prompt rather than a downloadable scoring table. No versioned
offline numerical table or complete formula was verified in this check.

[HY-TEK's own documentation](https://hytek.active.com/user_guides_html/swmm7/hy-tekpoints.htm)
distinguishes age-group, single-year and open point systems. These are not
interchangeable with World Aquatics points, and that description alone does not
provide the coefficients needed to reproduce USA Swimming's current calculator.
Do not substitute World Aquatics' cubic formula or infer scores from the B–AAAA
motivational ladder.

Before implementation, obtain an attributable table/formula with a known edition,
confirm event/course/age coverage, and verify boundary and rounding examples
against the official calculator. The absence of a verified source in this search
does not establish that no suitable archived or publisher-provided table exists.
USA Swimming Power Points remain unimplemented; this research does not add an
online dependency or send entered swims to an external service.

## Keep the interface small

Show one appropriate next target, not every possible achievement at once.
Use a standards picker for the full set. Keep the original entered event,
course, category and relevant age context visible; do not treat a converted
estimate as an actual qualifying swim. For points, retain an explicit scoring
system/edition label. Different point systems are not interchangeable scores,
percentiles or predicted chances of qualifying.

Future method comparison can show NCAA, Colorado and a separately validated
experimental predictor. Following a meet's required conversion policy and
exploring a likely performance are different tasks. No model confidence graphic
or new meet-eligibility claim belongs in the layout exploration.

## Update process before more tables

Reuse the existing checked-in snapshot/importer pattern in [DATA.md](DATA.md):
official source URL, edition/validity dates, retrieval date, content SHA-256,
schema version, validated event/course/category keys and explicit nulls.
Independent sample values, duplicate detection and row/header guards should make
unexpected PDF changes fail visibly. Keep old editions reproducible.

A later scheduled job can check source indexes and fetch changed documents,
produce a source/value diff, run import validation and prepare a reviewable PR.
It should not silently promote a new edition, merge its own changes or deploy
unreviewed numbers. Source-fingerprint changes sometimes reflect layout only;
validity and edition changes also need UI metadata updates. No automated source-promotion cron is implemented. The national benchmark
addition uses a reviewed static snapshot and an explicit importer.
