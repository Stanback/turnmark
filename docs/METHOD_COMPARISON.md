# Comparing published conversion methods

NCAA remains the default. A selected alternative drives the main result; the
comparison in calculation details evaluates NCAA and documented Colorado Timing
for the same entered event, category and destination. Native layouts adapt to
SwiftUI/Compose, web and widget share a small presentation component, and MCP
returns the comparison in both structured and text responses.

A **method difference** is the absolute gap between the two displayed clocks.
It is not a prediction interval, confidence score, accuracy ranking or evidence
that the swimmer will achieve either time. Both values come from the shared Rust
engine. Unsupported results retain their state; missing comparisons do not
become zero-second gaps. Same-course results remain the original swim.

On web, if altitude is enabled, both course methods receive the same sea-level
estimate after the current USA Swimming deduction. The original time and
deduction remain visible. This change does not introduce a second altitude
policy, native/widget altitude input, or a predictive model.

The optional UI explains category/event NCAA factors, Colorado multipliers and
fixed offsets, yard/metric distance mapping and the physical relevance of turns
without claiming individual turn technique, endurance or age are measured inputs.
Standards and points continue to assess the original swim separately.

For MCP, `convert_swim` preserves its primary `status`, `value`/`reason` and
`provenance`. Non-invalid responses add `methodComparison`, an array of
`{ method, label, result }`, with each result preserving available/unavailable/
invalid and its source. `methodDifferenceSeconds` appears only when both are
available. The server computes both through its existing immutable SDK engine;
the network-free card renders the supplied results without extra tool calls or
another numerical implementation. This is source work pending release; it does
not publish a new npm package by itself.

Verification covers method switching/persistence, destination changes,
unsupported/invalid states, unchanged entered swims, iframe offline behavior,
MCP stdio/HTTP parity and its sandbox, cancellation and accessibility boundaries.
See [methodology](METHODOLOGY.md) for source editions and calculation rules.
