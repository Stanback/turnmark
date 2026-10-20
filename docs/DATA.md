# Updating source data

The app uses checked-in numeric snapshots, with attribution and retrieval metadata. There is no live scraping or external API dependency in the shipped app.

## USA Swimming motivational standards

1. Visit the [official standards index](https://www.usaswimming.org/Times/time-standards) and confirm the current cycle, revision, and official PDF URL.
2. Install Poppler (`brew install poppler` on macOS).
3. Run `npm run data:refresh`. To reproduce a downloaded version: `python3 scripts/import-standards.py --pdf /absolute/path/source.pdf`.
4. The importer intentionally fails if the October 10, 2025 revision or the expected 482 individual-event/category rows changes. Review the new PDF before updating those guards.
5. Render and inspect representative pages from each course; verify age headers, both category column orders, distance mappings, missing events, and every amended value. Compare generated JSON against the prior snapshot. No PDFs are redistributed in this repository.
6. Update source dates and user-facing counts/cycle labels if they change. Run the checks and tests.

The generated `data/standards.json` records the source URL, revision, retrieval date, SHA-256 fingerprint, scope, level order, and 482 records. Each record’s six times are seconds in B → AAAA order. Stars in the source are not part of numeric time values.

## NCAA factors

1. Check the [official NCAA swimming rules page](https://www.ncaa.org/championships/playing-rules/swimming-and-diving-playing-rules/) for the current rules book.
2. Inspect Appendix C’s conversion tables, directions, factor categories, event coverage, and truncation instructions.
3. Update `data/conversions.json` and the source fingerprint in `data/sources.json`.
4. Add a published numerical example to the tests if the calculation changes. Never infer a missing event factor from a nearby event.

## Colorado Timing formulas

1. Review the **USA Swimming teams** section of [SportsEngine Motion / TeamUnify’s course-conversion documentation](https://motion-help.sportsengine.com/en/articles/8538107-how-to-perform-course-conversion-factoring-of-times). The pinned edition is August 6, 2026, checked October 19, 2026.
2. Save the source HTML outside the repository and calculate its SHA-256. Update `data/colorado.json` with the URL, edition, retrieval date, fingerprint and coefficients. The current HTML fingerprint is `933f228ae997a727a26798188a3497fd21955323a72d531881596da129aa76d6`; a changed page needs review, not an automatic coefficient update.
3. Check every direction separately, particularly the long freestyle exceptions. Do not mix in the non-USA-team formulas, route via an intermediate course or infer an absent 100 IM formula. See [methodology](METHODOLOGY.md) for the complete implemented rules.
4. Update independent fixtures in `fixtures/sdk-conformance.json`, regenerate SDK/native artifacts, and check native/Wasm parity. Preserve the omitted-method NCAA default and its existing results. Source metadata is generated for SDK consumers from this snapshot.

## World Aquatics points

1. Check [World Aquatics’ official points page](https://www.worldaquatics.com/swimming/points) for the current base-times PDF and its separate SCM/LCM validity dates.
2. Run `npm run data:points`. The importer fetches the pinned official PDF, uses Poppler to extract its numeric columns, verifies both time representations, rejects duplicates, and requires 35 individual events (70 category-specific base times).
3. For a future edition, review the PDF and update the URL, validity guards, source dates, labels, documentation, and tests together. Do not simply substitute current world records; the scoring base times have their own validity periods.
4. Verify all 70 base times score 1,000 and independent slower/faster samples follow the published cubic formula and truncation. There is no yards points table and no implicit scoring of course-converted estimates.

## Altitude

Check USA Swimming’s Times & Recognition Policy Manual §4.7 and the pinned NCAA 2026–27 Division I qualifying document, page 3. The [altitude contract](ALTITUDE.md) records editions, individual-event scope, ranges, boundaries and calculation order. Review source metadata, both numeric tables and cross-runtime boundary/composition fixtures together. Never change course factors merely because an altitude edition changed.

Run `npm run check`, `npm test`, `npm run test:browser`, and `npm run build` before publishing a data change.

## U.S. Masters Swimming targets

`npm run data:masters` fetches the official USMS NQT page with curl and extracts its first four 2026 tables. Exact headings, course/category order, 13 published age columns, row counts, unique event keys, and numeric cell formats are validated. The checked-in snapshot contains 70 event/category rows and 904 numeric targets. Six source cells say NO TIME and stay null. Source URL, checked date, year, and the source HTML SHA-256 are stored in `data/masters.json`.

Review a newer edition before changing importer guards. Ages 85+ have no USMS NQT; SCM has no target in these Nationals tables. Never infer those missing values, interpolate adult age groups, or generate an adult B–AAAA ladder from NQTs. The UI uses the entered course/time and does not apply NCAA course estimates or USA Swimming altitude corrections to adult eligibility comparisons. USMS entry guidance and event exceptions remain authoritative.

## National meet and high-school benchmarks

`python3 scripts/import-national-standards.py` builds `data/national-standards.json`
from the reviewed numeric CSV in `data/source-tables/national-2027.csv` and the
pinned official source manifest `data/national-sources.json`. `--check` verifies
snapshot drift; `--verify-sources` downloads the pinned PDFs and rejects changed
fingerprints. No source PDFs are redistributed.

The 2027 USA Swimming documents are image-only. Their 17 individual-event rows
were transcribed and visually reviewed in the published column order (women SCY,
women LCM, men LCM, men SCY). OCR was used only as an exploratory aid and is not a
numerical source. Futures has separate 18-and-under and 19-and-over pages; Junior
Nationals uses its main standards page, excluding its bonus standards and relays.
The Futures pages publish different qualifying-window start dates; the benchmark
does not determine whether a particular swim meets an entry window or age date.

NISCA's 2026–2027 tables contribute eight individual events in SCY and SCM for
each category, with Consideration and All-America time thresholds kept separate.
The official rules accept only 25-yard or 25-meter swims. LCM, relays, award
applications, scholastic eligibility and meet validation are outside this lookup.
A time threshold alone does not award All-America status.

For a new edition, inspect every relevant PDF page, update the CSV and source
manifest together, review the numeric diff, then regenerate. The importer rejects
duplicate keys, unexpected row counts, malformed clocks and reversed threshold
order. Independent samples and coverage/age boundaries belong in the portable
SDK fixtures. The shared Rust benchmark operation uses original swims only;
course and altitude estimates never become qualifying performances.
