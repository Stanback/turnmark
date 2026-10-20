# Turnmark SDK

Offline course conversion, altitude, USA Swimming standards, USMS targets, and
World Aquatics points, calculated by the shared Rust engine. Swift and Kotlin
libraries are generated from the same core. The JavaScript package is
`@turnmark/sdk`. The published version is `0.1.0`; this checkout prepares `0.2.0`.

Install with `npm install @turnmark/sdk@0.1.0`. A source checkout
can also produce a tested installable tarball with `npm run pack:sdk`; install
`release/turnmark-sdk-0.2.0.tgz` in your consumer project. Consumers need neither
Rust nor package install scripts. The ESM package supports modern browsers and
Node 22.12 or newer.

Initialize explicitly before using any calculation helpers. In an unbundled
browser application, the default loads the packaged WebAssembly asset:

```ts
import { createEngine } from "@turnmark/sdk";

const engine = await createEngine();
const result = engine.convert({
  swim: {
    time: "2:16.71",
    event: { distance: 200, stroke: "breaststroke", course: "LCM" },
  },
  to: "SCY",
  table: "men",
});
if (result.status === "available") {
  console.log(result.value.time); // 1:57.29
  console.log(result.value.hundredths); // 11729
  console.log(result.value.kind); // published
  console.log(result.provenance.url);
}
```

Bundlers should pass their resolved asset URL (for Vite, import
`wasmUrl` from `"@turnmark/sdk/engine.wasm?url"` and call
`await createEngine({ wasm: wasmUrl })`). Workers can pass an imported,
precompiled `WebAssembly.Module` as `wasm`; the MCP Worker exercises this path.
For Node, use the filesystem entry:

```ts
import { createEngine } from "@turnmark/sdk/node";
const engine = await createEngine(); // reads the bundled Wasm; no fetch
```

