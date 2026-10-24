# Changelog

## 0.2.0 — unreleased

- Optional `colorado-teamunify-2026` conversion method, pinned source metadata
  and direction-specific formulas. Omitted methods retain NCAA results.
- Conversion results expose optional `offsetSeconds`; native bindings expose
  `convertSwimWithMethod` and a typed method enum.
- Conversion results report `formula` (`none`, `multiplier`, `multiplier-offset`
  or `equivalent`), so clients describe the arithmetic from the engine instead of
  inferring it from the method.

- `assessSwimBenchmark` / `engine.benchmark` compare an original swim against
  youth or USMS targets, returning met states, the achieved level, next target
  and gaps from the authoritative Rust engine.

## 0.1.0 — 2026-10-18

- Rust-backed course conversion, altitude adjustment, youth standards, Masters
  targets, World Aquatics points and time helpers, with typed ESM exports.
- Explicit available, unavailable and invalid results, published/derived kinds,
  source editions and provenance. No fallback values for missing data.
- Browser Wasm asset and Node entry with bundled, offline filesystem loading.
- Installable tarball with declarations, TypeScript sources and GPL license;
  isolated Node/browser conformance checks require no consumer install scripts.
