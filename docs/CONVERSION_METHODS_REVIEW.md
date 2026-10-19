# Conversion methods and resources — October 19, 2026

NCAA remains the default. Colorado Timing is a quiet alternative in the web’s
collapsed settings, native overflow menus, widget and MCP card. Web/native drafts
remember it; web saved/history comparisons and share links retain it. Old records
and links retain NCAA. The original swim remains the basis of standards and points.

The canonical Rust engine implements the **USA Swimming teams** section of
[SportsEngine Motion / TeamUnify’s formulas](https://motion-help.sportsengine.com/en/articles/8538107-how-to-perform-course-conversion-factoring-of-times),
August 6, 2026 edition, checked October 19. See [methodology](METHODOLOGY.md) for
all formulas, coverage and independent examples, including distance exceptions.
`data/colorado.json` records coefficients and the source fingerprint. No source
HTML or swimmer dataset is redistributed.

[Web method setting](screenshots/conversion-method-web.png) ·
[iOS result](screenshots/conversion-method-ios.png) ·
[Android result](screenshots/conversion-method-android.png) ·
[Swimming resources](screenshots/swimming-resources.png)

## Validation

- Rust formatting, strict Clippy and workspace tests pass.
- 80 portable fixtures and the 7,368-case differential corpus pass through
  Node/browser Wasm and generated Swift/Kotlin host bindings. iOS and Android
  SDK fixture suites pass separately.
- Svelte/TypeScript: zero errors/warnings; 138 unit/design tests pass.
- Browser: 37 passing, one desktop-inapplicable skip. Production runtime: 20
  passing, including offline Colorado switching inside the isolated widget.
- Native apps: 20 iOS and 23 Android cases pass. New cases verify the unchanged
  NCAA default, explicit Colorado choice, persisted draft and formula details.
- MCP packed/offline and Worker protocol checks compare 53 exact SDK outcomes,
  plus eight malformed inputs. Official bridge tests pass over stdio and HTTP,
  including the alternative-method update. Real-host acceptance remains separate.
- Inspected web/resources/widget in light/dark and narrow layouts, native Colorado
  sample captures, and the MCP narrow card. Shared semantic tokens are unchanged.

SDK 0.2.0 and MCP 0.3.0 are **unpublished**. MCP’s development checks report the
pending exact registry dependency; release mode requires SDK 0.2.0 to be published
and verified before MCP can release. Current npm versions remain SDK 0.1.0 and
MCP 0.2.0. No publishing or deployment credentials were used for these checks.

## Scope

Resources link to SwimSwam, Swim Standards, USA Swimming Data Hub and standards,
Swimcloud, USMS and World Aquatics. These are outbound community/source links,
not an import or integration commitment.

The roadmap withdraws broader logger, PB, cloud and coach-feature expansion.
Existing local records and export/import remain supported. Model research is
isolated in [draft PR #24](https://github.com/Stanback/turnmark/pull/24), citing
[Alec Vercruysse’s paper](https://www.menloschool.org/live/files/3097-alec-vercruysse).
It contains synthetic fixtures and an evaluation/import scaffold, no real swimmer
data, trained model, scraper, product inference or claimed accuracy improvement.
