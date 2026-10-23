# Conversion methods and resources — October 19, 2026

NCAA remains the default. Colorado Timing is a quiet alternative in the web’s
**Calculation options** section, both native apps, widget and MCP card.
**Course conversion** and **Altitude policy** are separate controls. Web/native drafts
remember it; web saved/history comparisons and share links retain it. Old records
and links retain NCAA. The original swim remains the basis of standards and points.

The canonical Rust engine implements the **USA Swimming teams** section of
[SportsEngine Motion / TeamUnify’s formulas](https://motion-help.sportsengine.com/en/articles/8538107-how-to-perform-course-conversion-factoring-of-times),
August 6, 2026 edition, checked October 19. See [methodology](METHODOLOGY.md) for
all formulas, coverage and independent examples, including distance exceptions.
`data/colorado.json` records coefficients and the source fingerprint. No source
HTML or swimmer dataset is redistributed.

[Web method setting](screenshots/web-altitude-settings.png) ·
[iOS result](screenshots/ios-method-comparison-light.png) ·
[Android result](screenshots/android-method-comparison-light.png) ·
[Swimming resources](screenshots/swimming-resources.png)

## Validation

The current combined review is in [Native visual review](NATIVE_VISUAL_REVIEW.md)
and [the required PR checks](https://github.com/Stanback/turnmark/pull/31/checks).
Local checks cover 7,394 shared-engine cases in Node/browser Wasm and Swift/Kotlin,
106 packed-SDK fixtures, 164 unit/design cases, 47 browser cases plus one
inapplicable skip, 21 production-runtime cases, 24 iOS cases and 27 Android cases.
MCP packed/offline checks compare 79 exact SDK outcomes and eight malformed
requests across eight protocol/capability combinations; official bridge checks
pass over stdio and HTTP. Real-host acceptance remains separate.

SDK 0.2.0 and MCP 0.3.0 remain **unpublished** source versions. This pass does
not publish packages. Physical-device and assistive-technology checks remain
release work.

## Scope

Resources link to SwimSwam, Swim Standards, USA Swimming Data Hub and standards,
Swimcloud, USMS and World Aquatics. These are outbound community/source links,
not an import or integration commitment.

The roadmap withdraws broader logger, PB, cloud and coach-feature expansion.
Existing local records and export/import remain supported. Model research is
isolated in [draft PR #24](https://github.com/Stanback/turnmark/pull/24), citing
[Alec Vercruysse’s paper](https://www.menloschool.org/live/files/3097-alec-vercruysse)
and the [2018 Swimulator distribution-matching explanation](https://swimswam.com/swimming-real-time-converter/).
Its public source contains fixtures and import/evaluation scaffolding; collected
research data and local collector artifacts remain gitignored. No trained model,
product inference or accuracy improvement is claimed.
