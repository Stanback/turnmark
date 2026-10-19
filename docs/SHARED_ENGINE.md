# Shared engine implementation

Rust is the single calculation implementation for the web app and generated
Swift/Kotlin libraries. PR #2 completes the shared SDK and the web migration.
The paired SwiftUI/Jetpack Compose workflows were added in subsequent PRs.

Current consumers now include the web app, publisher iframe, MCP service and
paired native converter/history/Standards & points screens. The current source
corpus has 80 portable cases and 7,368 cross-runtime cases; published SDK 0.1.0
retains its original 62-case release contract. See [native scope](NATIVE_APPS.md),
[MCP Apps review](MCP_APPS_REVIEW.md) and [package release status](SDK_RELEASES.md).
The migration-specific observations below remain a record of that earlier stage.

## Ownership

| Path                   | Owns                                                                                                           |
| ---------------------- | -------------------------------------------------------------------------------------------------------------- |
| `data/*.json`          | Canonical numerical snapshots, conversion/altitude factors, source editions and fingerprints.                  |
| `crates/turnmark-core` | Calculation, semantic validation, coverage distinctions, provenance, clock parsing and typed native contracts. |
| `crates/turnmark-wasm` | A small wasm-bindgen transport into the same core.                                                             |
| `packages/swift`       | Swift package with generated Swift bindings and a device/simulator XCFramework.                                |
| `packages/android`     | Gradle library with generated Kotlin bindings, 64-bit native libraries and JNA.                                |
| `packages/sdk`         | Typed JavaScript adapters and explicitly initialized Wasm, used by the web app.                                |

Generated bindings, copied JSON, native binaries and Wasm are ignored build
outputs. Edit root `data/` and Rust source; regenerate instead of editing copies.
Import scripts now update root `data/`. The SDK build generates source metadata, embeds the numerical tables in Wasm,
and packages the asset. Web development needs Node/npm, Rust, and the pinned
wasm-bindgen CLI. Native builds do not require a JavaScript calculation runtime.

Swift and Kotlin call typed functions such as `convertSwim`, with records and
available/unavailable/invalid enum outcomes. Their application APIs do not pass
JSON strings. The exported `evaluate` transport additionally supports imported
JSON and portable conformance tests; malformed JSON/unknown operations throw
typed transport errors. Invalid calculation inputs return structured outcomes.
Native requests use the library's pinned method/data editions; each result
includes provenance. No platform wrapper contains a domain formula.

The old TypeScript calculation/validation implementation has been removed,
including the numeric helpers used by the existing web UI. `compat` modules
translate its argument/result shapes into Rust calls. Reactivity, labels,
layout, navigation, local storage, sharing and other UI behavior stay in Svelte.
The browser initializes the Wasm asset before hydration, and static pre-rendering
initializes the same module from bytes in Node. Offline caches include Wasm.
Initialization errors show a reload message instead of switching algorithms.

## Reproduce

Pinned tools: Rust 1.91.1, UniFFI 0.32.2, wasm-bindgen/CLI 0.2.129, Gradle 9.8.1,
AGP 9.4.1, Android NDK 30.0.16248370 and JNA 5.19.1. `Cargo.lock` and the Gradle
wrapper lock the resolved Rust dependencies and Gradle download. Local validation
used Xcode 27/Swift 6.4, JDK 21 and Kotlin CLI 2.4.21. AGP supplies Android's
built-in Kotlin compiler; no separate Kotlin Android plugin is needed.

Web/Node and pure core checks:

```sh
cargo install wasm-bindgen-cli --version 0.2.129 --locked
npm ci
cargo test --locked --workspace --features turnmark-core/native
cargo clippy --locked --workspace --all-targets --features turnmark-core/native -- -D warnings
npx playwright install chromium
npm run test:engine
npm run test:sdk:package
node scripts/engine-metrics.mjs
```

On macOS with Xcode and an installed iOS simulator:

```sh
rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios
npm run build:native:ios
node scripts/test-native-host.mjs swift
node scripts/test-ios.mjs
```

The generated Swift package is at `packages/swift`. Its XCFramework contains an
arm64 device slice and arm64/x86_64 simulator slices. It currently declares iOS
17 as a provisional minimum. Actual device signing is unnecessary for the
simulator proof; real device testing remains a release requirement.

For Android, install JDK 21, Android SDK platform 36, build tools 36.0.0, NDK
30.0.16248370, platform-tools, and a platform 36 emulator image. Set `JAVA_HOME`,
`ANDROID_HOME`, and `ANDROID_NDK_HOME` to those installations, then:

```sh
rustup target add aarch64-linux-android x86_64-linux-android
npm run build:native:android
./gradlew :sdk-android:assembleDebug :sdk-android:assembleDebugAndroidTest
# Start an Android emulator or connect a device first:
./gradlew :sdk-android:connectedDebugAndroidTest
node scripts/check-android-libraries.mjs
```

