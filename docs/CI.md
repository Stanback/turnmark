# Selecting builds and tests

CI follows consumer dependencies. Editing the web app does not rebuild the
native apps; editing canonical calculations or data tests every consumer.

| Changed inputs                                                                                                        | Checks selected           |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| Web UI, embedded widget, public assets, browser tests, Vite/Svelte/TypeScript configuration                           | Web                       |
| JavaScript SDK, Wasm adapter, npm manifest/lockfile, JS packaging scripts                                             | Web and core/Wasm         |
| MCP server, Worker, protocol tests                                                                                    | Core/Wasm (including MCP) |
| SwiftUI app, Swift package/tests, iOS packaging/test scripts                                                          | iOS                       |
| Compose app, Android package/tests, Gradle/NDK packaging/test scripts                                                 | Android                   |
| Canonical Rust core, data, conformance fixtures, Cargo manifest/lockfile/toolchain, shared binding build/test scripts | All                       |
| Portable history contract/fixtures (`apps/history/`)                                                                  | iOS and Android           |
| Native host-test helper                                                                                               | iOS and Android           |
| Shared brand-generation script                                                                                        | Web, iOS and Android      |
| Documentation, root Markdown instructions, issue/PR templates                                                         | Selection checks only     |
| Workflows, selection rules, or unfamiliar paths                                                                       | All                       |

The shared palette `design/turnmark.tokens.json`, its generator, the canonical
wave geometry `design/wave.svg`, and the shared glyph catalog/generator select
web, MCP/core and both native checks. The core job also verifies the MCP adapter;
this selection does not imply that a visual edit changes calculation behavior.
The brand export manifest and launcher/favicon exporter select web, iOS and
Android. Native test wrappers and design tests verify the committed vector
exports before running app tests.
Other design contract checks select web. Both native app test wrappers verify
committed generated palettes before testing, so a platform-only edit cannot
silently drift from the source contract.
Web-only layout changes still skip native builds. Editing CI selection rules
themselves selects all checks.

Core/Wasm checks also build and test the MCP package and local Worker. Web-only
edits skip those checks. SDK changes exercise their MCP consumer. The widget’s focused converter entry
and shared comparison controls select web; changes to the SDK converter itself
select web and core/Wasm, including full MCP tool verification. The production
widget test checks its fetched Wasm against the focused asset and rejects a
second engine download.

Shared changes run a fast `core` job first: source snapshot validation, Rust
formatting, Clippy and direct Rust tests. Once it passes, `web-sdk` (Wasm/JS
SDK), MCP, iOS and Android fan out in parallel. A broken shared calculation
therefore stops the expensive consumer jobs before they acquire runners. Native
jobs do not wait for the unrelated browser/JS test suite. Native-only UI edits
intentionally skip the core job and run their selected platform directly; a
failed, cancelled or unexpectedly skipped selected core cannot unlock them.
This uses GitHub's [job dependencies](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds).

The shared result gates downstream execution; a Linux core build is not an iOS
or Android binary. Each consumer still generates/compiles its actual target
libraries from the same checkout, using its platform-specific build cache.
The final `engine-ci` gate requires every selected job to succeed and only
accepts skips for jobs explicitly not selected.

Website hosting configuration (`wrangler.jsonc`) and isolated deployment tooling
under `deployment/` select web checks only. Workflow changes still select all.

The web app and JS SDK still compile their Wasm dependency when selected.
Native jobs generate and package their Rust SDK dependency on a clean runner;
this policy skips unrelated jobs, rather than reusing unchecked binaries.

Both workflows call `.github/workflows/changes.yml`, which tests the rules in
`scripts/ci-changes.test.mjs` and runs `scripts/ci-changes.mjs`. There is one
mapping to maintain. A change affecting multiple platforms selects their union.
When adding packages or moving dependencies, update the mapping and tests in the
same PR. Run these checks locally:

```sh
node --test scripts/ci-changes.test.mjs
actionlint
```

Pull requests compare the event's base commit against the actual merge checkout
being tested. Main-branch pushes compare the entire before/after range. Full Git
history is fetched, and NUL-delimited changed paths include deletions and both
sides of renames. Selection does not depend on the GitHub changed-files API or
its path-filter file limits. A failed comparison fails CI instead of silently
skipping validation. Manual workflow runs, new branches with no comparison base,
and unfamiliar events select all checks.

The workflows always start, so irrelevant jobs can finish as skipped rather than
leaving a required workflow pending. `web-ci` and `engine-ci` are stable summary
checks suitable for branch protection: they accept intentional skips but fail
when selection or any selected job fails or is cancelled. They do not grant
deployment permission. Website deployment still depends on a successful web
build on `main`; docs-only and native-only pushes do not redeploy it.

