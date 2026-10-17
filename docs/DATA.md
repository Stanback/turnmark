# Updating source data

The app uses checked-in numeric snapshots, with attribution and retrieval metadata. There is no live scraping or external API dependency in the shipped app.

## USA Swimming motivational standards

1. Visit the [official standards index](https://www.usaswimming.org/Times/time-standards) and confirm the current cycle, revision, and official PDF URL.
2. Install Poppler (`brew install poppler` on macOS).
3. Run `npm run data:refresh`. To reproduce a downloaded version: `python3 scripts/import-standards.py --pdf /absolute/path/source.pdf`.
4. The importer intentionally fails if the October 10, 2025 revision or the expected 482 individual-event/category rows changes. Review the new PDF before updating those guards.
5. Render and inspect representative pages from each course; verify age headers, both category column orders, distance mappings, missing events, and every amended value. Compare generated JSON against the prior snapshot. No PDFs are redistributed in this repository.
6. Update source dates and user-facing counts/cycle labels if they change. Run the checks and tests.

The generated `src/data/standards.json` records the source URL, revision, retrieval date, SHA-256 fingerprint, scope, level order, and 482 records. Each record’s six times are seconds in B → AAAA order. Stars in the source are not part of numeric time values.

## NCAA factors

1. Check the [official NCAA swimming rules page](https://www.ncaa.org/championships/playing-rules/swimming-and-diving-playing-rules/) for the current rules book.
2. Inspect Appendix C’s conversion tables, directions, factor categories, event coverage, and truncation instructions.
3. Update `src/data/conversions.ts` and the source fingerprint in `src/data/sources.json`.
4. Add a published numerical example to the tests if the calculation changes. Never infer a missing event factor from a nearby event.

## Altitude

Check USA Swimming’s official Times and Recognition Policy Manual §4.7. Review band boundaries and eligible events, then update the source metadata, numeric table, documentation, and boundary tests together.

Run `npm run check`, `npm test`, `npm run test:browser`, and `npm run build` before publishing a data change.
