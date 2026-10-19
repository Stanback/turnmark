# Native visual review

Updated October 18, 2026. All images below are actual simulator/emulator captures
with sample swims. They are not mockups or store artwork. This review supersedes
the earlier header-free, large-title and mixed-surface presentations. Earlier
research and adaptive baselines remain in [Native Design Review](NATIVE_DESIGN_REVIEW.md)
and [Adaptive Layout](ADAPTIVE_LAYOUT.md).

## Default phone views

Both apps show the same entered swim: women’s 100 freestyle, 58.32 in SCY, with a
1:06.72 LCM comparison. These are also the README’s default phone images.

| iOS 27 · iPhone 18 Pro                                                                                                             | Android API 36 · phone                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| <img src="screenshots/ios-home-light.png" width="300" alt="iPhone converter with compact turnmark wordmark, cyan period and wave"> | <img src="screenshots/android-home-light.png" width="300" alt="Android converter with the same compact wordmark and navy result"> |

A compact **turnmark.** wordmark and canonical wave share one native toolbar row
with the overflow menu. The period uses the generated accent color. iOS leaves
the wordmark unframed and keeps the system glass overflow control; Android uses
its Material app bar and menu. About and published methodology are reachable
from both. At large text sizes the wordmark can yield to the wave, retaining the
Turnmark accessibility label and space for the menu.

## Surfaces and native controls

Convert, Standards and Points use one numerical surface: an opaque gradient
between generated dark navy roles, a quiet static accent ribbon, readable event
context and restrained lime hundredths/next-target emphasis. Supporting content
follows the current light/dark appearance. No independent component palette or
native dependency upgrade was introduced.

- iOS uses grouped SwiftUI Forms, native menus and segmented pickers, TabView,
  sheets and system glass actions on supported versions. Details and Share are
  quiet icon actions beside labeled Standards & points. Increased contrast and
  Reduce Transparency hide the decorative ribbon.
- Android uses Material 3 exposed dropdown fields, single-choice segmented
  choices, grouped supporting cards, sheets and native bottom navigation/rail.
  Stroke and distance share a row when space permits and stack in narrower panes
  or at large text sizes. Very narrow course/category choices use dropdowns.
- The entered swim stays separate from estimates. Destination event distance,
  course and category remain visible; original, published and derived labels
  retain their meaning. Missing targets stay missing and SCY stays unscored in
  World Aquatics points.

[iOS result, dark](screenshots/ios-native-result-dark.png) ·
[iOS result, light](screenshots/ios-native-result-light.png) ·
[Android result, light](screenshots/android-current-result-light.png)

## Shared glyphs and logging

The [shared vector catalog](../design/ICONS.md) owns the five supported stroke
icons, distance, equivalents and stopwatch-plus. iOS uses vector template PDFs;
Android uses VectorDrawables. Web, widget and MCP inline the same paths with
semantic tint. The toolbar wave derives from the existing brand geometry.
Readable labels and accessible values remain available.

| iOS stroke menu                                                                                                      | Android stroke menu                                                                                                |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| <img src="screenshots/ios-stroke-menu.png" width="300" alt="Native iOS stroke menu with five distinct vector icons"> | <img src="screenshots/android-stroke-menu.png" width="300" alt="Material stroke menu with the same vector glyphs"> |

**Log swim** uses the stopwatch-plus and opens a confirmation form for an actual
performance. Its helper reads “Add this time to My times, with an optional date
and meet.” It never records a converted estimate as a personal best. My times
retains Recent and Best times, editing, removal and portable export/import.
Web’s **Save comparison** bookmarks its conversion setup and remains separate.
See [history and backup limits](MEET_HISTORY.md).

## Standards and Points

| iOS · youth standards                                                                                                  | Android · youth standards                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| <img src="screenshots/ios-standards-light.png" width="300" alt="iOS original swim and A standard with next AA target"> | <img src="screenshots/android-youth-standards-summary.png" width="300" alt="Android original swim and matching youth benchmark"> |

| iOS · World Aquatics points                                                                                    | Android · World Aquatics points                                                                                             |
| -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| <img src="screenshots/ios-points-light.png" width="300" alt="iOS 697 points and the next 700-point milestone"> | <img src="screenshots/android-world-points.png" width="300" alt="Android 697 points using the same navy numerical surface"> |

Benchmarks use the original time/event/course/category, never a course or altitude
estimate. Separate youth/Masters ages and comparison mode persist locally. Source
editions and meet-entry limits remain visible. More coverage and validation notes
are in [the standards review](NATIVE_STANDARDS_REVIEW.md).

## Text scaling and adaptive layouts

| iOS · largest accessibility text                                                                                                                          | Android · 200% text, dark                                                                                                                       |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| <img src="screenshots/ios-native-result-largest-text.png" width="300" alt="Full iOS comparison clock with wrapping context at the largest text category"> | <img src="screenshots/android-benchmarks-large-text-dark.png" width="300" alt="Android large-text benchmark controls and missing-target state"> |

The complete result clock stays within its region. Context and labeled actions
wrap, and longer content scrolls; these captures do not claim every control fits
in one viewport. iOS regression assertions cover ordinary-size action height,
wordmark width/toolbar alignment, and largest-text clock/action bounds. Form row
virtualization is handled by the test scroll helper.

Expanded conversion keeps inputs and results in independently scrollable panes.
Tabletop places a concise result above the division and inputs below it. Drafts,
active entry and the original swim behind a benchmark sheet survive layout
changes. My times uses native single-column or list/detail navigation as space
permits.

[Duo · current expanded converter](screenshots/ios-current-duo-open.png) ·
[Android · injected book fold](screenshots/android-current-book.png) ·
[Android · injected tabletop fold](screenshots/android-current-tabletop.png)

Android’s fold pictures use injected WindowManager geometry on an emulator,
not physical fold hardware. The Duo image uses its actual inner display;
XCTest’s generic screenshot attachment is black on that simulator.

## Verification and limits

- iPhone: 19 app cases (6 storage/unit and 13 UI), followed by focused final
  header/menu, default action sizing, largest-text bounds, details, logging and
  screenshot checks. Light/dark, missing targets and stroke menus were reviewed.
- Duo/iOS 27.1: benchmark settings/points and rotation, continued typing and
  keyboard dismissal pass. Earlier open/book/tabletop/outer-display behavior is
  documented separately in the adaptive review.
- Android API 36: all 22 instrumentation cases pass at 320 dp width, including
  injected book/tabletop geometry. Final phone and expanded-fold capture cases
  also pass. Test-only size, density, navigation and demo overrides are restored.
- Generated tokens and vector exports are checked for drift. Web has 127
  unit/design checks, 35 browser cases and 19 production-runtime cases; one
  desktop-inapplicable browser case is skipped. The CI selector has 60 cases.
  MCP packed/offline tools and official AppBridge checks pass over stdio and HTTP.
- Physical-device ergonomics, VoiceOver/TalkBack, real fold transitions and store
  signing/review remain release checks. No numerical snapshot, formula, cloud
  sync or npm publication is part of this visual pass.
