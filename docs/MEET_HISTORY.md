# Offline swim and meet history

Status: implemented on iOS and Android, pending physical-device release checks.
The paired apps now log actual swims with optional meet/date context, edit/delete
records, show personal bests, and import/export a portable JSON archive. The
previous saved comparison remains accessible separately in My times. See the
[shared record contract](../apps/history/README.md) for format, validation,
duplicate handling and platform storage details.

## Pool-deck workflow

Make recording a real swim quick enough to do between races:

1. Enter the time, event and course, then choose **Log swim**. This records the
   entered performance, independently of whether a conversion is available.
2. Show a small confirmation form with the actual time/event, date and an
   optional meet name. Default to today initially; offer the most recently used
   meet/date for the next race, while keeping that context visible and editable.
   Do not silently attach a future swim to an old meet.
3. After saving, return to entry with the meet and course ready for the next
   event. Allow a practice swim or time trial without requiring a meet.
4. My times groups compact rows by meet/date. Each row leads with the actual time
   and event, then course and useful context. Opening it allows correction,
   deletion and **Compare this swim** without modifying the original record.

My times also offers Log swim directly, with an empty clock field, and
Recent / Best times views. The previous saved comparison has explicit restore
and remove actions; restoring its inputs does not record a performance. Existing web conversion history is
also calculation history, not evidence that those swims actually happened.

## Information hierarchy

The converter's answer identifies the returned event, actual destination
distance and units, course, and published category. The number is prominent;
entered/published/derived status remains visible. The original time and course
stay nearby. A details sheet contains full entered/result context, the SDK's
multiplier, source and edition. This hierarchy is implemented in the current
native converter PR.

History uses a different emphasis: the actual performance comes first, with
meet/date providing its context. Estimates remain a separate comparison view.
Do not label a manually entered performance as an officially verified result.

Start progress with a simple chronological list and personal best for the same
actual distance, stroke, course and selected category. Keep yards and metres
separate. Converted times cannot set a personal best. A chart can follow once
the underlying history and editing flow are useful; it is not a prerequisite
for logging races.

## Data and storage

- A record needs a stable ID, the original clock string, normalized time from
  the shared engine, actual event/course, selected category, swim date and an
  optional meet reference/name. Creation/modification timestamps are separate
  from the calendar date of the swim. Support an unknown historical date
  explicitly rather than inventing one during import.
- Round, splits, placing, notes and external result IDs are later extensions.
  DQ/DNS and other non-time outcomes need explicit statuses if added; they are
  not zero-second swims. Keep the initial entry form small.
- Native storage belongs outside the Rust calculation core. Use a structured
  local store with explicit schema migrations once multiple records are added;
  preferences remain suitable for settings and the current draft. Use SwiftData on iOS and SQLiteOpenHelper on Android, with explicit local schema
  versions and no database abstraction in the numerical SDK.
- Define one versioned, portable export/import schema for both apps and the
  eventual web adapter. Validate imported clock strings and events through the
  shared engine, report rejected records, and make duplicate handling explicit.
  Preserve original records and IDs across an export/import round trip.
- Store actual swims independently of comparison outputs. Recalculate estimates
  with the current SDK and display its method/data edition; do not rewrite a
  recorded performance when a factor snapshot changes.
- Everything above works without an account or network connection. Export/import
  provides a portable copy; encourage users to keep a backup. A device-only log
  is not a synchronization or backup service.
- No iCloud/CloudKit sync is configured. Normal iOS device backups may include
  the local app data, according to the user’s settings; this is not a guaranteed
  reinstall/restore feature. Android currently sets `allowBackup="false"` for
  cloud backup (some manufacturers may still support device-to-device transfer).
  Export before deleting the app or clearing its data.

## Standard interchange follow-up

Keep the versioned Turnmark JSON archive as the lossless backup/transfer contract
for actual records and their IDs/timestamps. Established swimming exchange
formats can be adapters at the boundary rather than replacements for storage:
[SDIF version 3](https://www.usms.org/admin/sdifv3f.txt) defines fixed-width
swimming records, while the maintained [LENEX documentation](https://wiki.swimrankings.net/index.php/swimrankings:Lenex)
covers meet entries/results, records and time standards using XML.

Evaluate SDIF for US meet-file import and LENEX for broader interoperability,
using real sample exports before promising compatibility. Future adapters need
swimmer selection, course/event/category mapping, explicit handling of unknown
or non-time results, a preview and duplicate policy. Do not fabricate identity
or silently turn relay/split/converted values into individual performances.
Standard imports/exports are planned; current native import/export accepts only
the documented Turnmark JSON archive.

## Agent access later

MCP can eventually help import a meet's swims or answer questions about progress.
The first calculation tools remain read-only and accept explicit swim inputs;
they do not gain access to local history automatically. See the
[agent interface plan](AGENT_INTERFACES.md).

A later history adapter should share the versioned record schema and access an
explicitly selected local store or import file. Give reads and writes separate
contracts. Batch imports need a reviewable preview, validation, duplicate
handling and a clear save result. A public remote calculation endpoint must
not expose personal history. Logging and browsing remain fully usable without
MCP or WebMCP.

## Acceptance and release checks

- Log several races at one meet quickly on both platforms; edit the date/meet,
  log a swim without a meet, correct/delete a record and reopen after restart.
- Log a valid actual swim even when its requested conversion is unavailable.
  Changing comparison settings must leave the performance unchanged.
- Confirm personal bests use actual comparable swims only, including distinct
  400 m/500 yd and 1500 m/1650 yd events.
- Exercise migration from the current single saved conversion without silently
  creating race records. Check malformed imports, duplicate handling and
  export/import round trips without data loss.
- Review empty/populated history, longer meet names, large text, both
  appearances and native accessibility. Demonstrate the workflow offline.
