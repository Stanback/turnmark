# Native converter apps

The first native workflow is implemented in SwiftUI (`apps/ios`) and Jetpack
Compose (`apps/android`). Both call the generated Rust SDK directly, work
offline on first launch, and use the same source editions and outcomes.

## Current scope

- Time, stroke, actual event distance, entered course, published category and
  course-equivalent rows for choosing the focused destination. Available input events come from Rust, including
  yard-distance mappings and short-course-only events.
- Conversion, entered/published/derived labels, source attribution, invalid
  input and unsupported-comparison states. The persistent result shows its
  destination event, units, course and category alongside the original swim.
  Calculation details use native grouped sections/sheets to compare NCAA and
  Colorado Timing for the chosen destination, explain the rules and show the
  selected multiplier/offset and source edition. Values come from the SDK;
  method differences are not prediction intervals.
- **Convert · My times** navigation and **Log swim** confirmation. From Convert,
  the editor prefills the entered performance; My times opens a blank-time editor.
  Recent and Best times views show actual records, not converted estimates.
  Records can be edited/deleted and compared without changing the original time.
- Current-input persistence, native sharing and an explicit transition for the
  previous saved comparison. Old bookmarks retain their meaning and can be
  restored/removed from My times. Sharing uses `https://turnmark.app/`.
- Offline actual-swim storage with personal bests for matching actual events.
  JSON export/import uses one [portable format](../apps/history/README.md), with
  preview, rejected-row reporting, duplicate-ID skipping and atomic inserts.
  iOS uses versioned SwiftData; Android uses SQLiteOpenHelper with database and
  document I/O off the main thread.
- Contextual **Standards & points** from Convert and recorded-swim detail, including
  B–AAAA youth levels, 2026 USMS targets and 2026 World Aquatics points. Rust
  owns assessment and next-target gaps. Original swim context, source editions,
  missing-data states and locally remembered comparison settings remain visible.
  See the [standards review](NATIVE_STANDARDS_REVIEW.md).
- Generated semantic palettes from the [shared design contract](DESIGN_CONTRACT.md).
  A navy result card, tabular clock, cyan actions and lime result emphasis give
  both apps the same identity. Native forms, pickers, sheets and navigation retain
  platform behavior and appearance. iOS uses Liquid Glass actions on iOS 26+;
  older systems use standard bordered controls. Android maps complete Material 3
  foreground/background roles.
- Blank, input-first phone arrival with an explicit example action, followed
  by all three course equivalents. A scroll shortcut reaches valid results;
  typing never jumps the viewport. Expanded workspaces keep independent input/
  result panes.
  iOS 27.1 uses reserved division regions and ArrangementView for active folds;
  Android uses Material adaptive folding features and window bounds. Tabletop
  puts results above and inputs below the fold. My times has adaptive list/detail
  navigation. Native keyboard Done, scalable text and system sharing remain.
  [Adaptive layout notes](ADAPTIVE_LAYOUT.md) track verification and limits.

This is the first converter workflow, not full web feature parity. Native altitude entry,
layered iOS icon/store artwork, verified app links and final release targets remain later
work. Physical-device, VoiceOver/TalkBack, large-text and 16 KB Android runtime
checks are release gates; automated simulator tests do not establish those.
Bundle/application ID `net.stanback.turnmark`, iOS 17 minimum and Android API 26
minimum are provisional until release configuration is finalized.

The [offline meet and swim history](MEET_HISTORY.md) workflow is implemented
with portable export/import. Existing saved conversions do not become race
records unless explicitly logged. Charts, splits and synchronization are later
work. See the [native visual review](NATIVE_VISUAL_REVIEW.md) for current screenshots
and outstanding checks before physical-device testing and beta preparation.

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

Pull-request checks select affected platforms using the dependency rules in
[CI.md](CI.md). Web-only changes do not start native jobs. Shared Rust/data
changes run every consumer; Swift and Kotlin changes run their own platform.
Selected native jobs build unsigned iOS simulator apps and Android debug apps,
then run UI tests. They use `contents: read` and contain no
Cloudflare, Apple signing or store-upload credentials. The iOS job uses the
`xcode-27` runner, pins Xcode 27.1 and verifies SDK 27.1 before building. Simulator
selection prefers the latest installed iOS runtime; CI requires iOS 27. Local
visual checks can also run on older supported runtimes. Test artifacts expire
after seven days. Jobs are capped at 15 minutes for core/web, 45 minutes for iOS
and 20 minutes for Android, so a stalled toolchain cannot occupy a runner for the
default six hours. The existing website deployment remains a main-branch-only
job with its own permissions; do not use `pull_request_target` to execute PR code.

The iOS wrapper disables bulk simulator diagnostic collection: Xcode was observed
remaining in the test step after all five UI cases passed. Test exit status,
xcresult results and screenshot attachments are still retained. Local app checks
use the same option, so CI does not need a different test-success criterion.

When releases are added, put signed builds and TestFlight/Play uploads in a
separate trusted release workflow with a protected environment. Keep release
credentials out of PR jobs and require deliberate promotion of the reviewed
commit. IaC previews separately execute trusted branch code with infrastructure
credentials, so the IaC repo now skips fork/Dependabot previews.

## Checks

Both UI suites exercise a women's 100 free `1:00` LCM conversion to `52.44`
SCY, source details, draft persistence, original/derived context, invalid input,
unsupported comparisons and original-value sharing. They also cover recording
from My times, Recent/Best times filtering, actual-swim editing/comparing/deletion,
and old comparison bookmarks remaining separate across restart. The shared
history suites validate portable imports, atomic rejection and matching bests.
SDK conformance fixtures test numerical behavior independently of the UI.

For iOS, the result bundle retains screenshot attachments. Select a runtime with
`TURNMARK_IOS_RUNTIME=27.1 node scripts/test-ios.mjs app`. For Android opt-in captures, install the built app and test APKs, then run
`adb shell am instrument -w -e turnmarkScreenshots true net.stanback.turnmark.test/androidx.test.runner.AndroidJUnitRunner`.
PNG files are written to the debug app's private directory and can be read with
`adb exec-out run-as net.stanback.turnmark cat files/<name>.png`. Capture code
exists only in the test APK and requires no app permission. Gradle can uninstall
test apps after a connected run, so use direct instrumentation for this manual
capture workflow. The Android adaptive
test injects WindowManager book/tabletop regions and checks that complete input
and result bounds avoid the fold while entry and focus survive the transition.

## Usability review

The October 17 pass includes iPhone 18 Pro/iOS 27 and iPhone SE (3rd generation)/
iOS 26 at standard and accessibility text sizes, plus Android API 36 at the
default phone size and a 360 × 640 dp phone with 200% text. Review covers readable
result context, scrolling to input/actions, keyboard entry/dismissal, save
feedback, persistent removal and opening/cancelling platform share UI. iOS keeps
native system appearance; Android's chooser payload is checked independently of
its preview. These are simulator/emulator checks, not physical-device or full
VoiceOver/TalkBack sign-off.
