# Converter layout exploration

The first web layout pass is implemented in draft PR26, separate from
conversion-model research. It is ready for visual review; it has not been
merged or adopted by the native apps.

## Direction

Bring the editable swim and its three course equivalents into one visual group.
Make the original time, destination event/course and derived estimate easy to
scan. Explore a compact next-target summary using the existing published
standards, with the full standards/points view still reachable. Keep the navy,
cyan and lime identity and generated semantic tokens.

Keep water artwork behind the content, restrained border highlights and subtle
button hover feedback. Preserve readable surfaces, focus visibility, reduced
motion and light/dark appearances. Decorative branching light trails, miniature
swimmers and invented probability/confidence graphics are outside this study.

NCAA stays the default. The alternative conversion method stays a quiet setting;
its selected source and original-swim benchmark distinction remain accessible.
Native controls remain platform-owned; this web study does not imply a shared
web/native layout or a native redesign.

## Implemented web flow

The next exploration should make the starting point clearer: **enter a swim →
compare course equivalents → explore targets or methods**. On a narrow screen,
editable inputs come before the result. Preserve the desktop side-by-side
comparison; do not shrink that entire composition into a phone.

Arrival and Reset now use a blank time and a recognizable placeholder. “Try an
example” explicitly loads the default 58.32 SCY swim and settings without adding
a history entry. Remembered swimmer preferences retain their existing contract;
race time starts fresh. Shared URLs and restored saved/recent comparisons still
open their explicit swim. Empty input is a neutral state; malformed nonempty
input shows validation, with no stale result or enabled save/share action.

Keep result updates stable while typing: no automatic scrolling, disappearing
keyboard, reordered controls or layout jump to a result. Below the inputs, show
all three course equivalents clearly, with the original identified. Follow with
one relevant next target and a route into full standards/points. Methods,
altitude and other optional details remain quiet. Do not add an experimental
probability display until the separate research work earns one.

The native reference currently puts a prominent result first. This new
input-first direction should be evaluated for native apps in a paired follow-up
as well; it is not implemented by this web study. Preserve native navigation,
keyboard/focus behavior, Dynamic Type and platform controls in that work.

Polish supports this hierarchy: readable labels, consistent tokens, restrained
border illumination, generous touch targets and quieter secondary actions.
Keep water decorative. Save comparison and Log swim have different meanings:
logging an actual race must remain an explicit action, never an automatic side
effect of exploring estimates.

Potential additional benchmarks are reviewed in
[the maintenance shortlist](BENCHMARK_EXPANSION.md); adding their data or a new
scoring system is not part of this layout PR.

## README screenshots are part of this PR

Before this draft is ready, update the root README's images from the actual
running builds after the explored layout settles. Do not use the supplied
concept art as a screenshot of implemented behavior.

- Lead with the main converter: a readable original swim, editable time/event
  and SCY/SCM/LCM results. Avoid a hero-heavy crop that cuts off the converter.
- Keep the paired iOS and Android previews on their normal Convert/home view,
  using the same sample swim. Show enough input and converted result context;
  standards and points sheets belong in the detailed review.
- Make the NCAA/Colorado capability discoverable where shown, with a compact
  supplementary actual-build capture if opening settings would obscure the
  main comparison. Keep the lead screenshot representative of the NCAA default.
- Review existing widget/MCP images where this PR touches their presentation.
  Distinguish published npm behavior from newer source-only UI.
- Use sample data only. Check both appearances and narrow/large-text layouts in
  the detailed review; keep the README's gallery small, legible and current.
- Update image paths, alt text and captions together. Record source revision,
  method, sample event/time, viewport/device and capture procedure in the review.

The README now leads with an actual converter-region capture containing all
inputs, three equivalents and the next standard. The same sample's Colorado
capture is linked separately. Native home images remain the preceding actual
build captures: both use 58.32 SCY and the 1:06.72 NCAA LCM comparison, and native
source/presentation is unchanged in this web PR. They are development previews,
not evidence that native apps have adopted blank or input-first arrival.

## Actual-build review — October 19, 2026

| Desktop, NCAA default                                                                        | Same input, light appearance                                                |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| ![Editable swim and three course equivalents](screenshots/web-converter-comparison-dark.png) | ![Matching light converter](screenshots/web-converter-comparison-light.png) |

| Phone arrival                                                                                                                | Explicit example inputs                                                                                              | Comparison below the inputs                                                                                                              |
| ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| <img src="screenshots/web-converter-empty-mobile.png" width="250" alt="Blank time with Try an example and neutral controls"> | <img src="screenshots/web-converter-comparison-mobile.png" width="250" alt="Example swim inputs before the results"> | <img src="screenshots/web-converter-results-mobile.png" width="250" alt="Course equivalents reached by scrolling below the input panel"> |

[Colorado method and unchanged original-course next standard](screenshots/web-converter-method-dark.png) ·
[320px long-time and enlarged-root-text content review](screenshots/web-converter-large-text.png)

The desktop capture uses Chromium at 1120×1450, device scale 1, reduced motion,
and a crop of `#converter`. It excludes the hero deliberately so controls and
results remain legible in the README. Light/dark use the same 100 freestyle,
women/girls, age 15–16, SCY, 58.32 sample and NCAA default. The method supplement
opens Conversion method and selects documented Colorado Timing, yielding
1:06.33 LCM; the AA gap remains 1.83s because it uses the original SCY swim.

Mobile captures use 390×844 and ordinary viewport screenshots, with the input or
results panel scrolled to the top. They retain the actual fixed navigation bar.
The 320×900 content check uses 60:00.00 and a 200% root-font preference; this is
a narrow reflow check, not proof of complete browser zoom or screen-reader
coverage. Its long content crop omits fixed navigation to avoid an artificial
navigation overlay midway through the exported image. Category controls stack at the smallest width, and age controls can
shrink to their container instead of overflowing. Capture source hashes are in
the [local review manifest](screenshots/converter-review.json).

The shared semantic tokens, static water artwork, original/derived labels,
quiet method/altitude settings and explicit result navigation remain intact.
The new next-standard shortcut uses the existing youth table and unadjusted
entered swim. Other systems or altitude-adjusted input show a general route to
the full standards view rather than inventing a compact target.

## Completion checks

This first pass passes Svelte/TypeScript checks, 138 unit tests, 41 browser cases
(one desktop-inapplicable case skipped), and 20 production/offline cases.
Light/dark screenshots, 320px controls, enlarged root text, invalid/unavailable
results, method sharing/persistence and keyboard focus were reviewed. CI and
owner review remain pending. No native layout or widget/MCP presentation changed.

- Confirm which layout to keep through actual desktop/mobile browser previews.
- Keep calculations, unsupported/invalid states, offline behavior, shared links,
  keyboard access and original-swim standards/points semantics intact.
- Run web type/unit/browser/production checks for implemented layout changes.
  Exercise widget/MCP or native consumers only if this study changes them.
- Inspect the replacement README images at their rendered GitHub size and verify
  their relative links. Do not mark this draft ready with stale screenshots.
