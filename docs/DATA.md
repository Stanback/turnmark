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

## World Aquatics points

1. Check [World Aquatics’ official points page](https://www.worldaquatics.com/swimming/points) for the current base-times PDF and its separate SCM/LCM validity dates.
2. Run `npm run data:points`. The importer fetches the pinned official PDF, uses Poppler to extract its numeric columns, verifies both time representations, rejects duplicates, and requires 35 individual events (70 category-specific base times).
3. For a future edition, review the PDF and update the URL, validity guards, source dates, labels, documentation, and tests together. Do not simply substitute current world records; the scoring base times have their own validity periods.
4. Verify all 70 base times score 1,000 and independent slower/faster samples follow the published cubic formula and truncation. There is no yards points table and no implicit scoring of course-converted estimates.

## Altitude

Check USA Swimming’s official Times and Recognition Policy Manual §4.7. Review band boundaries and eligible events, then update the source metadata, numeric table, documentation, and boundary tests together.

Run `npm run check`, `npm test`, `npm run test:browser`, and `npm run build` before publishing a data change.

## U.S. Masters Swimming targets

`npm run data:masters` fetches the official USMS NQT page with curl and extracts its first four 2026 tables. Exact headings, course/category order, 13 published age columns, row counts, unique event keys, and numeric cell formats are validated. The checked-in snapshot contains 70 event/category rows and 904 numeric targets. Six source cells say NO TIME and stay null. Source URL, checked date, year, and the source HTML SHA-256 are stored in `data/masters.json`.

Review a newer edition before changing importer guards. Ages 85+ have no USMS NQT; SCM has no target in these Nationals tables. Never infer those missing values, interpolate adult age groups, or generate an adult B–AAAA ladder from NQTs. The UI uses the entered course/time and does not apply NCAA course estimates or USA Swimming altitude corrections to adult eligibility comparisons. USMS entry guidance and event exceptions remain authoritative.
