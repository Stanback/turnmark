# Working on Turnmark

Turnmark is an offline swimming utility with a shared SDK, a web app, and native
iOS and Android apps. Read [CONTRIBUTING.md](CONTRIBUTING.md) for contribution
and source-data conventions. `CLAUDE.md` is a symlink to this file; maintain
instructions here.

## Architecture

- `crates/turnmark-core/` owns calculations, time parsing, semantic validation,
  event mappings, coverage states and provenance. `data/` owns canonical
  numerical snapshots and source metadata.
- `packages/sdk/` adapts the Rust/Wasm core for JavaScript. `packages/swift/`
  and `packages/android/` package generated UniFFI bindings and native libraries.
  Regenerate bindings and copied data with the scripts; do not hand-edit them
  or introduce another calculation implementation.
- `src/` is the current Svelte web app. `apps/ios/` uses SwiftUI;
  `apps/android/` uses Kotlin and Jetpack Compose. Keep both native platforms on
  equal footing. Use their native UI, lifecycle, persistence and sharing APIs.
- Keep the engine stateless. Device storage and application state belong to
  consumers, outside the numerical core.
- See [SHARED_ENGINE.md](docs/SHARED_ENGINE.md) for SDK ownership and packaging,
  [NATIVE_APPS.md](docs/NATIVE_APPS.md) for current native scope and setup, and
  [PLATFORM_PLAN.md](docs/PLATFORM_PLAN.md) for future work. Plans are not shipped
  features; keep that distinction clear in documentation.
- Native [offline meet history](docs/MEET_HISTORY.md) uses the portable contract
  in [apps/history](apps/history/README.md); keep both adapters and fixtures aligned.
  Existing saved conversions must not silently become recorded race results.

## Product conventions

- Native navigation is Convert and My times; Record time confirms an actual
  performance. See [native product notes](docs/NATIVE_PRODUCT_NOTES.md) for
  workflow intent and the distinction between entry preparation and eligibility.
- Preserve the entered swim separately from converted estimates. Estimates
  must not become recorded performances or personal bests. Qualifying targets
  are benchmarks, not confirmation of entry eligibility.
- Use the SDK's returned event for result context: a destination's distance can
  differ from the entered distance. Show enough event, course, category and
  unit context to make a time understandable. Keep entered/published/derived
  labels visible and make source editions accessible.
- Preserve `available`, `unavailable` and `invalid` outcomes. Missing published
  data stays missing; do not invent targets, factors or unsupported events.
- Core workflows work offline, including first launch. Keep personal swim data
  local by default. Sharing and future agent integrations need explicit inputs
  and clear ownership of any data they access.
- Favor direct time entry and readable results. The converter has no app-name
  banner or decorative heading. Use the wave identity for app icons and
  platform launch behavior; keep copy concrete. See [BRANDING.md](docs/BRANDING.md)
  and [NATIVE_DESIGN_REVIEW.md](docs/NATIVE_DESIGN_REVIEW.md).
- Follow [the shared design contract](docs/DESIGN_CONTRACT.md) for semantic
  colors, spacing, result hierarchy and platform adaptations. Change canonical
  values in `design/turnmark.tokens.json`; regenerate the committed CSS, Swift and Kotlin outputs
  with `node design/generate.mjs`. Consumer adoption is tracked there;
  do not claim parity from the web adapter alone. Native system controls,
  accessibility behavior and logical text styles remain platform-owned.
- Preserve native text scaling, accessible labels/order, keyboard dismissal,
  light/dark appearance and reduced-motion preferences. iOS uses system Liquid
  Glass controls on supported versions; numerical cards retain readable opaque
  surfaces.

## Making and checking changes

- Follow existing code style and keep changes focused. Check the relevant docs
  before changing data or methodology. Source changes need an official source,
  edition, reproducible example and corresponding metadata/test updates.
- Use the pinned toolchains and lockfiles. Run checks appropriate to the change;
  documentation-only work does not require application tests.
- Follow [CI.md](docs/CI.md) when selecting affected consumers. Web-only changes
  do not need native builds. Update the shared CI selection rules and their
  tests when introducing a new package, build input or dependency boundary.
- Web: `npm run check`, `npm test`, and relevant Playwright tests
  (`npm run test:browser` / `npm run test:production`). Package/API changes also
  need `npm run test:sdk:package`.
- Core: `cargo fmt --all --check`,
  `cargo clippy --locked --workspace --all-targets --features turnmark-core/native -- -D warnings`,
  `cargo test --locked --workspace --features turnmark-core/native`, and
  `npm run test:engine`. Run relevant native fixture checks when the shared
  contract or bindings change; commands are in the engine guide.
- Native UI: build the affected apps and run `node scripts/test-ios.mjs app`
  and/or `node scripts/test-android.mjs app`. Android needs a fully booted
  emulator/device. The wrappers reject missing or stale test results. A paired
  feature needs both platforms checked.
- Inspect screenshots for visible changes, including dark appearance and text
  wrapping. Use sample data. Automated simulator tests do not replace release
  checks on physical devices or with VoiceOver/TalkBack.
- Regenerate the checked-in Xcode project with
  `xcodegen generate --spec apps/ios/project.yml` when project structure changes.
  Native UI-only changes do not require rebuilding unchanged SDK artifacts.
- PR checks use unsigned/debug builds and read-only repository permissions.
  Keep signing, infrastructure and store credentials out of PR jobs. Website
  deployment and signed store releases have separate workflows and scope.
- Read [HOSTING.md](docs/HOSTING.md) before changing deployment. Keep the
  Cloudflare token in the main-only production environment, scoped to the website
  Worker. Build application code without credentials; deploy the tested static
  artifact from an isolated runner. Never copy IaC or account-wide credentials
  into this repository, job logs or chat.
- The MCP Worker has its own main-only environment and token scoped only to
  `turnmark-mcp`; follow [MCP.md](docs/MCP.md). Keep both Workers on Free unless
  the owner explicitly approves a plan change. Public MCP tools remain
  read-only and accept explicit calculation inputs, without personal history.
- Report what changed, meaningful validation, and remaining limitations. Do not
  claim planned integrations, full native feature parity or store readiness
  from a successful build alone.
