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
- Optional USA Swimming altitude adjustments
- Shareable URL fragments, CSV export, and an optional local swimboard
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
npm run build
npm run preview
```

The production app is static files in `dist/`. The GitHub Actions workflow checks types, unit tests, desktop/mobile browser interactions and accessibility before deploying to GitHub Pages.

## Data and calculations

Read [the methodology](docs/METHODOLOGY.md) for sources, rounding behavior, coverage, and limitations, and [the data maintenance guide](docs/DATA.md) for updating the tables. Inputs and original-course benchmarks are separated from course estimates. A converted time is not an official swim or a guarantee of meet-entry eligibility.

Application code is licensed under GPL-3.0-or-later. Published numerical data remains attributed to its respective source organizations. Turnmark is an independent project and is not affiliated with or endorsed by NCAA, USA Swimming, or World Aquatics.
