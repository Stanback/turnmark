# Contributing to Turnmark

Thanks for helping improve Turnmark. Bug reports, source-data corrections,
accessibility improvements, documentation, and focused code changes are welcome.
Please follow the [code of conduct](CODE_OF_CONDUCT.md).

## Before you start

- Search [existing issues](https://github.com/Stanback/turnmark/issues) and pull
  requests before opening a new one.
- Use an issue template for bugs, calculation or data corrections, and feature
  requests. Include the smallest example that demonstrates the problem.
- Discuss substantial features or changes to calculation behavior in an issue
  before investing in an implementation. Small fixes can go straight to a pull
  request.
- Report vulnerabilities privately using the [security policy](SECURITY.md).
  Public reports and screenshots should contain only sample swim data, with no
  personal information about swimmers.

## Local development

Use Node.js 22.12+ or a current supported release; CI uses Node.js 24. Fork the
repository, clone your fork, and create a branch for your change. Rust is pinned
in `rust-toolchain.toml`; install the matching Wasm generator first.

```sh
cargo install wasm-bindgen-cli --version 0.2.129 --locked
npm ci
npm run dev
```

Open `http://localhost:5173/turnmark/`. The app uses Svelte, TypeScript, and Vite.
Shared calculations live in `crates/turnmark-core`, numerical snapshots in
`data/`, and the Wasm SDK adapters in `packages/sdk/src/`; web-only
state, display helpers, and their tests live in `src/lib/`. Browser tests live
in `tests/`, and built-app checks in `tests-production/`. Read the
[SDK guide](packages/sdk/README.md) when changing the shared engine or API.
For native app setup and checks, see [the native guide](docs/NATIVE_APPS.md).
[AGENTS.md](AGENTS.md) records the repository conventions for coding assistants;
`CLAUDE.md` points to the same file.

## Making a change

- Keep changes focused and follow the surrounding code style. Format changed
  files with `npx prettier --write <files> --plugin=prettier-plugin-svelte`.
- Keep calculations usable offline and personal swim data on the device:
  no accounts, analytics, or uploaded swim data.
- Preserve keyboard access, accessible labels, responsive layouts, reduced-motion
  support, and both light and dark appearances when changing the interface.
- Add or update relevant tests for behavior changes. For calculation changes,
  cover a published example, rounding or boundary behavior, and unsupported cases
  where applicable.
- Update documentation when behavior, data coverage, setup, or sources change.

For source-data or formula changes, read the [methodology](docs/METHODOLOGY.md)
and [data maintenance guide](docs/DATA.md). Include the official source URL,
edition or validity dates, page/table reference, and a reproducible example.
Review generated snapshots and update attribution, metadata, labels, and tests
together. Preserve missing values rather than inferring unsupported standards,
factors, events, or age groups. Keep converted estimates distinct from actual
swims and original-course benchmarks.

## Checking your work

Run checks for the affected consumers; [the CI guide](docs/CI.md) explains the
dependency boundaries. For web or JavaScript SDK changes:

```sh
npm run check
npm test
npx playwright install chromium
npm run test:sdk:package
npm run test:browser
npm run test:production
```

The production browser suite runs `npm run build` and checks the static build.
You can also build and inspect it manually with `npm run build` and
`npm run preview`. On Linux, Playwright may need system dependencies installed
with `npx playwright install --with-deps chromium`.

For documentation-only changes, check formatting and links; application tests
are unnecessary unless the change also affects app behavior or build inputs.

## Opening a pull request

Use the pull request template to explain the problem, resulting behavior, and
validation. Link related issues and include screenshots for visible changes,
using sample data. Note any checks you could not run. Maintainers may request
changes before merging; contributors do not need deployment access.

Contributions to application code are made under the existing
[GPL-3.0-or-later license](LICENSE). Keep third-party notices and source-data
attribution intact; include only material you have permission to contribute.
