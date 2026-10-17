# Native apps: implementation scope

Status: draft implementation plan for PR #2, October 17, 2026.

PR #1 established the JavaScript/TypeScript SDK and its source-backed contract.
That package already supports web, embed, and Node consumers. It does not yet
provide a library importable by Swift or Kotlin. The first milestone here is
to prove that native integration, then deliver a working native converter on
both platforms.

## Fixed product constraints

- iOS: Swift and SwiftUI.
- Android: Kotlin and Jetpack Compose.
- Both platforms have equal feature scope and shared acceptance criteria.
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

If the packaging or debugging cost is unsuitable, use Swift/Kotlin domain
implementations backed by the same data and fixture gates. Record that decision
explicitly before expanding the screens. The native UI direction remains fixed.

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
