# Adaptive native layouts and iPhone Duo

Design research checked October 18, 2026. This is an implementation brief for the
paired native design adoption, not a shipped Duo layout or simulator sign-off.

## What is confirmed

Apple lists a 7.6-inch inner display and 5.4-inch outer display. Panel pixels are
hardware specifications, not layout breakpoints or a reliable way to infer
usable app dimensions. [Apple specifications](https://www.apple.com/iphone-duo/specs/).

The useful constraints are resizability, safe areas, compact/regular environments
and reserved fold/camera regions. System bars can move to a vertical edge; the
inner portrait arrangement has horizontal bars. Use standard navigation and
sheets instead of drawing a fixed bottom bar. Folding should preserve hierarchy
and functionality. [Duo design guidance](https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo)
and [Apple design walkthrough](https://developer.apple.com/videos/play/tech-talks/111466/).

Apple's iOS 27.1 `ArrangementView` can arrange primary and supporting content
around available regions. Navigation wraps that layout; scroll views belong in
its panes, not around the arrangement. A split arrangement can collapse a view
when it cannot split, so our compact fallback must explicitly keep inputs and
results accessible. Use layout/region APIs for geometry; continuous hinge angles
are intended for interactions rather than rebuilding layout rules.
[Adaptive layouts walkthrough](https://developer.apple.com/videos/play/tech-talks/111463/),
[hinge and scene guidance](https://developer.apple.com/videos/play/tech-talks/111464/).

## Turnmark proposal

Extra room should expose the existing comparison workflow and event context.
It is not a reason to add a coach dashboard, graphs without a clear question,
or extra promotional content.

| Available environment                       | Converter                                                                                      | History                                                                  |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Compact / outer display                     | Direct time entry and inputs, with a compact result nearby; controls stay scrollable           | List followed by native detail navigation                                |
| Regular / open inner display                | Input pane beside the selected result and three course equivalents                             | Swim/meet list beside the selected recorded swim and optional comparison |
| Book fold                                   | Keep each content pane within a usable region; the complete time and its context stay together | List and detail follow the system's pane/fold adaptation                 |
| Tabletop                                    | Explore result above, entry controls below; preserve the same features and meaning             | Preserve selected swim and reachable edit/navigation actions             |
| Half-window multitasking / short PiP window | Re-evaluate the actual available space; return to the compact workflow when needed             | Collapse list/detail through native navigation                           |
| Accessibility text / keyboard               | Stack or scroll before clipping; avoid a pinned result that consumes the working area          | Preserve reading order and visible edit/share controls                   |

The tabletop treatment is a proposed refinement, not a new function available
only in that posture. Reachable inputs and a visible answer matter more than an
animation between layouts. Keep controls stable while someone types or folds.

For the expanded converter, favor a readable input pane and a slightly more
prominent result pane rather than stretching every field across the display.
Use the [shared palette and hierarchy](DESIGN_CONTRACT.md), native typography and
system controls. Keep the result opaque. The time must never straddle the crease;
move the whole result/context block into a usable region.

History offers the strongest second benefit: select a meet swim without losing
the surrounding list. A recorded 1:00.00 LCM stays the recorded performance;
52.44 SCY remains a separate published-factor estimate. Those sample values were
checked through the actual SDK with women's 100 freestyle; the SCM derived
estimate is 58.52. Do not turn saved comparisons into race records or personal
bests when changing the layout.

## Implementation boundaries

- Keep `TabView` / navigation outside the adaptive content arrangement. Let iOS
  place native bars, menus and sheets; do not simulate Duo's side controls.
- Preserve the draft, selected course/swim, editing focus and navigation when
  layouts change. Pane views do not own independent copies of the same swim.
- Use a regular-width list/detail container for History. On older supported
  systems, use existing adaptive SwiftUI containers and an explicit compact
  fallback. Availability checks do not make new APIs compile with an older SDK.
- Replace the narrow-phone pinned-result strategy with an inline expanded result
  when the input/result panes are visible together; never render duplicate clocks.
- Check fit and accessibility along with size class. Do not branch on a device
  model name, hard-code panel resolutions or derive placement from raw hinge angles.
- Keep Android at equal scope: the same compact/expanded workflows and preserved
  state, implemented with its native adaptive navigation and folding-region tools.
  The shared contract describes the visual/semantic roles, not Apple's APIs.
- If multiple app windows are enabled, keep drafts/selections scene-scoped and
  verify persistence behavior. Multiple scenes and simultaneous use of both
  displays are separate capabilities, not prerequisites for a good expanded UI.

## Acceptance evidence still required

The local inventory on October 18 contains Xcode 27.0 and iOS 27.0 simulators,
including iPhone 18 Pro and iPad; it contains no Duo device type/runtime. Current
CI phone tests do not prove Duo behavior. Add a compatible SDK/runtime before
using the 27.1 arrangement APIs and claiming a Duo review. iPad/resizable previews
can exercise wide layouts earlier but are not substitutes for fold regions.

Capture and inspect native screens in both appearances, with these checks:

- Outer/compact, fully open, rotated, book fold and tabletop.
- Both sides of a half-window split, reduced height and keyboard visible.
- Standard and accessibility text; long times; original, invalid and unavailable states.
- 500-yard / 400-meter context, source details and unchanged original performance.
- Folding/resizing during entry, selected History detail, save and native sharing.
- Safe areas and active reserved regions: no clock, action or sheet obscured by
  the fold, camera, side navigation, keyboard or system overlays.

Store screenshots follow the native implementation and this review. Physical
Duo testing, VoiceOver and device ergonomics remain release checks; a concept
preview or successful ordinary-phone CI run does not establish them.
