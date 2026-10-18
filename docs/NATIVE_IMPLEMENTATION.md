# Native apps: implementation scope

Status: PR #2 merged the shared SDK and web migration. The following native-app
PR implements the paired converter workflow; see [current app setup and scope](NATIVE_APPS.md).

PR #1 established the JavaScript/TypeScript SDK and its source-backed contract.
That package already supports web, embed, and Node consumers. The Rust proof now
provides generated Swift/Kotlin libraries with native packaging, plus a Wasm
JavaScript adapter. See [implementation and evidence](SHARED_ENGINE.md). The next
milestone is a working native converter on both platforms. Its first screens,
persistence and native sharing are now implemented; broader web feature parity
and release acceptance remain separate work.

## Fixed product constraints

- iOS: Swift and SwiftUI.
- Android: Kotlin and Jetpack Compose.
- Both platforms have equal feature scope and shared acceptance criteria.
- One authoritative calculation engine and one canonical dataset produce the
  Swift, Kotlin, and JavaScript libraries. Generated artifacts are derived
  outputs; domain formulas and validation rules are not maintained independently
  in each wrapper. The former TypeScript calculation implementation has been removed after
  migration comparisons passed.
- Shared calculations execute on-device, work offline, and use the same source
  editions, supported events, precision, and missing-data semantics.
- Platform code owns navigation, controls, accessibility, lifecycle, persistence,
  and sharing. The calculation engine owns domain behavior only.
- The web UI framework remains open. The current Svelte app is the first SDK
  consumer and continues to exercise the shared contract.

## Milestone 1: native SDK proof

Evaluate Rust as the shared calculation implementation. Use UniFFI for Swift
and Kotlin bindings and wasm-bindgen for the web-facing implementation. Keep
the existing TypeScript package as the reference consumer during the experiment.
Do not select Rust for production based solely on a successful host build.

Required evidence:

| Target   | Artifact and verification                                                                                                                     |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| iOS      | Device and simulator libraries, generated Swift bindings, Swift package/XCFramework integration, and fixture calls from the actual Swift API. |
| Android  | Packaged native libraries and Kotlin bindings, a Gradle library consumer, emulator/device coverage, and native-library compatibility checks.  |
| Web/Node | A typed JavaScript wrapper around the Wasm artifact, with explicit initialization, packaged assets, and offline/browser/Node checks.          |

Run [the portable fixtures](../fixtures/README.md) through the real bindings.
Preserve all asserted result fields and availability/validation reasons. Where
an idiomatic native type prevents a malformed JavaScript-shaped input, test
rejection at the native import/share-data adapter instead of bypassing the
generated API's types.

Record toolchain versions, clean/incremental build times, artifact and browser
payload sizes, initialization cost, and a reproducible debugging example.
Test ownership, errors, and lifetime behavior across FFI; invalid user input
must not trigger a Rust panic at the boundary.

If Rust packaging or debugging is unsuitable, evaluate another shared-engine
approach against the same requirements. Independently maintained Swift, Kotlin,
and TypeScript calculation implementations do not meet the single-source goal.
Record the engine decision explicitly before expanding the screens.

Keep maintenance practical: pin binding-generator/toolchain versions, generate
artifacts with repeatable scripts, and record source commit, method/data editions,
and library version together. Native wrappers should translate platform types
and errors; calculations and semantic validation belong to the shared engine.
Generated files should be regenerated rather than hand-edited.

## Development and build environments

Research checked October 17, 2026. Recommended starting setup: local development
on the existing Mac, with GitHub Actions for reproducible builds and tests.
Xcode 27 and Rust are installed locally; the proof also installed a local JDK,
Android CLI/SDK/NDK and emulator in the user's tool cache. Android Studio remains
optional for interactive editing/debugging. This adds no external service account.

| Option            | Current free provision                                                                                                                       | Fit                                                                                                                               |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| GitHub Actions    | Standard hosted runners are free for public repositories, including macOS and Linux. Larger runners and storage have separate billing rules. | Primary CI: Rust/SDK checks, iOS simulator builds/tests on macOS, Android builds/emulator checks on Linux, and release artifacts. |
| Xcode Cloud       | 25 compute hours/month included with Apple Developer Program membership.                                                                     | Optional Apple-specific build/test and TestFlight delivery workflow; does not cover Android.                                      |
| Codemagic         | Personal accounts receive 500 macOS M2 build minutes/month; the free allowance does not apply to Teams or Linux/Windows minutes.             | Optional mobile CI alternative; unnecessary alongside GitHub Actions initially.                                                   |
| Firebase Test Lab | Spark no-cost quota: up to 10 virtual-device and 5 physical-device test runs/day.                                                            | Optional Android device coverage after producing build artifacts; not an IDE or build service.                                    |

Sources: [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[runner capabilities](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[Xcode Cloud allowance](https://developer.apple.com/xcode-cloud/get-started/),
[Codemagic pricing](https://docs.codemagic.io/billing/pricing/),
[Test Lab quotas](https://firebase.google.com/docs/test-lab/usage-quotas-pricing).

Hosted CI runs automated build/test jobs; local Xcode and Android Studio provide
the interactive editing, debugger, simulator/emulator, and device development
loop. Keep the build commands executable locally and in CI. Use short artifact
retention and a small representative device matrix to keep storage and testing
maintenance modest.

Avoid basing a new remote development setup on Firebase Studio: its official
release notes say new signup/workspace creation is disabled and the service
sunsets March 22, 2027. This concerns Firebase Studio, not Firebase Test Lab.
[Firebase Studio status](https://firebase.google.com/support/release-notes/firebase-studio).

## Milestone 2: one complete native workflow on both platforms

Build `apps/ios` and `apps/android` with:

1. Time, stroke, actual distance, entered course, and published category input.
2. Conversion results with published/derived/entered labels, source attribution,
   and understandable unsupported-event or invalid-input states.
3. One locally saved target and native sharing of a link the web app can read.
4. Offline first launch, process restart, and data restoration checks.
5. VoiceOver/TalkBack checks, platform text scaling, keyboard handling, safe
   areas, and native navigation/back behavior.

Keep these workflows at parity while using each platform's controls and layout
conventions. Validate on simulators/emulators and physical devices before a
store release. The initial converter milestone does not establish parity with
all existing web features; youth/Masters/points, full history, and export need
their own completed native acceptance cases.

## Completion and release boundary

Keep PR #2 as a draft until its implemented scope, supported targets, and
validation evidence are explicit. Generating bindings, compiling on macOS,
or creating empty app projects does not establish a working iOS/Android SDK.
Publish neither npm packages nor store binaries as part of scaffolding.

SDK/core licensing stays unchanged during this experiment. Resolve distribution
rights, final identifiers, supported OS versions, store metadata/privacy, and
signing before public release, using the decisions tracked in the
[platform plan](PLATFORM_PLAN.md).
