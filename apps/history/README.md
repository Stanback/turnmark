# Portable swim history v1

This is the shared record contract for native history and future web/agent
adapters. `contract-v1.json` is an importable sample using fictional swims;
`import-cases.json` defines validation cases exercised by both native suites.
Contract/fixture changes select both native consumers in CI. Numerical validation remains
in the Rust SDK (`parseTime` and `getEventOptions`); storage is platform-owned.

A JSON archive contains `format: "turnmark.swim-history"`, `version: 1`, and a
`swims` array. Unknown fields are ignored in v1 and are not preserved on export.
A future incompatible contract must use a new version. Imports reject unknown
versions before changing storage.

| Record field | Contract                                                                              |
| ------------ | ------------------------------------------------------------------------------------- |
| `id`         | Lowercase, hyphenated UUID; stable across edits and transfers                         |
| `time`       | Original entered clock string, at most 32 UTF-8 bytes; validated by the SDK           |
| `hundredths` | Integer, must match SDK-parsed seconds rounded to hundredths                          |
| `distance`   | Actual event distance, positive integer supported by the SDK for the stroke/course    |
| `stroke`     | `FR`, `BK`, `BR`, `FL`, `IM`                                                          |
| `course`     | `SCY`, `SCM`, `LCM`                                                                   |
| `category`   | `women` or `men`                                                                      |
| `date`       | Proleptic Gregorian date `YYYY-MM-DD` (years 0001–9999), or null/omitted when unknown |
| `meet`       | Optional name; null/omitted for no meet; nonblank text up to 200 UTF-8 bytes          |
| `createdAt`  | Nonnegative integer UTC Unix milliseconds                                             |
| `updatedAt`  | Integer UTC Unix milliseconds, at least `createdAt`, at most 253402300799999          |

`hundredths` is a checked convenience field, not an independent time source.
Records contain no converted time or comparison target. Personal bests use
actual times grouped by actual distance, stroke, course, and category. All ties
at the lowest time receive PB status; this is the best in the user's current
log, not a claim of official verification or a complete lifetime record.

## Import behavior

- Files are bounded at 10 MiB / 25,000 rows. Read at most the byte limit plus one
  before parsing. Export checks the same limits instead of producing a file
  these apps cannot import.
- Preview validates every row, lists new swims and rejected row numbers, and
  reports duplicate counts. Invalid rows do not prevent reviewing valid rows.
- IDs already on the device are skipped, even if imported fields are different.
  Within a file, the first valid occurrence wins. A rejected occurrence does not
  reserve its ID. Different IDs are separate records even when times match.
- Nothing is saved until the user confirms the preview. Valid new records are
  inserted in one transaction. Existing records are never overwritten by import.
- Export contains the original IDs, clock strings, dates and timestamps. A
  round trip preserves records, including unknown dates and absent meets.
- This format transfers a copy. It does not synchronize edits or deletions,
  deduplicate matching swims with different IDs, or migrate web calculation
  history into actual race results.

## Local stores

- iOS: SwiftData, explicit `HistorySchemaV1` and `HistoryMigration`. The model
  stores the stable ID and encoded record. Autosave is disabled; mutations save
  explicitly, with rollback on failure. Opening/decoding failure is surfaced
  without replacing the store.
- Android: SQLiteOpenHelper database version 1, `swims(id, payload)`. Imports use
  a transaction; database/document I/O runs on `Dispatchers.IO`. Failures are
  surfaced without deleting/recreating the store.
- Existing current-input and saved-conversion preferences are untouched. There
  is no automatic migration into performances. The user may explicitly choose
  **Log entered swim** from the saved conversion.

A logging session remembers the last chosen meet/date for the next swim, keeps
them visible in the form, and resets defaults when the calendar day changes or
the app restarts. Logging does not erase the current input. Meets are optional
labels, not a separate cloud or identity resource. Device backup behavior is
controlled by the operating system; Turnmark adds no account or sync service.
