# Shared engine implementation

The Rust experiment now produces typed Swift/Kotlin APIs and a typed JavaScript
adapter over WebAssembly. It passes the existing calculation contract and runs
through an iOS Swift package/XCFramework and an Android Gradle/AAR consumer.
This is sufficient to proceed with paired native converter apps. PR #2 remains
a draft: native app workflows and the production web migration are still open.

## Ownership

| Path                   | Owns                                                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `data/*.json`          | Canonical numerical snapshots, conversion/altitude factors, source editions and fingerprints.                           |
| `crates/turnmark-core` | Calculation, semantic validation, coverage distinctions, provenance, clock parsing and typed native contracts.          |
| `crates/turnmark-wasm` | A small wasm-bindgen transport into the same core.                                                                      |
| `packages/swift`       | Swift package with generated Swift bindings and a device/simulator XCFramework.                                         |
| `packages/android`     | Gradle library with generated Kotlin bindings, 64-bit native libraries and JNA.                                         |
| `packages/engine`      | Experimental, explicitly initialized JavaScript engine and packaged Wasm asset.                                         |
| `packages/sdk`         | Existing TypeScript implementation, temporarily retained as an independent migration oracle and current web dependency. |

Generated bindings, copied JSON, native binaries and Wasm are ignored build
outputs. Edit root `data/` and Rust source; regenerate instead of editing copies.
Import scripts now update root `data/`. The SDK build generates its self-contained
JSON copies, so normal web development still needs only Node/npm.

Swift and Kotlin call typed functions such as `convertSwim`, with records and
available/unavailable/invalid enum outcomes. Their application APIs do not pass
JSON strings. The exported `evaluate` transport additionally supports imported
JSON and portable conformance tests; malformed JSON/unknown operations throw
typed transport errors. Invalid calculation inputs return structured outcomes.
Native requests use the library's pinned method/data editions; each result
includes provenance. No platform wrapper contains a domain formula.

The JavaScript adapter temporarily uses the existing SDK's declaration types.
These imports are erased; its runtime calls Rust only. Keeping the TypeScript
oracle is an intentional migration step, not the final single-engine state.
Before merging a production migration, move the web app and compatibility
helpers onto Rust and remove the independent TypeScript domain implementation.

## Reproduce

Pinned tools: Rust 1.91.1, UniFFI 0.32.2, wasm-bindgen/CLI 0.2.129, Gradle 9.8.1,
AGP 9.4.1, Android NDK 30.0.16248370 and JNA 5.19.1. `Cargo.lock` and the Gradle
wrapper lock the resolved Rust dependencies and Gradle download. Local validation
used Xcode 27/Swift 6.4, JDK 21 and Kotlin CLI 2.4.21. AGP supplies Android's
built-in Kotlin compiler; no separate Kotlin Android plugin is needed.

Web/Node and pure core checks:

```sh
npm ci
cargo test --locked --workspace --features turnmark-core/native
cargo clippy --locked --workspace --all-targets --features turnmark-core/native -- -D warnings
cargo install wasm-bindgen-cli --version 0.2.129 --locked
npx playwright install chromium
npm run test:engine
node scripts/test-engine-package.mjs
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
- A larger 6,054-case corpus compares Rust bindings against existing TypeScript
  answers in Swift, Kotlin/JVM, Node and Chromium. It covers all youth records,
  USMS age cells including explicit nulls, points bases/unsafe results, course
  combinations, missing factors, and altitude band edges. This comparison corpus
  supplements the independently sourced fixtures; it does not replace them.
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

The initial optimized Wasm build was about 293 KB raw / 87 KB gzip, including
all benchmark tables. One local Node run initialized it in about 9 ms and made
the first conversion in about 2 ms. These are development-machine observations,
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

Before moving PR #2 out of draft, complete the paired converter workflow from
`NATIVE_IMPLEMENTATION.md`, validate native debugging and accessibility, resolve
the production web/SDK migration, and record the supported release targets. Do
not publish packages or submit store builds as part of this proof.
