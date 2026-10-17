# Methodology

Source review: October 16, 2026. Turnmark provides perspective for training and planning. Meet organizers determine accepted entry times and conversion methods.

## Course conversion

Factors are transcribed from **Appendix C, printed page 120** of the [NCAA 2025–26 and 2026–27 Swimming and Diving Rules Book](https://ncaaorg.s3.amazonaws.com/championships/sports/swimdive/rules/PRXSW_RulesBook.pdf#page=125), updated October 1, 2026. Source metadata and SHA-256 are recorded in `data/sources.json`; factors live in `data/conversions.json`.

NCAA publishes metric-to-short-course-yards factors. Long-course factors vary by event and published men/women table. Short-course factors are shared between categories. Turnmark applies the same published table labels; these are calculation categories, not a determination of athlete eligibility.

| Direction        | Calculation                                                 | Label                |
| ---------------- | ----------------------------------------------------------- | -------------------- |
| SCM or LCM → SCY | Multiply by the published event factor                      | Published factor     |
| SCY → SCM or LCM | Divide by the target course’s factor                        | Derived estimate     |
| SCM ↔ LCM        | Multiply by source-to-yards factor / target-to-yards factor | Derived estimate     |
| Same course      | Retain the input (or explicitly altitude-adjusted input)    | Your swim / adjusted |

Reverse directions and cross-metric ratios are Turnmark’s derivations, not separately published NCAA tables. Each result exposes its multiplier. No intermediate course result is rounded or truncated; only the final displayed converted time is truncated to hundredths, following the NCAA instruction to drop smaller units. A small epsilon corrects floating-point representation only. The unit test reproduces the NCAA example: 2:16.71 men’s 200m long-course breaststroke → 1:57.29 short-course yards.

The corresponding distance events are 400m ↔ 500yd, 800m ↔ 1000yd, and 1500m ↔ 1650yd freestyle. Other distances retain their numerical distance. The interface updates the distance label when changing courses.

No LCM factor is invented for 50 backstroke, breaststroke, or butterfly. Those course conversions are unavailable, while SCY ↔ SCM remains supported. The 100 IM is unavailable in LCM. Missing standards and factors are left blank with an explanation.

Pool lengths/turn counts describe the selected event’s geometry. The displayed pace is an even average per 100 units, not a race split prediction. Turns, underwater skill, fatigue, starts, age, and other individual differences are not modeled.

## Motivational standards

The [USA Swimming 2024–2028 Motivational Standards](https://www.usaswimming.org/docs/default-source/timesdocuments/time-standards/2025/2028-motivational-standards-age-group.pdf), revised **October 10, 2025**, supplies 482 individual-event/category rows, each containing B, BB, A, AA, AAA, and AAAA: **2,892 published times**.

Coverage: SCY, SCM, LCM; 10 & under, 11–12, 13–14, 15–16, and 17–18; the published girls/boys categories. Relay rows are excluded. Not every event is published in every age group. Adult swimmers can use the converter; the age-group ladder is for the listed youth age groups and must not be presented as an adult benchmark.

Girls’ columns run B → AAAA in the source PDF; boys’ columns run AAAA → B. The importer normalizes both into B → AAAA, validates six strictly decreasing thresholds per row, and rejects duplicate keys and unexpected revisions. Tests check independent PDF cells, count, ordering, boundaries, and missing data.

The ladder uses the entered course. Converted results are never silently treated as an actual swim for standards. A time equal to a standard meets that level; the next goal is the next faster standard. Ladder marker positions interpolate between neighboring published thresholds. The marker is kept inside the track at its extremes; exact level and next-goal text remain authoritative.

## Masters standards

The [official USMS National Qualifying Times page](https://www.usms.org/events/national-championships/pool-national-championships/national-qualifying-times), checked October 16, 2026, publishes 2026 Spring Nationals SCY and Summer Nationals LCM tables. Turnmark includes both published categories and 13 age groups from 18–24 through 80–84: 70 event/category rows and 904 numeric targets. Six NO TIME cells remain null. USMS states there are no NQTs for ages 85+; the UI explains that rather than inventing a cutoff. No SCM NQT is inferred from a conversion.

Adult comparisons use the raw entered swim, not NCAA course estimates or USA Swimming altitude-adjusted times. The UI reports seconds above/below the published NQT and labels the year. Meeting a displayed benchmark does not confirm entry eligibility: the qualifying window, meet rules, distance exceptions, and any additional conditions must be checked with USMS. This dataset is not an adult motivational ladder. Youth and adult standards selection, including the adult age group, round-trip through shared links and saved/history entries.

## World Aquatics points

Points are a separate way of comparing performances across events, using [World Aquatics’ cubic formula](https://www.worldaquatics.com/swimming/points): `floor(1000 × (base / enteredTime)^3)`. A floating-point epsilon of 1e-9 corrects representation at exact integer boundaries. Scores may exceed 1,000; they are not capped or interpreted as age-group rankings.

The [official 2026 base times PDF](https://resources.fina.org/fina/document/2026/09/05/9b48fb98-233c-4ce9-b67b-bc6163319bbd/Points-Base-times-SCM-and-LCM-2026_09.2026.pdf) supplies 35 individual events across two published categories, or 70 base times. SCM validity is September 1, 2026–August 31, 2027; LCM validity is January 1–December 31, 2026. These are fixed, labeled snapshots, not live records. The importer excludes relays and verifies the clock-formatted and seconds-formatted columns agree. Source metadata and fingerprint live in `data/points.json`.

Points use the entered metric course and raw time, without altitude correction. Yards swims and unsupported events remain unscored. Course estimates are not silently scored as actual performances. World Aquatics points are open scoring, not an age-adjusted or Masters benchmark. The points view shows the 1,000-point base and the next 100-point training milestone. Its target is the slowest whole hundredth at or faster than the cubic threshold for that score; it is derived locally and labeled as a milestone, not a separate published qualification. Tests verify that the target meets the milestone and the following hundredth does not. No rankings, percentiles, age-adjusted performance categories, relay scoring, or live records comparisons are inferred.

## Altitude

Optional corrections follow [USA Swimming’s Times and Recognition Policy Manual §4.7](https://www.usaswimming.org/docs/default-source/timesdocuments/general-docs/times-and-recognition-policy-manual.pdf#page=7), verified October 16, 2026.

For eligible individual-event distances of 200, 400/500, 800/1000, and 1500/1650, subtract the published band adjustment from the original time before course conversion. Elevation bands are 3,000–4,250 ft, 4,251–6,500 ft, and above 6,500 ft. Feet are the default elevation unit. Meters use exactly 0.3048 m per foot and are rounded to the nearest whole foot on entry to select the published elevation band. Switching display units preserves the stored feet value, so repeated switches cannot move an elevation into another band. Links, saved swims, history, and CSV exports continue to use canonical feet. Altitude at 6,500 ft remains in the middle band. No adjustment is applied below 3,000 ft or to sprint events. Source-course results and standards comparisons are labeled as altitude-adjusted when a correction is applied. These adjustments are not for record or recognition purposes; verify the entry process with the meet.

## Privacy

The app makes no runtime requests to source organizations. Its service worker caches public static assets for offline use; user inputs are not included in cache requests. Appearance preferences are saved locally, with Auto following the system setting. Data, fonts, icons, and calculations ship with the static build. After a valid edit settles for 1.4 seconds, the conversion is recorded in device-local history, capped at the most recent 50 entries. Merely opening the default or a shared swim does not create an entry. Each entry retains event, source course, focused target course, input time, category, age group, elevation, and a timestamp. Restoring history does not add a duplicate. History supports per-entry removal and clearing, and never syncs between browsers. Save swim keeps an additional explicit collection of at most eight distinct swims. Copy link uses the URL fragment and clipboard; CSV export creates a device download. Browser storage can be blocked or cleared. Following a source link opens that organization’s website. No analytics or user accounts are included.
