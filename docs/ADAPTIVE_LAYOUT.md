# Adaptive native layouts and iPhone Duo

Design research checked October 18, 2026. This records the paired native implementation and its validation limits.
Simulator evidence is distinct from physical-device release sign-off.

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

## Implemented workspace

Extra room should expose the existing comparison workflow and event context.
It is not a reason to add a coach dashboard, graphs without a clear question,
or extra promotional content.

| Available environment                       | Converter                                                                                      | My times                                                                 |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Compact / outer display                     | Direct time entry and inputs, with a compact result nearby; controls stay scrollable           | List followed by native detail navigation                                |
| Regular / open inner display                | Input pane beside the selected result and three course equivalents                             | Swim/meet list beside the selected recorded swim and optional comparison |
| Book fold                                   | Keep each content pane within a usable region; the complete time and its context stay together | List and detail follow the system's pane/fold adaptation                 |
| Tabletop                                    | Compact result above, entry controls below; preserve the same features and meaning             | Preserve selected swim and reachable edit/navigation actions             |
| Half-window multitasking / short PiP window | Re-evaluate the actual available space; return to the compact workflow when needed             | Collapse list/detail through native navigation                           |
| Accessibility text / keyboard               | Stack or scroll before clipping; avoid a pinned result that consumes the working area          | Preserve reading order and visible edit/share controls                   |

The tabletop treatment keeps the complete clock and source context prominent,
with course equivalents behind a disclosure to reduce vertical pressure. The
input and result panes scroll independently; the same features remain available. Reachable inputs and a visible answer matter more than an
animation between layouts. Keep controls stable while someone types or folds.

For the expanded converter, favor a readable input pane and a slightly more
prominent result pane rather than stretching every field across the display.
Use the [shared palette and hierarchy](DESIGN_CONTRACT.md), native typography and
system controls. Keep the result opaque. The time must never straddle the crease;
move the whole result/context block into a usable region.

The converter's supporting pane belongs to the current conversion. History and
personal bests should not replace that immediate feedback. History owns a
separate list/detail workspace; a matching recorded personal best could later
appear as secondary context alongside an estimate, explicitly labeled as an
actual performance. Do not add that comparison until its purpose and matching
rules are clear.

History offers the strongest second benefit: select a meet swim without losing
the surrounding list. A recorded 1:00.00 LCM stays the recorded performance;
52.44 SCY remains a separate published-factor estimate. Those sample values were
checked through the actual SDK with women's 100 freestyle; the SCM derived
estimate is 58.52. Do not turn saved comparisons into race records or personal
bests when changing the layout.

## Implementation boundaries

- Use Convert and My times as the two native destinations, with contextual
  methodology. Record time confirms an actual entered swim; comparisons and
  sharing remain available without a separate comparison-save action. Follow the
  [agreed persistence contract](DESIGN_CONTRACT.md#result-and-terminology-contract)
  when transitioning existing saved comparisons.
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

## Baseline review after the Xcode upgrade

On October 18, Xcode was updated to 27.1 (27A9275), and the iOS 27.1 simulator
runtime (24A94232) was installed. The SDK contains `ArrangementView` and reserved
region APIs. The existing app builds successfully with this SDK; no numerical
engine changes were needed.

Device Hub review covered the closed outer display, fully open inner display,
partially open book fold and rotated tabletop configuration. Light appearance
was inspected throughout, with an additional dark tabletop review. Baseline
captures show the [open light layout](screenshots/ios-duo-baseline-open-light.png)
and [tabletop dark layout](screenshots/ios-duo-baseline-tabletop-dark.png).
These are existing native screens, not the redesigned concepts or store assets.

The current converter stretches a single input card and a bottom result across
the expanded display. Both cards span the fold instead of forming useful panes.
System navigation already changes between side and bottom placements; preserve
that behavior. The current default blue controls and lime Details link also need
the planned semantic color adoption. This baseline review supports the proposed
adaptive layout; it does not establish that the new layout is implemented.

The baseline `TURNMARK_IOS_RUNTIME=27.1 node scripts/test-ios.mjs app` run on the
closed, rotated Duo reported 9 passing and 4 failing tests out of 13, with no
skips. All six History model tests passed. UI failures include a missing Done
button, queries scoped to a bottom `tabBars` container, and a log-sheet field
expectation; runtime warnings also reported invalid frame dimensions. Investigate
both actual presentation behavior and phone-specific test assumptions during
native adoption. Do not call this a passing Duo suite or suppress these failures
to claim support. Fold transitions and other poses still need dedicated tests.

## Current validation and remaining release checks

The native branch generates Swift and Kotlin palettes from the canonical token
source. The converter uses compact inline content or independent expanded panes;
iOS 27.1 uses active division regions and ArrangementView, while Android uses
WindowManager folding features relative to the actual content origin. My times
uses native list/detail navigation on iOS and an adaptive list/detail workspace
on Android. Drafts and actual records retain their original meaning. Manual Device Hub review
covered the redesigned open, book, tabletop and closed outer layouts, including
dark tabletop. Typing through open/book/tabletop preserves the draft and restores
the active converter field after reattachment. These checks used the simulator
hardware keyboard; soft-keyboard and physical-device transitions remain release work.

The 15-case model/UI suite passed on iPhone 18 Pro/iOS 27.0. The final Duo/iOS
27.1 suite passed all 16 cases, including the new rotation/focus regression. Android API 36
passed all 17 tests on both the phone emulator and the expanded Pixel 10 Pro Fold
profile.
The folding test injects book/tabletop WindowManager regions, checks complete
clock/input bounds against the hinge, and preserves text plus editing focus.
Injected folds are test geometry, not a claim of physical posture testing.

The [native visual review](NATIVE_VISUAL_REVIEW.md) contains actual application
captures, appearances, typography observations and outstanding checks. The
baseline above remains historical evidence, not screenshots of the redesign.

Capture and inspect native screens in both appearances, with these checks:

- Outer/compact, fully open, rotated, book fold and tabletop.
- Both sides of a half-window split, reduced height and keyboard visible.
- Standard and accessibility text; long times; original, invalid and unavailable states.
- 500-yard / 400-meter context, source details and unchanged original performance.
- Folding/resizing during entry, selected History detail, Add to History and native sharing.
- Safe areas and active reserved regions: no clock, action or sheet obscured by
  the fold, camera, side navigation, keyboard or system overlays.

Store screenshots follow the native implementation and this review. Physical
Duo testing, VoiceOver and device ergonomics remain release checks; a concept
preview or successful ordinary-phone CI run does not establish them.
