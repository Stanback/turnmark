# Turnmark SDK, embeds, native apps, and agent interfaces

Research date: October 17, 2026. This is the original design/research record.
The [current implementation](#current-implementation) below supersedes its
earlier milestone/status wording.

## Direction

Build native iOS and Android apps with equal product scope from the start:
Swift/SwiftUI on iOS and Kotlin/Jetpack Compose on Android. Use the current
Svelte web app as the first SDK consumer and add an embeddable calculator in
the same repository. The web framework is an open choice; SDK consumers do
not need Svelte, and a later web UI can be evaluated independently.
React Native, Expo, and webview app shells are outside the requested direction.
The owner already has an Apple Developer account.

**Recommendation:** share the calculation contract, source data, and conformance
tests immediately. Evaluate a small Rust calculation engine with generated Swift
and Kotlin bindings and a WebAssembly-backed JavaScript SDK before committing
to that engine for production. Keep navigation, controls, persistence, sharing,
accessibility, and lifecycle handling in each platform's native code.

The target is one authoritative calculation engine and canonical dataset, with
derived libraries for Swift, Kotlin, and JavaScript. Rust would serve numerical
consistency and SDK distribution here. There is no measured calculation-
performance problem in the existing application. Evaluate build, distribution,
and debugging costs while preserving the single-source requirement; permanent
independent domain implementations are outside that target.

## What the research establishes

### The native direction has current, concrete precedent

On September 10, 2026, Shopify described its return from React Native to Swift
and Kotlin. Its rationale was that improved development tools changed the cost
of maintaining two implementations; it still described React Native as a
successful choice for its earlier needs. Its Shop team reported a 12-week
migration. These are company-specific reports, not evidence that every app
should follow the same stack or schedule. Turnmark's native direction is a
product decision, supported by direct access to platform tools and UI behavior.
[Shopify's decision](https://shopify.engineering/back-to-native),
[Shop migration](https://shopify.engineering/shop-app-migration).

Apple recommends SwiftUI for new Apple-platform apps, and Google recommends
Jetpack Compose for native Android UI. Use those tools while sharing the swim
domain below the UI layer.
[Apple's overview](https://developer.apple.com/documentation/technologyoverviews/swiftui),
[Android's overview](https://developer.android.com/compose).

### There is an existing publisher use case

The current [SwimSwam converter](https://swimswam.com/swimming-times-conversion-tool/)
credits Stanback’s original converter and describes Colorado Timing conversion factors. This
was verified in the page's publicly served HTML. Turnmark currently documents
NCAA factors and its own derived reverse/cross-metric estimates. A publisher
migration therefore needs a methodology explanation and examples of changed
results. Do not market the new calculator as numerically interchangeable with
the old one, or silently introduce a legacy formula into the new engine.

No publisher has been contacted and no integration commitment is assumed.

## Existing code and the extraction boundary

The starting point is the application at commit `a0e73d4`:

| Existing code                                       | Destination or responsibility                                                                                   |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `src/lib/swim.ts`                                   | Separate time parsing, event mapping, conversion, altitude, and youth benchmarks from UI helpers and URL state. |
| `src/lib/points.ts` and `masters.ts`                | Domain operations with explicit dataset versions and availability results.                                      |
| `src/data/*.json`, `conversions.ts`, import scripts | One reviewed set of numerical snapshots, schemas, provenance, and source-update tooling.                        |
| `src/App.svelte`                                    | Keep web interaction, history, storage, scroll behavior, clipboard, and downloads in the web app.               |
| `src/main.ts`, `scripts/finish-build.mjs`           | Web bootstrap, prerendering, metadata, and PWA caching; do not export these from an SDK.                        |
| Existing unit and browser tests                     | Preserve behavior and promote independent examples into portable conformance fixtures.                          |

Most calculation helpers already avoid the DOM. However, `swim.ts` imports the
youth standards table even for conversion-only consumers, and also contains
share-link, CSV, and display helpers. A public SDK needs narrower entry points
and runtime validation: internal TypeScript types do not validate arbitrary
JavaScript, Swift, or Kotlin input.

The existing convention represents freestyle distances internally as 400/800/1500
and maps them to 500/1000/1650 yards. The public contract should accept the
actual event distance and course, normalize once, and reject ambiguous or invalid
combinations. See [the draft SDK contract](SDK_DESIGN.md).

## Shared engine options

All three options below retain native SwiftUI and Android Compose screens.
These assessments are engineering judgments for this repository, not benchmark
results.

| Engine strategy                                              | Benefits for Turnmark                                                                                                     | Costs and decision                                                                                                                                                                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rust + UniFFI for mobile; Rust + wasm-bindgen for web        | One calculation implementation; generated Swift/Kotlin API; reusable native and npm distributions.                        | Adds cross-compilation, binary packaging, FFI, and WebAssembly initialization. Recommended first experiment.                                                                                                   |
| Swift and Kotlin implementations; existing TypeScript engine | Straightforward platform debugging; small calculations remain ordinary platform code; smallest binding/toolchain surface. | Three implementations can drift. Shared data, independent fixtures, and a parity gate are mandatory. Rejected for the single-source requirement; independent platform formulas are not an acceptable fallback. |
| Kotlin Multiplatform domain library with native UIs          | Shared domain implementation across mobile; Kotlin is already needed for Android.                                         | Still needs Apple integration and a decision about JavaScript SDK output. Consider if Kotlin ownership is preferred; test the actual export path rather than assuming all Swift interop is equally mature.     |

[UniFFI](https://mozilla.github.io/uniffi-rs/latest/) generates bindings for Rust
libraries and supports Swift and Kotlin; packaging those libraries remains our
responsibility. Its [Swift guide](https://mozilla.github.io/uniffi-rs/latest/swift/overview.html)
also notes Swift concurrency limitations. Keep this small calculation API
synchronous and value-based, and verify it with the selected Swift compiler.

Rust has documented [iOS targets](https://doc.rust-lang.org/rustc/platform-support/apple-ios.html).
For web distribution, [wasm-pack](https://rustwasm.github.io/docs/wasm-pack/commands/build.html)
supports distinct bundler, browser, and Node targets. A successful native build
does not prove a usable browser package; both need independent verification.

[Kotlin Multiplatform](https://kotlinlang.org/docs/multiplatform/multiplatform-share-on-platforms.html)
can share selected logic while leaving platform-specific code in each app.
Its direct [Swift export](https://kotlinlang.org/docs/native-swift-export.html)
is currently labeled Alpha. That statement concerns this export mechanism,
not the maturity of Kotlin Multiplatform as a whole.

### Rust experiment: acceptance criteria

Start with time parsing, the NCAA 200 LCM breaststroke example, event-distance
mapping, an unsupported event, one altitude boundary, and a points example.
Keep datasets and test cases identical across bindings. This is an experiment
with bounded scope, not a second production engine to maintain indefinitely.

Before selecting Rust, demonstrate:

1. A fresh-checkout build produces an iOS device/simulator library and a Swift
   package or XCFramework, an Android library with Kotlin bindings and packaged
   native binaries, and browser/Node SDK artifacts. Pin the supported toolchains
   and test current Android native-library packaging requirements.
   In particular, exercise Android's
   [16 KB page-size support](https://developer.android.com/guide/practices/page-sizes)
   for the packaged Rust libraries and dependencies.
2. SwiftUI and Compose sample screens call the same Rust operation, with no
   JavaScript runtime in either native app. A browser and Node consumer call
   the WebAssembly build through typed JavaScript wrappers.
3. The same fixture inputs yield identical public outputs, availability codes,
   and integer hundredths/points on all targets. Expand to full event and data
   coverage before migrating production.
4. Bad inputs produce ordinary typed results or documented errors. No user
   input can trigger a Rust panic across the language boundary. Test error
   propagation and ownership/lifetime behavior in the generated wrappers.
5. Record cold/warm build time, incremental edit time, package size, compressed
   browser payload, initialization time, and a reproducible debugging example.
   Measure on real hardware before making a performance claim.
6. Browser CSP, WebAssembly loading, offline packaging, and SSR/Node imports work
   without requiring cross-origin isolation or hidden network requests.

If these criteria fail, investigate another shared-engine approach against the
same contract and single-source requirement. The separate implementation option
in the comparison table is background research, not the selected fallback.
Keep the native UI direction fixed.

## Proposed monorepo

Introduce directories as real consumers arrive; the following is a target
structure, not a request to generate empty packages:

```text
apps/
  web/                       existing Svelte app and PWA
  embed/                     compact publisher calculator, static hosting
  ios/                       SwiftUI application and platform integrations
  android/                   Kotlin/Jetpack Compose application
packages/
  sdk/                       public JavaScript/TypeScript API
  mcp/                       local MCP server using the SDK
  webmcp/                    optional browser tool registration using the SDK
  widget/                    optional loader/custom element, after iframe v1
  data/                      reviewed snapshots, schemas, attribution
crates/
  turnmark-core/             pure Rust engine, if the experiment passes
  turnmark-bindings/         UniFFI API and packaging support
  turnmark-wasm/             wasm-bindgen adapter
fixtures/                    portable input/output cases and source references
scripts/                     data imports and release tooling
docs/                        methodology, SDK, embedding, architecture
```

Keep npm and the existing lockfile for JavaScript work, with
[npm workspaces](https://docs.npmjs.com/cli/v11/using-npm/workspaces/). Cargo,
Swift Package Manager/Xcode, and Gradle remain their respective platform build
systems. Root scripts can coordinate them; a task orchestrator can wait until
build times justify it. A monorepo does not require every test run to build
every platform.

Initially extract `packages/sdk` and portable fixtures without moving the web
app. Move the app in a separate change: its Vite base, prerender imports, public
assets, data import paths, tests, workflow artifact path, and service worker
scope all need review. Preserve `/turnmark/` and existing share URLs throughout.

UI theme values may share a small token source, but each app should own its
native components, text scaling, focus, navigation, safe areas, and platform
conventions. Feature parity means equivalent user capabilities and calculations,
not identical controls or screen layouts.

## Publisher embed and distribution

Ship an iframe-based calculator first: a CMS editor should be able to paste a
snippet without a JavaScript build step. Give it a compact conversion-focused
layout, optional benchmark/points panels, theme settings, an accessible title,
a source/methodology link, visible Turnmark credit, and an open-in-app link.
Reserve space before loading and provide a useful fallback link.

An iframe isolates page styles and execution context. A later
[Svelte custom element](https://svelte.dev/docs/svelte/custom-elements) can offer
closer visual integration for developers who want it. Shadow DOM helps with
styles, but does not isolate script permissions from the host page. Treat the
two distribution modes as different integration contracts.
[MDN's embedding guidance](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content/General_embedding_technologies),
[script versus iframe context](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API).

Embed requirements:

- Version the embed protocol and publish immutable release assets. Let
  publishers choose an explicit upgrade policy; avoid an unversioned remote
  script whose behavior can change unexpectedly.
- No accounts, analytics, cookies, or automatic history persistence in embed
  mode. Calculate in memory and work when browser storage is denied. Embedded
  storage may be blocked or partitioned; do not require access prompts.
  [Storage behavior](https://developer.mozilla.org/en-US/docs/Web/API/Storage_Access_API).
- Use a small, validated `postMessage` protocol for resize and explicit
  configuration. Check sender origin, window identity, protocol version,
  instance ID, and payload shape. Bound reported dimensions. Use exact target
  origins; do not broadcast swim inputs or expose saved history to the parent.
  [Messaging guidance](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage).
- Review sandbox permissions, CSP `frame-src`/`frame-ancestors`, and clipboard
  permissions with the final hosting setup. Do not promise automatic resizing
  or copying on every CMS without testing it. Plain iframe mode should still
  work at a documented fixed height when a CMS strips the helper script.
- Keep the widget independent of the full site's service worker, URL mutation,
  global CSS, and storage keys. Multiple instances on one page must work.
- Provide an embed playground, copyable snippets, a plain HTML example, and
  a WordPress/editor guide. A dedicated plugin can follow actual demand.
- Offer self-hosting and a downloadable bundle. Hosted assets still create
  normal HTTP requests to the host even when calculations stay local; describe
  that accurately in publisher privacy documentation.

Package the SDK with types, explicit exports, and separate conversion, youth,
Masters, and points imports so small consumers do not load every dataset.
[Vite library mode](https://vite.dev/guide/build.html#library-mode) is an option
for the JavaScript facade. Test installed tarballs in separate browser and Node
projects, rather than trusting workspace imports. Use scoped package names only
after checking registry ownership. Publication is a later release step; use
[npm trusted publishing](https://docs.npmjs.com/trusted-publishers/) when configured.

## MCP and WebMCP

Add two agent interfaces around the same Rust-backed SDK: a local MCP server
for assistant clients, and optional WebMCP tools on the active website. Share
tool contracts for conversion, altitude, youth/Masters benchmarks, points and
source metadata. Keep the SDK's explicit inputs, availability/validation states,
precision and provenance; do not create another calculation implementation.

MCP now supports offline stdio and stateless Streamable HTTP on its own
Cloudflare Worker at `mcp.turnmark.app`. The website and publisher iframe use
a separate static-assets Worker at `turnmark.app`; legacy GitHub Pages has been
retired. Treat WebMCP as progressive
enhancement with feature detection and browser-version checks, since its API
is still evolving. Native feature parity remains the next implementation
milestone; agent adapters follow in focused PRs with the embed work. See the
[agent interface plan](AGENT_INTERFACES.md) for tool scope, protocol research,
packaging and acceptance checks.

## Native product quality and parity

Build a pool-deck utility: fast time entry, immediately readable comparisons,
clear original-versus-estimated results, a local swimboard, and offline source
tables. Avoid turning the first release into a training platform.

| Capability          | iOS and Android requirement                                                               |
| ------------------- | ----------------------------------------------------------------------------------------- |
| Calculator          | Same accepted events, precision, factors, missing cases, and category semantics.          |
| Standards/points    | Same snapshot editions, validity labels, and original-course rules.                       |
| Saved swims/history | Device-local persistence, deletion, restart/process-death tests, and export.              |
| Sharing             | Native share sheet/chooser; versioned links readable by the web app.                      |
| Accessibility       | VoiceOver and TalkBack labels/order; platform text scaling, contrast, and reduced motion. |
| Navigation/input    | Appropriate keyboard, visible validation, keyboard dismissal, and platform back behavior. |
| Offline             | Fresh installed app works in airplane mode, with no first-launch asset download.          |
| Releases            | Both platform suites pass before a shared feature is considered complete.                 |

Keep storage implementations native, outside the engine. Use small preference
stores for settings and choose a structured local store only when the swimboard
needs it. Do not assume browser storage migrates into a native app automatically;
plan an explicit export/import format. Preserve existing web links, then add
verified app/universal links when domain ownership and association hosting are
available.

The next native workflow is [offline meet history](MEET_HISTORY.md): log actual
swims with convenient meet/date context, browse progress and export/import
records. Keep saved calculations distinct from recorded performances and
exclude estimates from personal bests.

Association files live at the host's well-known location, not under the app's
`/turnmark/` project path. Plan a custom domain or root-site hosting controlled
by the owner before promising verified links; test both installed and uninstalled
app behavior.
[Apple associated domains](https://developer.apple.com/documentation/xcode/supporting-associated-domains),
[Android App Links verification](https://developer.android.com/training/app-links/verify-applinks).

Apple's model-data guidance and Android's architecture guidance both support
separating application state from presentation. Keep the shared engine stateless
and pass values through small platform adapters.
[SwiftUI model data](https://developer.apple.com/documentation/swiftui/managing-model-data-in-your-app/),
[Android architecture](https://developer.android.com/topic/architecture/recommendations).

Later platform additions can include a saved target widget and quick conversion
actions. Apple [App Intents](https://developer.apple.com/documentation/AppIntents)
supports integrations such as Shortcuts. Specify an equivalent Android user
outcome before scheduling a feature; native implementations may differ.
Watch apps, workout tracking, cloud sync, social features, and HealthKit/Health
Connect integrations are separate product decisions.

## Distribution decisions to resolve before release

### License and source-data rights

Application code currently uses GPL-3.0-or-later. That is a material decision for
an SDK intended for broad third-party adoption, especially proprietary products.
The FSF describes GPL library linking obligations in its
[FAQ](https://www.gnu.org/licenses/gpl-faq.html#IfLibraryIsGPL). It also explains
that copyright owners can offer their own code under additional licenses in the
[dual-licensing FAQ](https://www.gnu.org/licenses/gpl-faq.html#ReleaseUnderGPLAndNF).

Consider a permissive SDK/core license, dual licensing, or keeping the present
terms. Choose based on the intended adoption model after verifying authorship
and third-party rights. The visible Git history currently lists one author;
that is not a complete rights audit. Do not automatically relicense the project,
invent a linking exception, or assume a Rust rewrite changes existing rights.

GPL/App Store distribution also needs an explicit licensing review. The FSF's
[VLC account](https://www.fsf.org/blogs/licensing/vlc-enforcement) documents a
historical conflict; Apple's current
[developer agreement](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/)
requires compliance with included open-source licenses. Those sources identify
the question; they do not determine the legal outcome for this app. Ownership,
dependencies, distribution terms, and any additional permissions must be checked
for the actual release.

Published numerical snapshots, source documents, fonts, and other assets require
their own attribution/redistribution review. Keep provenance, retrieval/revision
dates, hashes, and coverage metadata. Do not assume licensing the engine grants
rights to source organizations' documents or branding.

### Store readiness

Apple's guidelines require useful app functionality beyond a repackaged website,
complete metadata, and an in-app and store-linked privacy policy. Native code
alone does not guarantee approval. Describe and demonstrate offline calculations,
saved targets, and native sharing in review notes.
[App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/).

Review actual data flows and dependencies before declaring privacy practices.
Apple says purely on-device processing is not collected data for its privacy
answers; user-initiated exports and any added remote services need their own
assessment. Privacy manifests and required-reason API declarations are a separate
check from the store label.
[App privacy details](https://developer.apple.com/app-store/app-privacy-details/),
[privacy manifests](https://developer.apple.com/documentation/BundleResources/privacy-manifest-files).

Track Android's current target SDK requirement, native binary requirements, Play
Console verification/testing, signing, and Data safety answers alongside Apple's
requirements. Select supported OS versions from framework and device needs;
recheck store rules at release time rather than freezing this research as policy.
[Android target requirements](https://developer.android.com/google/play/requirements/target-sdk),
[Android quality guidance](https://developer.android.com/quality/user-experience).

## Implementation sequence

1. **Portable contract and SDK extraction.** Define public event/time/error
   semantics, extract the existing TypeScript calculation boundary, and create
   independently checked conformance fixtures. Keep current web behavior passing.
   Decide SDK licensing before public publication, not before local experiments.
2. **Native engine experiment.** Prove Rust → Swift, Kotlin, browser, and Node
   distribution with the same small operation set. Record build/debugging costs
   and payload sizes; record a shared-engine decision in a short
   architecture decision record.
3. **First complete experience on both native platforms.** Ship a testable
   converter plus source attribution, a saved target, and native sharing on iOS
   and Android together. Run fixtures through the real platform bindings, then
   test UI behavior on physical devices. Use TestFlight and Android internal
   testing before store launch.
4. **Publisher embed.** Build the compact iframe experience against the same SDK
   contract. Validate a hostile-style host page, restricted storage, multiple
   instances, narrow viewports, keyboard/screen-reader use, and a real CMS preview.
   Keep attribution and methodology visible.
5. **MCP and WebMCP adapters.** Expose the same SDK operations through a local
   MCP server and optional browser tools. Reuse tool contracts, preserve source
   attribution and missing-data semantics, and test real protocol consumers plus
   browsers without WebMCP. Keep calculations read-only in the first release.
6. **Monorepo completion and releases.** Move the web app separately, establish
   artifact packaging/release jobs, document integrations, and expand native
   coverage to the full existing web capability set before claiming parity.

The first acceptance milestone is one swim yielding the same documented answer
through the SDK, web app, embed, native iOS app, and native Android app. Complete
data and edge-case parity follows before production engine replacement.

## Open decisions

- First supported iOS/Android versions and available physical test devices.
- Publisher upgrade policy and initial partner feedback.
- Store price and support model; keep subscriptions/accounts out of the first
  implementation unless separately chosen.

## Current implementation

Rust is the single calculation implementation, with canonical snapshots in
`data/`, typed generated Swift/Kotlin libraries and a Wasm-backed JavaScript SDK.
The web UI, native UI and agent/publisher adapters retain their own platform
state and controls. SDK consumers do not require Svelte.

| Surface          | Current scope                                                                                                                                           | Details                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| SDK              | Published JavaScript 0.1.0; shared Rust/native bindings; benchmark assessment and Colorado method in unreleased SDK 0.2.0                               | [Engine](SHARED_ENGINE.md), [SDK](../packages/sdk/README.md), [release status](SDK_RELEASES.md) |
| Web              | Converter, standards/points, browser-local history, offline installation                                                                                | [Live app](https://turnmark.app/)                                                               |
| Publisher widget | Versioned isolated iframe, light/dark/device appearance and copyable setup                                                                              | [Setup](https://turnmark.app/embed/)                                                            |
| Native apps      | SwiftUI/Compose converter, offline My times/import/export, Standards & points including B–AAAA, adaptive layouts                                        | [Native scope](NATIVE_APPS.md), [standards review](NATIVE_STANDARDS_REVIEW.md)                  |
| MCP              | Published stdio 0.2.0 and hosted Streamable HTTP, six published npm tools / seven source/hosted tools, official Apps card with text/structured fallback | [MCP](MCP.md), [Apps review](MCP_APPS_REVIEW.md)                                                |
| WebMCP           | Planned, separate from the MCP Apps iframe extension                                                                                                    | [Agent interfaces](AGENT_INTERFACES.md)                                                         |

The source has 117 portable fixtures and a 7,405-case cross-runtime corpus.
Packed artifacts are tested outside the monorepo. The native apps remain
development builds: physical devices, screen readers, signing/store metadata
and beta/submission are release work. Standalone SwiftPM/Maven registry releases
and native altitude entry are also follow-ups. Public npm versions and prepared
changes are distinguished in the release documentation; an implementation plan
is not evidence of registry publication or store approval.

## Product scope and anti-goals — October 19, 2026

The October 18 exploration of a general swim logger, cloud synchronization and
coach features is withdrawn. Turnmark stays a focused offline conversion,
standards and points utility. Existing local records, saved comparisons and
portable export/import remain supported; this decision does not remove data or
turn estimates into recorded performances. Do not expand personal-best tracking,
accounts, cloud infrastructure, recruiting or coach dashboards under this plan.

Link to established result/profile services through a small resources section
instead of building a competing results database. NCAA remains the default
conversion method; alternative published methods belong in a quiet advanced
setting, with the selected method preserved in shared comparisons and clearly
identified in the calculation details.

A separate conversion-model research experiment on the follow-up branch
`research/conversion-model` may
evaluate matched real swims against NCAA and legacy Colorado baselines. It is
an offline development experiment, not a replacement default, an accepted-entry
mode, a physiological assessment or a promise of improved accuracy. A production
model needs independent held-out evaluation and an explicit later decision.

Anti-goals for now: a general swim logger, expanded personal-best tracking,
automatic meet-result aggregation, cloud accounts/sync, recruiting and coach
features. Existing local records and export/import are maintenance scope.

## Converter layout follow-up

Explore a clearer grouping of swim inputs, course equivalents and the next
published target with subtle ambient effects. The [layout study](CONVERTER_LAYOUT_EXPLORATION.md)
keeps this separate from statistical-model research. Refresh the root README’s
actual-build screenshots in that same PR: lead with the converter and retain
paired native Convert/home previews, making the method choice discoverable
without letting an open menu obscure the main view. The study remains a draft;
this plan does not claim a redesigned layout has shipped.
