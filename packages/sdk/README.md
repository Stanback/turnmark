# Turnmark SDK

Offline JavaScript/TypeScript calculations for course conversion, altitude,
USA Swimming youth standards, USMS targets, and World Aquatics points.
This is an **unpublished private workspace** at version `0.1.0`. The proposed
`@turnmark/sdk` name has not been reserved on npm. It runs compiled JavaScript
with no runtime dependencies; no Rust/Wasm implementation is included yet.

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

`convertSwim` and `adjustAltitude` are also direct named exports.
`createEngine()` initializes without I/O; calculation calls never fetch data.

## Entry points

| Import                     | Operations                                                              |
| -------------------------- | ----------------------------------------------------------------------- |
| `@turnmark/sdk`            | Engine, conversion, altitude, time helpers, contract types.             |
| `@turnmark/sdk/conversion` | Conversion/altitude operations, source metadata and method identifiers. |
| `@turnmark/sdk/time`       | `parseTime`, `formatTime`, `truncateTime`.                              |
| `@turnmark/sdk/youth`      | `getYouthStandards`, ages, source and edition.                          |
| `@turnmark/sdk/masters`    | `getMastersTarget`, ages, source and edition.                           |
| `@turnmark/sdk/points`     | `getWorldPoints`, next points milestone, source and validity.           |

Root and conversion imports do not load benchmark or points tables. Import only
the optional modules you need. `compat` entry points temporarily support the
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
npm ci
npm run build:sdk
npm test
npx playwright install chromium
npm run test:sdk:package
```

`npm run dev --workspace @turnmark/sdk` watches sources. Root dev/build/check/test
commands build the SDK first. Data import scripts update the canonical snapshots
in this package's `src/data/`. Source-backed portable cases live in the repo's
`fixtures/`. The package check installs a tarball into a temporary project and
validates Node, browser, declaration resolution, and conversion-only bundling.

GPL-3.0-or-later remains in effect. Publication and broader SDK licensing are
separate decisions. Preserve source attribution, metadata, and third-party
notices. The repository's `docs/METHODOLOGY.md` and `docs/DATA.md` document sources
and calculation limitations.