PR execution retains read-only repository permissions, no persisted checkout
credentials, and no signing, store or infrastructure secrets. Release and
deployment policies remain separate from test selection. Website checks run
without Cloudflare credentials, including local Workers hosting validation.
Automatic production publishing uses the main-only environment and isolated
deployment runner described in [HOSTING.md](HOSTING.md).

MCP Apps views/build/browser harness live under `packages/mcp/` and
`scripts/{build,test}-mcp-ui.mjs`; edits select the core/MCP checks, without native
builds. The MCP job installs Chromium and runs the official bridge/sandbox tests.
Generated shared CSS tokens also select MCP checks because the card inlines them.
Changes to workflows or the selection rules themselves retain the fail-safe full
matrix. Shared numerical core changes still exercise all consumers.

## Native feedback loops

Full regression remains required for each affected native platform. Smoke and
focused runs are local development tools, not substitutes for those gates.
Numerical cases belong in Rust/conformance tests first; pure application-state
and history variations belong in direct tests. Keep real UI journeys for input,
menus, scrolling, native persistence, sharing, accessibility and lifecycle changes.
This follows [Apple's testing guidance](https://developer.apple.com/documentation/xcode/testing)
and [Android's test strategy](https://developer.android.com/training/testing/fundamentals/strategies).

iOS uses native **Full** (default) and **Smoke** Xcode test plans. The 20 UI
regressions are grouped by conversion, benchmarks, history and input, with shared
helpers containing no tests. The wrapper limits parallel execution to two
simulator workers; each has its own app container. `--workers 1` gives a serial
baseline or reduces memory pressure. Smoke, focused and direct-test runs use
one worker by default to avoid provisioning extra simulators for small selections.
It checks/builds current sources once with
`build-for-testing`, then uses `test-without-building`. Incremental products are
reused without accepting an unchecked stale binary. Choose a simulator explicitly
when multiple local iPhones are installed, so another workspace is not interrupted.

```sh
export TURNMARK_IOS_DEVICE=SIMULATOR_UUID
node scripts/test-ios.mjs app                       # full: 7 direct + 20 UI cases
node scripts/test-ios.mjs app --suite smoke         # 7 direct + 4 UI cases
node scripts/test-ios.mjs app --suite unit          # 7 direct app tests, no UI run
node scripts/test-ios.mjs app --only TurnmarkUITests/InputUITests
node scripts/test-ios.mjs app --workers 1           # full serial comparison
node scripts/test-ios.mjs app --screenshots         # opt-in review attachments
```

The Android app and SDK define the same Gradle-managed **turnmarkPhone**:
Pixel 2, stable Android 17/API 37, Google APIs, 64-bit and explicit 4 KB pages.
Gradle owns provisioning, snapshots, boot and teardown.
CI uses that profile on x86_64; Apple Silicon uses arm64, with the same SDK,
profile and tests. The app pins stable Espresso 3.7 explicitly: Compose’s transitive 3.5 dependency
crashes on API 37 while reflecting `InputManager.getInstance`. Rendering uses
SwiftShader on managed devices; animations
are disabled during instrumentation. One device is sufficient for the current
small suite; adding shards would increase boot/resource costs without an
established benefit. See [managed-device guidance](https://developer.android.com/studio/test/managed-devices).

```sh
node scripts/test-android.mjs app --managed         # all 30 cases
node scripts/test-android.mjs app --managed --suite smoke
node scripts/test-android.mjs sdk --managed         # native ABI/fixture checks
node scripts/test-android.mjs app --serial emulator-5556 \
  --only net.stanback.turnmark.ConverterTest#nationalBenchmarksKeepOriginalSwimAndAgeTable
```

Connected-device runs remain available and require an unambiguous, fully booted
device. Android smoke tests use a runtime annotation; focused runs accept one
class or method selector. Do not pass comma-separated method lists to the managed
runner: the tested AGP version executed only the first method in that form.
Both wrappers validate the exact selected test inventory, rejecting missing,
duplicate, failed or skipped cases. Managed test tasks are forced to execute;
compilation remains incremental. Fresh result artifacts cannot be replaced by
an old successful report.

Both wrappers write phase timings and per-test durations to
`target/*-metrics.json`, and list the five slowest cases in the Actions summary.
Full and smoke/focused results use separate names. CI keeps these metrics with
xcresult/JUnit artifacts for seven days. Compare wall time, boot/build overhead
and test durations separately; local warm results do not predict a cold hosted
runner. Track repeated slow/failing cases before adding more workers or retries.

Successful iOS review screenshots are opt-in; XCTest's automatic failure
diagnostics remain enabled. This avoids taking every documentation image on
every commit. Native review still checks light/dark appearance and text scaling;
simulator checks do not replace physical-device or VoiceOver/TalkBack release
review. Host-side Compose screenshot tests remain a possible follow-up: Google's
[Preview screenshot tooling](https://developer.android.com/studio/preview/compose-screenshot-testing)
is experimental, so it is not introduced as a required gate here.

The API 37 headless lane uses 4 KB pages to avoid the 16 KB software-rendering
allocator stalls also documented in
[Robolectric's device configuration](https://chromium.googlesource.com/external/robolectric/+/cf4e934fbbc179f9088a9592ea297999416f0a24/build-logic/convention/src/main/java/org/robolectric/gradle/GradleManagedDevicePlugin.kt).
The existing native-library alignment check still runs. This does not establish
16 KB runtime compatibility; that remains a separate release check.

### Native build caches

Native jobs restore Cargo downloads and compiled host/cross-target artifacts.
iOS also restores Xcode's content-addressed compiler cache, shared by the SDK
and app builds. The wrapper explicitly enables
`COMPILATION_CACHE_ENABLE_CACHING`, uses a repository-local
`target/xcode-compilation-cache`, and emits compiler cache remarks. It always
checks/builds current sources before running tests. See Apple's
[build settings reference](https://developer.apple.com/documentation/xcode/build-settings-reference).

These caches are partitioned by OS, architecture, pinned Apple SDK/NDK and Rust
dependency/toolchain inputs. A commit-specific key with a compatible restore
prefix lets successful main runs publish updated build state. Only successful
main jobs save them; PRs restore without writing. Explicit paths exclude
xcresults, app DerivedData, simulator/device state, generated bindings and
release bundles. Cargo and Xcode still validate compilation inputs, and packaging
always regenerates the bindings and libraries from the current sources.

Android enables Gradle's local task-output build cache. Dependencies, compiled
build scripts, transforms, wrapper distributions and that build cache are also
in the explicit GitHub cache, keyed additionally by JDK/Gradle build inputs.
The official [setup-gradle action](https://github.com/gradle/actions/blob/main/docs/setup-gradle.md)
validates the wrapper and uses its documented `external` cache-provider mode
to avoid a second cache for the same files. Commit-specific entries refresh task
outputs from successful main runs, with PRs restoring read-only. This avoids the
basic provider's immutable build-file-only cache while keeping storage in GitHub.
No remote Gradle service, Build Scan publication or configuration-cache secret
is needed. Monitor archive size/restore time and GitHub's cache eviction; don't
raise cache storage budgets without first measuring the benefit.

Test execution is never conditional on a cache hit. Android's managed test task
still uses `--rerun`, and iOS still executes `test-without-building` after a fresh
build check. Caches reduce downloads/compilation; boot and interaction time
remain. First use and evicted caches must work cold. The initial successful main
run seeds caches for subsequent PRs; a cold PR cannot demonstrate cross-run
hosted savings before that seed exists. Inspect restore/save logs and compiler
remarks alongside the phase metrics before claiming a speedup.

### October 20 local measurement

On the same iPhone 18 Pro / iOS 27.0 development simulator, the earlier serial
27-test result session took **597s**; the split, two-worker full session took
**345s** (**358s** for the complete wrapper including its warm build). All 27
cases passed. The four UI plus seven direct-test smoke plan took **78s** with
one worker, and direct app tests alone took **5.3s**. The 20 existing UI test
method bodies were preserved unchanged when splitting the classes. On the
managed Android 17 profile, all 30 app tests passed in **83s** including dependency
recompilation, and both SDK cases passed in **19s**.

With compilation caching enabled, cleaning app build outputs and rebuilding
produced **23/23 Xcode compiler-cache hits**, followed by all seven direct app
tests passing. Cleaning both Android modules and assembling again restored
**67 Gradle tasks from cache** (1s reported build, versus 9s while populating it).
These checks demonstrate local cache reuse after clean builds, not hosted
cross-run restore performance.

These are single local development observations, not a promised CI speedup or
an isolated parallelism benchmark: screenshot capture is also now opt-in, and
boot/build caches differ between runs. Use the uploaded phase and per-test
metrics to assess cold hosted results before reducing any required coverage.

### Hosted worker budget

The initial two-worker hosted iOS run took about 24 minutes in test execution
and failed two UI timing checks (viewport settling and keyboard dismissal). It
did not reproduce the local parallelism gain. Hosted CI therefore explicitly uses
`--workers 1`, preserving all 27 app tests and their assertions. Local full runs
still default to two workers. Do not raise hosted concurrency again without
repeatable hosted timing and reliability evidence. Build caching remains enabled.

The first serial hosted run passed 26/27 app tests in about 21 minutes of test
execution. The remaining recorded-benchmark failure was the keyboard-dismissal
predicate's five-second deadline: hosted accessibility queries consumed the
budget, while the diagnostic immediately afterward showed no keyboard and the
rest of the recorded-swim flow passed. That predicate now has a 15-second
budget, still requiring both visible keyboard content and the entry toolbar to
be gone. It completes as soon as those conditions hold; no sleep, retry or
assertion removal is introduced.
