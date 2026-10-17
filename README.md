# Turnmark

**Your swim. Any course.**

[Try Turnmark →](https://stanback.github.io/turnmark/)

A browser-only swim time converter, standards explorer, and World Aquatics points calculator. Built for swimmers, coaches, and parents who want to understand a swim across pool courses and find a useful next target.

- Live SCY / SCM / LCM comparisons with event-specific distance mapping
- Published NCAA metric-to-yards factors, with explicitly labeled derived reverse conversions
- 2,892 published USA Swimming 2024–2028 motivational times, revised October 10, 2025
- Original-course standards ladder with the next level and time gap
- World Aquatics points from 70 published 2026 metric base times
- Automatic, device-local conversion history with stroke filters, restore, remove, and clear
- 904 published 2026 USMS Nationals targets for adults, with explicit SCY/LCM and age-group coverage
- Optional USA Swimming altitude adjustments with feet/meters input and an explicit sea-level comparison
- Shareable URL fragments, CSV export, and an optional local swimboard
- Automatic system light/dark mode with a saved appearance override
- Installable desktop/mobile app with offline calculations and bundled tables
- Pre-rendered introduction and expandable FAQs, canonical/social metadata, and app structured data
- Responsive layouts, keyboard controls, reduced-motion support, and self-hosted fonts

No backend, account, analytics, third-party runtime requests, or uploaded swim data. Conversion history and saved swims stay in this browser’s local storage. Sharing a link shares the event, time, category, age group, and elevation contained in its URL fragment.

## Develop

Requires Node.js 22.12+ (or a current supported Node release).

```sh
npm ci
npm run dev
```

The app is served at `http://localhost:5173/turnmark/`. Production hosting is configured for GitHub Pages at `/turnmark/`; change `base` in `vite.config.ts` for another host.

```sh
npm run check
npm test
npx playwright install chromium
npm run test:browser
npm run test:sdk:package
npm run test:production
npm run build
npm run preview
```

The production app is static files in `dist/`. The GitHub Actions workflow checks types, unit tests, desktop/mobile browser interactions and accessibility before deploying to GitHub Pages.

The web app consumes the private [Turnmark SDK workspace](packages/sdk/README.md),
which contains the current web calculations and generated copies of root `data/`
snapshots. `npm ci` and
the normal development/check/build commands compile it automatically. The SDK
has no framework or runtime dependencies; optional benchmark datasets have
separate imports. Portable examples live in [fixtures](fixtures/README.md).
See the [platform plan](docs/PLATFORM_PLAN.md) for native SwiftUI/Android Compose
apps and publisher embeds; these are ongoing work, and the SDK is not published.

The experimental [shared Rust engine](docs/SHARED_ENGINE.md) now generates Swift,
Kotlin and WebAssembly libraries. Its iOS/Android packages run in simulator/emulator
tests; native app screens and the production web migration are still in progress.
The guide includes pinned tools, build commands, evidence and remaining gates.

## Data and calculations

Read [the methodology](docs/METHODOLOGY.md) for sources, rounding behavior, coverage, and limitations, and [the data maintenance guide](docs/DATA.md) for updating the tables. Inputs and original-course benchmarks are separated from course estimates. A converted time is not an official swim or a guarantee of meet-entry eligibility.

Application code is licensed under GPL-3.0-or-later. Published numerical data remains attributed to its respective source organizations. Turnmark is an independent project and is not affiliated with or endorsed by NCAA, USA Swimming, U.S. Masters Swimming, or World Aquatics.

## Community

Bug reports, data corrections, accessibility improvements, and pull requests are welcome.
Read the [contributing guide](CONTRIBUTING.md) for setup, checks, and source-data requirements,
and follow the [code of conduct](CODE_OF_CONDUCT.md). Use the
[issue templates](https://github.com/Stanback/turnmark/issues/new/choose) to report a problem
or suggest an improvement. Report vulnerabilities privately as described in the
[security policy](SECURITY.md). The full application license is in [LICENSE](LICENSE).

## Install and offline use

Your age groups, standards selection, category, swum-in course, elevation, and ft/m choice are remembered in this browser. Restored elevations stay visible in the expanded elevation panel. A shared conversion link overrides remembered swim settings, including altitude. Race time, stroke, and distance start fresh; conversion history keeps past swims. Reset restores the app defaults and updates remembered preferences. Preferences stay on this device and work without an account.

Chrome and Edge can install Turnmark from the address bar/browser menu; the app’s Install button invokes the native prompt when available and otherwise shows instructions. Safari on iPhone/iPad supports Share → Add to Home Screen. Icons include 192px/512px PNGs, a maskable icon, and an Apple touch icon. The manifest and service worker are scoped to `/turnmark/`.

Once an online visit completes caching, calculations, standards, history, and saved swims work without a connection. Source links still need the internet. Browser-managed storage may be cleared or evicted; this is not cloud backup. New static builds are cached separately; a waiting service worker activates after existing app tabs close. The network is preferred for document navigation, so online visits receive the current release. Offline navigation retains the complete active build until a new worker activates, keeping its HTML and asset revisions together.

## Discoverability

The build pre-renders the actual Svelte page and FAQ answers, then hydrates it in the browser. A backend is not needed. Metadata lives in `index.html` and `src/data/site.ts`; `scripts/finish-build.mjs` emits app JSON-LD and `dist/sitemap.xml`. Keep the production URL, Vite base, manifest scope, and service worker base consistent if moving hosts. No search indexing or answer-engine placement is guaranteed, and no Search Console submission is performed automatically.
