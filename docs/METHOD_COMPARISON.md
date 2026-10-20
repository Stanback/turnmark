# Comparing published conversion methods

NCAA remains the default. **Calculation options** contains separate **Course
conversion** and optional altitude controls across all converter interfaces.
The course selection does not silently change altitude policy.

A selected alternative drives the main result; the
comparison in calculation details evaluates NCAA and documented Colorado Timing
for the same entered event, category and destination. Native layouts adapt to
SwiftUI/Compose, web and widget share a small presentation component, and MCP
returns the comparison in both structured and text responses.

A **method difference** is the absolute gap between the two displayed clocks.
It is not a prediction interval, confidence score, accuracy ranking or evidence
that the swimmer will achieve either time. Both values come from the shared Rust
engine. Unsupported results retain their state; missing comparisons do not
become zero-second gaps. Same-course results remain original unless an explicit altitude deduction creates a labeled sea-level estimate.

If altitude is enabled, both course methods receive the same sea-level
estimate after the selected altitude policy’s deduction. The original time and
deduction remain visible. The [altitude follow-up](ALTITUDE.md) adds an independent policy selector and
shared adjustment order to every converter. No predictive model is implied.

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

## Distance-event limitation of the documented Colorado rule

For SCM↔SCY distance freestyle the pinned TeamUnify USA-team formula uses the
general ×1.11 / ÷1.11 rule, despite mapping unequal-distance events. Turnmark
preserves that rule but marks the result with the engine-owned
`colorado-short-course-distance` caveat. Every converter shows the caveat;
NCAA remains the default. Do not silently replace the documented result with a
new formula under the same method ID.

A regression example: **4:11.36 for 400 m SCM → 500 yd SCY** returns **4:47.30**
with NCAA (×1.143, truncated), versus the legacy Colorado **3:46.45**
(÷1.11, truncated). The latter is a documented-rule limitation, not a useful
comparison of matched event distances. Model evaluation must report this cohort
separately; a large gap here is not a calibrated prediction interval.
