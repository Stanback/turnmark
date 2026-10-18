# Native converter apps

The first native workflow is implemented in SwiftUI (`apps/ios`) and Jetpack
Compose (`apps/android`). Both call the generated Rust SDK directly, work
offline on first launch, and use the same source editions and outcomes.

## Current scope

- Time, stroke, actual event distance, entered course, published category and
  target course controls. Available input events come from Rust, including
  yard-distance mappings and short-course-only events.
- Conversion, entered/published/derived labels, source attribution, invalid
  input and unsupported-comparison states. The persistent result shows its
  destination event, units, course and category alongside the original swim.
  Details open a native sheet with entered/result context, multiplier and
  source edition; the multiplier comes directly from the SDK.
- One saved swim, restore/remove actions, current-input persistence and native
  sharing. Share links still open the existing GitHub Pages app. The
  `turnmark.app` website migration is a separate PR.
- Convert, Saved and Method screens, system appearance, scalable native text
  and native accessibility semantics. The converter opens directly into inputs,
  without an app-name banner or page heading. Shared wave launcher icons and
  platform launch behavior are described in [brand asset generation](BRANDING.md).
- iOS uses system Liquid Glass navigation, pickers and glass Save/Share buttons
  on iOS 26+. Input and result cards retain opaque, readable surfaces. Older
  supported versions use standard bordered buttons.

This is the first converter workflow, not full web feature parity. Native youth
and Masters benchmarks, points, altitude entry, full history/export,
layered iOS icon/store artwork, verified app links and final release targets remain later
work. Physical-device, VoiceOver/TalkBack, large-text and 16 KB Android runtime
checks are release gates; automated simulator tests do not establish those.
Bundle/application ID `net.stanback.turnmark`, iOS 17 minimum and Android API 26
minimum are provisional until release configuration is finalized.

The next workflow is [offline meet and swim history](MEET_HISTORY.md): quick
logging of actual performances, meet/date context and progress, with portable
export/import. Existing saved conversions will not silently become race records.

## iOS

Use current stable Xcode 27.1 with an iOS 27 simulator and the Rust targets listed in
[the engine guide](SHARED_ENGINE.md), then:

```sh
npm run build:native:ios
xcodebuild -project apps/ios/Turnmark.xcodeproj -scheme Turnmark \
  -sdk iphonesimulator -configuration Debug -derivedDataPath target/ios-app \
  build CODE_SIGNING_ALLOWED=NO
node scripts/test-ios.mjs app
```

Open `apps/ios/Turnmark.xcodeproj` in Xcode, select an iPhone simulator, and Run.
Xcode 27 displays simulators in Device Hub. Simulator development needs no signing
credentials. Device builds use the developer's local team/signing configuration.

The Xcode project is checked in, so building does not require a generator.
`apps/ios/project.yml` records its source definition. After changing project
structure, regenerate with XcodeGen 2.46.0 using
`xcodegen generate --spec apps/ios/project.yml` and commit the resulting project.
Do not commit `xcuserdata`, signing credentials or provisioning profiles.

## Android

Use JDK 21, Android SDK platform **37.0**, build tools 36.0.0 and NDK
30.0.16248370. The app uses AGP 9.4.1, Compose compiler/Kotlin 2.4.21 and the
stable Compose BOM 2026.09.00. Set `JAVA_HOME`, `ANDROID_HOME` and
`ANDROID_NDK_HOME` to your installations, then:

```sh
npm run build:native:android
./gradlew :app-android:assembleDebug :app-android:assembleDebugAndroidTest
# Boot an emulator fully or attach a development device first:
node scripts/test-android.mjs app
```

Open the repository's Gradle project in Android Studio, select `app-android`,
and Run, or install `apps/android/build/outputs/apk/debug/app-android-debug.apk`
with `adb install -r`. No Internet permission is requested by the app.
The app bundles arm64-v8a and x86_64 native libraries. New SDK platforms use a
minor-version package name (`platforms;android-37.0`), not `android-37`.

The test wrapper removes stale reports, checks the runner's result when
available, and requires fresh JUnit test cases with no failures/errors/skips.
This catches a real observed AGP failure mode: the Gradle task exited successfully
after the test APK could not install on a still-booting emulator.

## Public-repository CI

Pull-request checks run Rust/web tests, unsigned iOS simulator builds/UI tests,
and Android debug builds/emulator tests. They use `contents: read` and contain no
Cloudflare, Apple signing or store-upload credentials. The iOS job uses the
`xcode-27` runner, pins Xcode 27.1 and verifies SDK 27.1 before building. Simulator
selection prefers the latest installed iOS runtime; CI requires iOS 27. Local
visual checks can also run on older supported runtimes. Test artifacts expire
after seven days. Jobs are capped at 15 minutes for core/web, 30 minutes for iOS
and 20 minutes for Android, so a stalled toolchain cannot occupy a runner for the
default six hours. The existing website deployment remains a main-branch-only
job with its own permissions; do not use `pull_request_target` to execute PR code.

When releases are added, put signed builds and TestFlight/Play uploads in a
separate trusted release workflow with a protected environment. Keep release
credentials out of PR jobs and require deliberate promotion of the reviewed
commit. IaC previews separately execute trusted branch code with infrastructure
credentials, so the IaC repo now skips fork/Dependabot previews.

## Checks

Both UI suites exercise a women’s 100 free swim of `1:00` LCM converted to
`52.44` SCY, source-detail access, saved-swim restoration, zero-time rejection,
and an unavailable 100 IM to LCM comparison. A fourth test checks destination
context for 400 m to 500 yd, category changes and same-course entered swims.
The iOS saved-swim test terminates/relaunches the app;
Android recreates the activity and reads persisted state. The portable SDK
fixtures continue to test the numerical core independently of UI controls.

The iOS result bundle retains screenshots of Convert, Saved and Method in light
and dark appearance. For a local Android visual review, pass instrumentation
argument `turnmarkScreenshots=true` to the conversion/restoration test. It writes
`android-converter.png`, `android-saved.png`, `android-method.png` and
`android-details.png` in the debug
app's private files directory, readable with `adb exec-out run-as
net.stanback.turnmark cat files/<name>.png`. The app requests no screenshot or
storage permission; capture code exists only in the test APK.
