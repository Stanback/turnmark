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
edits skip those checks. SDK changes exercise their MCP consumer.

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