The generated AAR is `packages/android/build/outputs/aar/sdk-android-debug.aar`.
An external Gradle consumer also needs its JNA dependency; the AAR is not a fat
bundle. Maven publication and release metadata are not configured yet. The proof
supports arm64-v8a and x86_64, with provisional minimum Android API 26. Future
app modules must keep their ABI filters consistent with the library.

Optional Kotlin/JVM comparison on the host: install Kotlin CLI 2.4.21, put
`kotlinc` on `PATH`, set `JNA_JAR` to the JNA 5.19.1 jar, and run
`node scripts/test-native-host.mjs kotlin`. Android instrumentation does not
depend on this optional CLI installation.

## Evidence and costs

Locally verified October 17, 2026:

- All 62 source-backed portable cases pass in Rust, Swift, Kotlin, Node and
  Chromium. The iOS simulator and Android emulator each run these fixtures plus
  typed native API checks.
- Before deleting the TypeScript implementation, 6,054 public cases and 1,776
  numeric compatibility cases were compared to saved pre-deletion outputs and
  matched. This was a migration check, not a retained second implementation.
- Ongoing cross-runtime checks run the 7,368-case corpus through the pure Rust
  CLI and the generated Node/browser/Swift/Kotlin bindings. The 80 portable cases
  retain independently sourced expected values; additional cases check transport,
  platform arithmetic and data coverage against the Rust host reference.
- Rust additionally checks all 70 points bases yield 1,000 points and verifies
  that the next milestone's target hundredth meets the score while the following
  hundredth misses it. Differences in floating ratios/gaps are tolerated only
  below 1e-9; a one-point or one-hundredth discrepancy fails.
- Error cases, repeated owned-value calls, and generated enum/record transfer
  pass across FFI. The Kotlin generator's reserved `message` error-field conflict
  was found by compiling and fixed in the Rust contract.
- The JavaScript tarball installs offline outside the monorepo, resolves its
  public declarations and Wasm asset export, and executes in Node. Chromium uses
  the browser's fetch/instantiate path, then disables network access before all
  calculations. The existing SDK's isolated Node/browser package checks also pass.
- iOS tests run through the packaged Swift library on a simulator. Android tests
  run through the packaged Gradle library on an arm64 API 36 emulator. Physical
  iOS/Android devices and a 16 KB Android runtime have not been tested yet.
- The packaged Android test APK passes 16 KB ZIP alignment and ELF alignment
  checks for both Rust and JNA libraries in both supported 64-bit ABIs.

The migrated optimized Wasm build is about 360 KB raw / 109 KB gzip, including
all benchmark tables. One local Node run initialized it in about 7 ms and made
the first conversion in about 1.5 ms. These are development-machine observations,
not a cross-device performance budget. `engine-metrics.mjs` writes version,
source commit/dirty state, toolchain, dataset hashes, payload sizes, and current
measurements to `target/engine-metrics.json`; CI uploads its own measurements.
Browser loader/adapter JavaScript adds a small separate payload. A conversion-only
Wasm build and splitting lazily loaded tables remain options if web measurements
justify the maintenance cost.

On the local Mac, initial Rust-only native builds took roughly 9–14 seconds per
architecture once host tooling/dependencies were cached. Incremental Rust builds
took roughly 2 seconds per changed native architecture and about 1 second for
Wasm. These exclude fresh toolchain downloads, Gradle dependency downloads and
emulator startup. The shared engine adds real build tools and native packaging;
it removes the need to maintain the calculations in three languages.

## Debugging and remaining gates

For a repeatable native debugging case, use the typed request in
`packages/swift/Tests/TurnmarkCoreTests/EngineTests.swift` or Android's
`EngineTest.kt`: women, 100 free LCM, `1:00`, target SCY must produce `52.44`.
Changing the time to `invalid` returns an invalid outcome without throwing a
Rust panic. Set a Swift/Kotlin breakpoint on that result first to inspect the
generated enum and provenance.

To inspect Rust source in a native debugger, regenerate with
`TURNMARK_NATIVE_PROFILE=debug` using the same packaging script, rebuild the
consumer, and load symbols from the matching `target/<triple>/debug` library.
The normal packaging default is optimized release. Debug symbol loading inside
Xcode/Android Studio has not yet been manually validated; retain that acceptance
check when the native app projects are added. Pure Rust reproduction works with
the named `typed_native_contract_and_transport_errors` Cargo test.

`.github/workflows/shared-engine.yml` runs core/web checks on Linux, Swift package
tests on macOS and Android instrumentation on a Linux emulator. Native artifacts
are regenerated in each job; reports have seven-day retention. The existing web
workflow continues separately.

PR #2 closes the shared-engine/web scope after its SDK, application, packaging,
offline and native-binding checks pass. Native converter screens, native sharing,
saved targets, accessibility, IDE debugger integration and physical/16 KB device
runtime testing remain acceptance work for the next app PR and release process.
No package publication or store submission is part of this change.
