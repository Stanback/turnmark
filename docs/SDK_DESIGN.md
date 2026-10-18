# SDK contract

Status: Rust-backed implementation, published October 18, 2026 as
`@turnmark/sdk@0.1.0`. The SDK implements conversion, altitude, and separate
benchmark/points APIs with runtime validation and portable conformance cases. See the [SDK guide](../packages/sdk/README.md)
for the implemented interface and the [platform plan](PLATFORM_PLAN.md) for
native architecture, distribution, licensing, and rollout decisions.

## Public boundaries

Keep the engine independent of Svelte, SwiftUI, Compose, storage, network access,
clipboard, URL mutation, and analytics. Calls operate on values and return values.
The same public semantics should be available through TypeScript, Swift, and
Kotlin wrappers, using idiomatic types in each language.

Expose these capabilities separately:

| Capability              | Contract                                                                         |
| ----------------------- | -------------------------------------------------------------------------------- |
| Time parsing/formatting | Strict clock input, explicit precision/range, consistent hundredths.             |
| Event normalization     | Course plus actual distance plus stroke; validate before mapping.                |
| Conversion              | Entered swim, target course, explicit factor table/method edition.               |
| Altitude                | Explicit elevation unit and adjustment request; preserve raw and adjusted times. |
| Youth standards         | Dataset edition, age group, published category, original-course event/time.      |
| Masters targets         | Dataset edition, age group, category, original-course event/time.                |
| World Aquatics points   | Base-time edition/validity, raw metric swim; no implicit converted score.        |
| Provenance/coverage     | Sources, dates, edition, supported events, and machine-readable missing reasons. |

Do not include UI marker coordinates, history, CSV files, or share-link encoding
in the numerical engine. A separate adapter can encode a versioned share format
and read existing Turnmark fragments without changing old links.

## Example ergonomics

Implemented TypeScript conversion API:

```ts
import { createEngine } from "@turnmark/sdk";

// Initialize the packaged Rust/WebAssembly engine once.
// Supply local assets in offline or self-hosted deployments.
const engine = await createEngine();

const result = engine.convert({
  swim: {
    time: "2:16.71",
    event: { distance: 200, stroke: "breaststroke", course: "LCM" },
  },
  to: "SCY",
  table: "men",
  method: "ncaa-2025-27",
});

if (result.status === "available") {
  console.log(result.value.time); // "1:57.29"
  console.log(result.value.hundredths); // 11729
  console.log(result.value.kind); // "published"
  console.log(result.value.factor); // 0.858
  console.log(result.provenance); // edition and source reference
}
```

The workspace package name is provisional; registry ownership has not been
established. The Rust-backed JavaScript SDK initializes asynchronously from a
packaged Wasm URL or caller-provided bytes; Node consumers pass bytes. Startup
errors can be retried and are surfaced by the web app. Do not perform network
requests during calculation calls or silently fall back to a different formula.

MCP and WebMCP will expose these same operations through thin protocol adapters,
with shared tool contracts and unchanged domain results. See the
[agent interface plan](AGENT_INTERFACES.md).

Native Swift/Kotlin consumers call their generated or platform wrappers directly;
they do not load this JavaScript facade or initialize WebAssembly.

Separate entry points should permit conversion-only use without loading youth,
Masters, or points snapshots. Measure whether a proposed Rust/Wasm artifact
actually preserves that property; a JavaScript exports map alone cannot remove
data compiled into a monolithic Wasm binary. Choose split artifacts or explicitly
loaded immutable data packs if the size measurements justify it.

## Units and validity

- Public event distances are actual distances: `500` with `SCY`, `400` with
  `SCM`/`LCM`. Use named event identifiers or a normalization function internally
  to map corresponding freestyle events. Reject `400 SCY freestyle` when it is
  intended as an unsupported event rather than guessing the user's intention.
- Require a published category/table explicitly for operations that need it.
  The table describes a calculation source and does not establish eligibility
  or infer a person's identity.
- Specify accepted time syntax and limits. Preserve the current strict parser
  behavior during extraction: positive input, at most hundredths, seconds below
  60 in a clock field, and no more than 3,600 seconds. Changing that domain is
  a separate versioned decision.
- Represent entered and displayed whole hundredths as bounded integers at the
  language boundary. Retain the precision needed for intermediate calculations.
  Existing conversion truncation and points rules remain authoritative until a
  separately reviewed numerical change.
- Model elevation as a value plus `feet`/`meters`. Reproduce current unit
  conversion and band boundaries; never repeatedly round during unit toggles.
- Distinguish an unchanged entered swim, an altitude-adjusted swim, a published
  metric-to-yards conversion, and a derived estimate. An entered swim is not
  certified as an official performance by the SDK.
- Query standards against the relevant original-course swim. Keep the current
  youth altitude behavior explicit, and Masters and points raw-input behavior
  intact. An estimate must never become an eligibility claim by default.

## Results and errors

Use a discriminated result with stable reason codes. Expected missing coverage
is different from invalid input or an engine initialization failure:

```ts
type Result<T> =
  | { status: "available"; value: T; provenance: Provenance }
  | { status: "unavailable"; reason: CoverageReason; provenance: Provenance }
  | { status: "invalid"; field: string; reason: ValidationReason };
```

Examples of coverage reasons are `event-not-published`, `course-not-supported`,
`age-group-not-published`, `factor-not-published`, and `no-time-published`. Display text belongs in
the consuming UI, where it can be localized.

Every language boundary must validate enum values, supported distances, numeric
ranges, safe output sizes, and dataset identifiers. Test nonfinite JavaScript
numbers, malformed strings, zero/negative times, missing fields, and mismatched
course/distance pairs. Swift/Kotlin compile-time types are helpful but do not
replace checks when accepting imported or shared data.

For a Rust implementation, avoid panics and unchecked arithmetic in reachable
operations. Investigate integer/rational arithmetic for decimal factors and
cubic point truncation, but prove compatibility before changing the numerical
model. A rewrite that changes an answer by one hundredth is a behavior change,
not automatically a precision improvement.

## Data and versioning

Use distinct identifiers for SDK version, calculation method, dataset edition,
and serialized share/export schema. Include revision and validity dates in
provenance; old pinned datasets should remain reproducible. A correction to
values can change output without changing a function signature and must be
called out in release notes.

Store data once in a documented schema and generate language-specific resources
from it. Validate duplicates, counts, table order, missing values, and source
metadata before packaging. Keep original document redistribution and numerical
snapshot attribution decisions separate from code licensing.

## Conformance and release checks

Use portable fixtures with an identifier, input, expected structured output,
source reference, and independently verified rationale. Expected values should
not merely be generated by the implementation being tested.

Include the NCAA example above; same-course behavior; 400/500, 800/1000, and
1500/1650 mappings; unsupported LCM sprint strokes and 100 IM; parser rejection
cases; hundredth truncation boundaries; all altitude bands and meter conversions;
exact/next youth thresholds; missing Masters events, ages, and NO TIME cells;
all base times at 1,000 points; points integer boundaries; and next-milestone
targets with the following hundredth failing the target.

Run the same cases through the existing TypeScript oracle, candidate Rust core,
generated Swift/Kotlin bindings, and browser/Node wrappers. Review intentional
differences against source evidence instead of copying legacy errors. Confirm
installed artifacts work outside the monorepo and without network access.

Release examples should include plain JavaScript, TypeScript, a native Swift
consumer, a native Kotlin consumer, and a static HTML embed. Publish API docs,
coverage/methodology, license/notices, a changelog, and a clear support policy.
