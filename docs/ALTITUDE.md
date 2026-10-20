# Altitude adjustments across Turnmark

Optional altitude adjustment is separate from course conversion. It is off on
fresh arrival; web's existing remembered elevation preference still restores.
**Calculation options** groups **Course conversion** (NCAA / Colorado)
and optional **Altitude adjustment** settings. Enable **Adjust for altitude**
to reveal elevation in feet/meters and an **Altitude policy** choice, with a compact selected-policy preview. The full two-policy comparison
is shown once in calculation details. USA Swimming remains the default; the NCAA alternative is explicitly
pinned to the **2026–27 Division I** altitude table. Choosing NCAA or Colorado
course formulas never changes altitude policy automatically.

## Calculation order and UI contract

1. Keep the entered time and actual event/course untouched.
2. Deduct the selected policy's allowance for that original event and elevation.
3. Convert the sea-level estimate with the selected NCAA or Colorado method.
4. Compare both course methods using the same adjusted input. Label their gap
   **Method difference**, never a confidence interval or prediction range.

Altitude details show both policies' deductions and sea-level estimates, plus
source links. These are rule comparisons, not measurements of personal altitude
response. Below 3,000 ft and for events without a published allowance, the
allowance is zero. An adjusted same-course result is a **Sea-level estimate**,
not the original performance. Invalid elevation never produces a valid estimate.

Standards and points assess the original swim. Native **Log swim** records that
original performance; it never substitutes an altitude/course estimate. Web and
widget calculations, shared links, saved comparisons and MCP tool inputs retain
the explicit altitude context. Widget/MCP do not gain access to personal history.

The web and widget use semantic-token HTML disclosures; iOS uses a native
DisclosureGroup, pickers and grouped detail rows; Android uses Material controls
and its native detail sheet. The MCP card uses host-approved tool calls and
source-link actions, without adding network access to its sandbox.

## Sources and numerical scope

| Original individual event | USA Swimming: 3,000–4,250 / 4,251–6,500 / >6,500 ft | NCAA 2026–27 D1: same bands |
| ------------------------- | --------------------------------------------------- | --------------------------- |
| 100 yd/m                  | 0 / 0 / 0                                           | 0 / 0.10 / 0.15             |
| 200 yd/m                  | 0.50 / 1.20 / 1.60                                  | 0.50 / 1.20 / 1.60          |
| 400 m / 500 yd            | 2.50 / 5.00 / 7.00                                  | 2.50 / 5.00 / 7.00          |
| 800 m / 1000 yd           | 5.00 / 10.00 / 15.00                                | 6.30 / 11.40 / 18.50        |
| 1500 m / 1650 yd          | 11.00 / 23.00 / 32.50                               | 11.00 / 20.00 / 32.50       |

All allowances are seconds. Individual-event APIs do not implement relay rules.
Feet must be whole numbers from 0 to 20,000; meters range from 0 to 6,096 and
round to the nearest foot for band selection, preserving the existing contract.
The resulting time must remain positive. Unit switches preserve the elevation
with the displayed meter precision; they do not select a different policy.

- [USA Swimming Times & Recognition Policy Manual, §4.7](https://www.usaswimming.org/docs/default-source/timesdocuments/general-docs/times-and-recognition-policy-manual.pdf#page=7): posted edition April 14, 2022. The existing `usa-swimming-altitude-2026` ID denotes Turnmark's checked snapshot, not a claimed 2026 manual edition.
- [NCAA 2026–27 Division I qualifying standards, page 3](https://ncaaorg.s3.amazonaws.com/championships/sports/swimdive/d1/2026-27D1XSW_QUALSTANDARDS.pdf#page=3): updated June 15, 2026, checked October 19. SHA-256 `259c76ba10df6f72314a677df6aea1becc6d7d9b4400b5f0f95d4d33e88bf7ab`.

The NCAA qualifying document also has championship-specific SCM course factors.
This altitude feature does **not** replace the existing generic NCAA course
conversion edition with those selection/seeding overrides. Meet rules remain
controlling; a calculated estimate is not entry eligibility.

## Shared API

`adjustAltitude({ swim, elevation, policy? })` defaults to USA Swimming.
`convertSwim({ swim, to, table, method?, elevation?, altitudePolicy? })` applies the
same engine operation before converting. Without elevation the existing result
shape is unchanged. With elevation an available result includes `value.altitude`
containing the original/adjusted clocks, deduction, rounded feet and its own
provenance. Course provenance remains separate.

Swift/Kotlin retain the original typed entry points and gain
`adjustAltitudeWithPolicy` and `convertSwimAtAltitude`. No formula is implemented
in a UI. Source snapshots and independent fixtures live in `data/conversions.json`
and `fixtures/sdk-conformance.json`; bindings are regenerated by packaging scripts.
