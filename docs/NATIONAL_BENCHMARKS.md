# National meet and high-school benchmarks

Turnmark bundles three additional source-backed benchmark programs for offline
comparison with the original entered swim. These are time comparisons, not a
meet-entry service or an award determination.

| Program                              | Edition   | Published individual-event coverage   | Selection                                          |
| ------------------------------------ | --------- | ------------------------------------- | -------------------------------------------------- |
| TYR Futures Championships            | 2027      | 17 events; SCY / LCM; women / men     | Separate 18 & under and 19 & over tables           |
| Speedo Junior National Championships | 2027      | 17 events; SCY / LCM; women / men     | Main standards; bonus and relay standards excluded |
| NISCA Swimming All-America           | 2026–2027 | Eight events; SCY / SCM; girls / boys | Consideration and All-America time thresholds      |

The 236 records contain 268 time thresholds. Unsupported courses/events stay
unavailable. Destination estimates are never substituted for a missing target.
Futures’ two age tables have different qualifying windows in the source; the UI
asks which table to compare, and does not infer an athlete's eligibility from an
age-group setting. NISCA requires a completed application and an eligible
interscholastic performance, among its other rules; meeting a time does not grant
an award.

The shared Rust `benchmark` operation / typed `assess_swim_benchmark` now accepts
`futures`, `juniors` and `nisca` alongside `youth` and `masters`. Futures requires
age `18 & under` or `19 & over`; Juniors and NISCA are not age-group lookups and
use an empty age string. `get_national_standard_programs` provides shared program
labels, scope, age choices and coverage notes. The JavaScript SDK exposes the
same metadata through `getNationalStandardPrograms` after initialization.

Web and native Standards selectors expose these programs without adding another
home-screen card. Native preferences retain Futures' table independently of youth
and Masters ages. Web preferences/share links retain the selected program and
Futures table. The read-only MCP `assess_swim_benchmark` tool returns the same
structured outcome and provenance; it has no access to personal history.
The standalone widget remains a course-conversion embed, without a benchmark UI.

## Sources and maintenance

- [USA Swimming's official standards index](https://www.usaswimming.org/Times/time-standards)
  links the pinned 2027 Futures and Junior National documents.
- [NISCA's official time standards](https://niscaonline.org/index.php/award-programs/all-america-swimming/aa-time-standards)
  link the pinned 2026–2027 yards/meters documents and the
  [All-America rules](https://niscaonline.org/images/Documents/AllAmerica/Swimming/AASwimRules.pdf).
- [Data maintenance](DATA.md#national-meet-and-high-school-benchmarks) describes
  the small reviewed transcription, importer guards, source fingerprints and
  edition update process. There is no live scraping in the shipped application.

USA Swimming Power Points and NISCA Power Points remain research candidates.
No custom-target, ranking percentile, new points formula or predictive model is
included in this addition.

## Visual review

Actual app and browser captures use sample swims only:

- [Web Futures, dark](screenshots/web-futures-dark.png) and
  [phone, light](screenshots/web-futures-light.png).
- [Web NISCA, dark](screenshots/web-nisca-dark.png) and
  [phone, light](screenshots/web-nisca-light.png).
- [iOS Futures](screenshots/ios-futures-benchmark.png) and
  [NISCA thresholds](screenshots/ios-nisca-thresholds.png).
- [Android Futures](screenshots/android-futures-benchmark.png) and
  [NISCA thresholds](screenshots/android-nisca-thresholds.png).