After initialization every operation is synchronous and offline. Repeated
`createEngine()` calls reuse the loaded module. Failed initialization can be
retried; there is no fallback calculation engine. Direct named exports such as
`convertSwim` and `formatTime` use that initialized module too. Swift/Kotlin
consumers do not load WebAssembly or JavaScript. See the
[shared engine guide](https://github.com/Stanback/turnmark/blob/main/docs/SHARED_ENGINE.md) for native packaging.

## Entry points

| Import                     | Operations                                                              |
| -------------------------- | ----------------------------------------------------------------------- |
| `@turnmark/sdk/node`       | Same engine/API, with local Wasm loading for Node.                      |
| `@turnmark/sdk`            | Engine, conversion, altitude, time helpers, contract types.             |
| `@turnmark/sdk/conversion` | Conversion/altitude operations, source metadata and method identifiers. |
| `@turnmark/sdk/time`       | `parseTime`, `formatTime`, `truncateTime`.                              |
| `@turnmark/sdk/youth`      | `getYouthStandards`, ages, source and edition.                          |
| `@turnmark/sdk/masters`    | `getMastersTarget`, ages, source and edition.                           |
| `@turnmark/sdk/points`     | `getWorldPoints`, next points milestone, source and validity.           |

The Wasm asset currently embeds all numerical tables. JavaScript modules contain
API adapters and generated source metadata, without a second set of calculations. `compat` entry points temporarily support the
existing web UI; new integrations should use the validated APIs above.

## Inputs and results

Courses are `SCY`, `SCM`, `LCM`. Strokes are `freestyle`, `backstroke`,
`breaststroke`, `butterfly`, `individual-medley`. Distances are actual distances:
use `500` with `SCY`, and `400` with `SCM`/`LCM`. Category tables are `women` or
`men`, following the published sources. Input times are positive clock strings
such as `58.32` or `1:02.45`, with up to hundredths and no more than one hour.
Conversion results truncate the final time to hundredths.

```ts
const adjusted = engine.adjustAltitude({
  swim: {
    time: "2:00.00",
    event: { distance: 200, stroke: "freestyle", course: "SCY" },
  },
  elevation: { value: 1828.8, unit: "meters" },
});
```

Elevation units are `feet` or `meters`. Feet must be whole numbers in 0–20,000;
meters are converted once to the nearest foot with exactly 0.3048 m/ft.
Altitude adjustment is explicit and separate from conversion and points input.

```ts
import { getYouthStandards } from "@turnmark/sdk/youth";
import { getMastersTarget } from "@turnmark/sdk/masters";
import { getWorldPoints } from "@turnmark/sdk/points";

const event = { distance: 100, stroke: "freestyle", course: "SCY" } as const;
const youth = getYouthStandards({ event, table: "women", age: "15-16" });
const masters = getMastersTarget({ event, table: "women", age: "18-24" });
const points = getWorldPoints({
  swim: { time: "1:00.00", event: { ...event, course: "LCM" } },
  table: "men",
});
```

Youth lookup returns six times in seconds and B–AAAA labels. Masters lookup
returns clock time, seconds, and hundredths. Points scores the raw entered
metric swim and returns base time, validity, and a derived next 100-point
milestone. These operations do not certify meet-entry eligibility or infer
age-adjusted points.

Request APIs return `available`, `unavailable`, or `invalid`. Unavailable results
include coverage reasons and provenance; invalid results include a field and
validation reason. Explicit USMS `NO TIME` cells produce `no-time-published`,
distinct from absent events, unsupported SCM, and ages 85+. JavaScript inputs
are runtime-validated, with no implicit coercion or fallback method.

## Development

From the repository root:

```sh
cargo install wasm-bindgen-cli --version 0.2.129 --locked
npm ci
npm run build:sdk
npm test
npx playwright install chromium
npm run test:sdk:package
```

`npm run dev --workspace @turnmark/sdk` watches sources. Root dev/build/check/test
commands build the SDK first. Data import scripts update the canonical snapshots
in root `data/`; Rust embeds those tables and builds generate JavaScript source
metadata. The pinned Rust toolchain is selected by `rust-toolchain.toml`. Source-backed portable cases live in the repo's
`fixtures/`. The package check installs a tarball into a temporary project and
validates Node, browser, declaration resolution, and conversion-only bundling.

## Versioning and release

The package and Rust engine start at `0.1.0`. Consumers should pin their SDK
version and retain returned source editions when storing results. During 0.x,
incompatible public API changes increment the minor version; compatible fixes
increment the patch version. Dataset edition updates are documented in release
notes and do not silently replace a published package. The `compat` exports
serve the existing web app and are not the integration contract for new callers.

The initial npm release covers JavaScript/TypeScript. Swift and Android already
use generated libraries from the same engine in this repository; public SwiftPM
binary distribution and Maven publication remain separate distribution work.
See the [release guide](https://github.com/Stanback/turnmark/blob/main/docs/SDK_RELEASES.md)
for the package checks, first publish and token-free subsequent releases.

GPL-3.0-or-later remains in effect. Preserve source attribution, metadata, and third-party
notices. [Methodology](https://github.com/Stanback/turnmark/blob/main/docs/METHODOLOGY.md)
and [data maintenance](https://github.com/Stanback/turnmark/blob/main/docs/DATA.md)
document sources and calculation limitations.

## Original-swim benchmarks (unreleased)

The next SDK release adds `assessSwimBenchmark` at the root entry and
`engine.benchmark`. The published `0.1.0` package does not contain this addition.
It compares the original achieved course with one bundled youth or USMS table;
no course conversion or altitude estimate enters the assessment.

```ts
const outcome = engine.benchmark({
  swim: {
    time: "58.32",
    event: { distance: 100, stroke: "freestyle", course: "SCY" },
  },
  table: "women",
  system: "youth",
  age: "15-16",
});
// Available: A standard; next AA target 56.49, 1.83 seconds away.
```

An available result includes formatted targets, `met` states, the achieved level,
next target and gaps rounded to hundredths by Rust. Source provenance remains
attached. Invalid inputs and missing published targets retain their distinct
outcomes. Meeting a target does not confirm entry eligibility. Native bindings
also expose `getStandardAgeGroups` from the same core; selecting 85+ for the
bundled USMS table produces explicit missing-age-group coverage.

## Alternative conversion method (unreleased 0.2.0)

Omit `method` for the unchanged NCAA default, or pass
`method: "colorado-teamunify-2026"` to `engine.convert` / `convertSwim`.
`conversionMethods` from `@turnmark/sdk/conversion` supplies labels, identifiers
and source metadata. Results carry the selected provenance and optional
`offsetSeconds` (absent when zero): the untruncated calculation is
`inputSeconds × factor + offsetSeconds`. Colorado results are estimates and
unsupported formulas remain unavailable. Swift/Kotlin use
`convertSwimWithMethod(request, method)`; the existing `convertSwim` stays NCAA.
See the methodology for the exact source scope and distance-event exceptions.

### Optional altitude context

`convertSwim` accepts `elevation: {value, unit: "feet" | "meters"}` and an
independent `altitudePolicy`: `usa-swimming-altitude-2026` (default) or
`ncaa-altitude-2026-27-d1`. Rust deducts altitude from the original event before
course conversion and returns its own provenance under `value.altitude`.
`adjustAltitude` accepts the same choice as `policy`. Existing omitted-altitude
results are unchanged. See [the altitude contract](../../docs/ALTITUDE.md).

Available Colorado SCM↔SCY distance-freestyle results carry
`caveat: "colorado-short-course-distance"`. The pinned rule uses a general
multiplier for unequal-distance events; display that limitation with the result.
See [the method comparison contract](../../docs/METHOD_COMPARISON.md).

National benchmark programs (`futures`, `juniors`, `nisca`) share the original-swim
`assessSwimBenchmark` API. Initialize the SDK, then call
`getNationalStandardPrograms()` for labels, age choices and coverage notes.
Futures uses `18 & under` / `19 & over`; Juniors and NISCA use `age: ""`.
See [coverage and source editions](../../docs/NATIONAL_BENCHMARKS.md).
