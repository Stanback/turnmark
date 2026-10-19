# Product positioning

Direction recorded October 19, 2026. Turnmark is **a private, offline swim
companion**: convert across pool courses, see how an entered time compares with
published benchmarks, and keep a small local scratchpad useful at practice or
on the pool deck. Keep the identity **Your swim. Any course.**

Suggested short description:

> Your swim. Any course.
>
> An offline swim companion for converting times, checking standards, and logging swims on your device.

The visual direction supports those jobs: editable swim first, readable course
equivalents, one useful next target, and optional explanation/source detail.
Use restrained water artwork and shared navy/cyan/lime tokens. Native apps
adapt the hierarchy with SwiftUI/Compose controls and platform navigation;
sharing colors and icons does not automatically propagate a web layout.

Native supporting copy may add **“Log meet and practice swims on your device.”**
Web supporting copy may add **“Save comparisons and optionally adjust for altitude.”**
Keep SCY, SCM and LCM beside the converter, where they describe the choices.
Do not lead with “swim logger”: conversion and standards remain the primary jobs,
and actual performance logging is currently a native feature. “Offline-first”
is useful in developer documentation; “works offline” is clearer in the UI.
The web needs an initial online visit to cache its app files; installed native
apps work offline on first launch. Do not imply altitude input in native,
widget or the MCP conversion card until they implement it. The separate MCP
altitude tool already provides the current USA Swimming adjustment.

## What the companion helps with

- Compare a timed swim across yards and meters without losing its original
  event, course or time.
- See an original-course standards ladder, distance to the next published
  benchmark, or applicable World Aquatics points. Visualize the comparison with
  clear labels and existing data rather than invented prediction ranges.
- Keep a few useful swims or comparisons close at hand, with no account or
  dependency on a results provider's live connection. Actual practice/time-trial
  swims can be useful even when they are absent from official databases.

The local record is a working scratchpad. It is not a verified national results
profile or a promise to expand into a general training logger, coach dashboard,
cloud synchronization or meet aggregator. Those remain outside the roadmap.

## Describe the current surfaces accurately

The web app keeps recent conversions and explicitly saved comparisons locally.
**Save comparison** stores a calculation setup; it does not log an actual race.
Native development builds have **My times** and **Log swim** for actual
performances, including timed practice swims, with a date and optional meet.
Those native records stay on the device and have portable import/export.
Do not advertise native logging as a shipped web feature or imply cloud backup.

Actual performances and hypothetical comparisons remain distinct. A converted
estimate is never silently a recorded performance or personal best. Published
standards are benchmarks; the meet's rules determine entry eligibility.

Keep the main description about the swimmer's job. Shared Rust, Wasm and other
implementation details belong in developer documentation after that purpose is
clear. Relevant contracts: [native jobs](NATIVE_PRODUCT_NOTES.md),
[design](DESIGN_CONTRACT.md), [history](MEET_HISTORY.md), and
[layout exploration](CONVERTER_LAYOUT_EXPLORATION.md).
