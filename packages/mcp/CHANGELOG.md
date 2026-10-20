# Changelog

## Unreleased

- Add original-swim national benchmark comparisons through `assess_swim_benchmark`;
  keep conversion estimate guidance beside the result.

- Add optional, explicit altitude context to conversion tools/card and an independent USA Swimming / NCAA altitude policy. Both policies are compared without confidence claims; original inputs and altitude provenance remain separate. UI resource revision is `0.3.0-r5.html`.

- `convert_swim` adds `methodComparison` (NCAA/Colorado outcomes with their own
  provenance) and `methodDifferenceSeconds` when both results exist. The chosen
  method still drives the original top-level result. Invalid inputs retain their
  existing shape. Text-only clients receive the same comparison as Apps clients.
- The revised `0.3.0-r2.html` view uses a shared navy result surface, white clock
  and lime hundredths, with host-themed editing controls and less repeated copy.
- The card keeps the comparison and deeper explanation inside How this is
  calculated. Method differences are not prediction or confidence intervals.

## 0.3.0 — unreleased

- Uses SDK 0.2.0, preserving the NCAA default and adding documented Colorado
  Timing formulas through the optional method input and a collapsed card setting.
- Source discovery lists both conversion methods; the card shows additive
  offsets when applicable. Current immutable resource URI ends in `0.3.0-r5.html`.
- Includes the source-only 0.2.1 glyph/wordmark work below. Publish SDK 0.2.0
  before MCP 0.3.0; release checks require that exact registry dependency.

## 0.2.1 — source-only, folded into 0.3.0

- Shared vector stroke glyphs and an accent-colored wordmark period in the interactive comparison card.
- New versioned UI resource; tool schemas, calculations and SDK dependency are unchanged.

## 0.2.0

- Official MCP Apps conversion card for compatible hosts, with editable time
  and target course, source context and host light/dark appearance.
- Versioned, self-contained HTML resource with no runtime network or storage.
- Existing six read-only tools, output schemas, text fallback and Streamable
  HTTP/stdio transports remain compatible with SDK 0.1.0.
- Packed offline, workerd protocol, official bridge/browser, accessibility and
  cancellation/error-boundary checks. Real-host rendering remains unverified.

## 0.1.0 — 2026-10-18

- Initial published stdio adapter and six SDK-backed swimming tools.
