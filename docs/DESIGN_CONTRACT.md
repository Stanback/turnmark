# Turnmark design contract

Turnmark should be recognizable across the web, embedded widget, native apps and
MCP Apps: the same wave identity, navy/cyan palette, restrained lime result
emphasis, readable times and precise event context. Platform adapters implement
that identity using their own controls and accessibility behavior.

## Ownership and current adoption

`design/turnmark.tokens.json` owns semantic light/dark colors, a small spacing
scale and default custom-content radii. It uses the literal color and dimension
subset of the [DTCG Format Module 2025.10](https://www.designtokens.org/tr/2025.10/format/),
with Turnmark contract version 1 in `$extensions`. Light and dark are explicit
groups, not an implementation of the separate DTCG Resolver specification.

| Consumer                      | Current status                                                | Adapter boundary                                                |
| ----------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------- |
| Web converter                 | Generated palette and selected spacing/radius roles           | CSS variables; responsive web layout                            |
| Web history/standards/dialogs | Generated palette across benchmarks, dialogs and interactions | CSS variables; semantic hover/focus/error states                |
| Widget/MCP setup pages        | Shared palette, fonts, content width and brand header         | Static HTML/CSS; readable without JavaScript                    |
| Embedded widget               | Generated palette, control boundaries and result emphasis     | Compact stylesheet and appearance selection                     |
| iOS                           | Generated screen palette; native controls and result adopted  | SwiftUI palette and semantic system text styles                 |
| Android                       | Generated screen palette; native controls and result adopted  | Kotlin colors mapped into Material 3 and custom result roles    |
| MCP Apps                      | Inline conversion card; official bridge verified              | Shared web tokens plus host theme and accessibility preferences |

The contract is a foundation, not a claim that every screen is already aligned.
Do not create a shared UI runtime, move styling into the calculation SDK, or add
runtime JSON parsing to native screens. Add each generated native adapter when
its consuming screen adopts it, and verify both native platforms together.

Edit source values, then regenerate and verify the committed CSS, Swift and Kotlin outputs:

```sh
node design/generate.mjs
node design/generate.mjs --check
node scripts/generate-brand-assets.mjs
node scripts/generate-brand-assets.mjs --check
npm test
```

`src/generated/design-tokens.css`, `apps/ios/Sources/TurnmarkPalette.swift` and
`apps/android/src/main/java/net/stanback/turnmark/TurnmarkTokens.kt` are derived outputs. The small generator supports
our opaque sRGB colors and pixel dimensions, rejects unsupported inputs, checks
matching mode roles, and verifies the human-readable hex against sRGB components.
It is not a general DTCG translator. A future adapter must read the same source.

## Color roles

| Roles                                                | Meaning                                                          |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| `canvas`, `surface`, `surfaceRaised`, `surfaceInput` | Content background, opaque card, raised content, time entry      |
| `text`, `textMuted`                                  | Primary text and readable secondary context/provenance           |
| `borderSubtle`, `borderControl`                      | Decorative dividers versus visible interactive boundaries        |
| `accent`                                             | Links, focus and accent text on content surfaces                 |
| `actionFill`, `onAction`                             | A paired filled-action background and foreground                 |
| `resultHighlight`                                    | Selected time/hundredths and selected course emphasis            |
| `selectedSurface`                                    | Selected course fill, alongside a checkmark and accessible state |
| `error`                                              | Invalid input, accompanied by a specific message                 |

Dark raised controls use a deeper blue navy, with matching input, selected and
divider roles. These shared roles keep web history, benchmark help and native
controls in one tonal family; the water artwork can remain teal.

Cyan identifies actions and the brand. Lime emphasizes the selected comparison;
it does not mean a qualifying time, success or permission to enter a meet. Keep
published benchmark status separate. Never rely on color alone for selection,
availability or errors. The lighter action fill needs its dark `onAction` text;
use `accent` for a readable link on a light surface. Do not map the light action
fill blindly to every Material primary/text role.

For iOS adoption, use the appearance-dependent `accent` role as the starting
native tint: deeper teal on light surfaces and brighter cyan in dark appearance.
Keep lime for result emphasis rather than links or general controls. Check
actual SwiftUI/Liquid Glass control foregrounds and selected states in both
appearances; content-surface contrast tests alone do not validate system tint.

Tests protect at least 4.5:1 contrast for text/accent/highlight/error on their
intended content surfaces, and 3:1 for control boundaries. Decorative dividers
are not control outlines. These palette checks complement actual rendered
accessibility checks; they do not validate gradients, opacity or system chrome.
System increased-contrast and reduced-transparency settings take precedence.

## Typography, spacing and shape

Share roles and emphasis rather than one fixed font-size table:

| Role                | Web/widget                                              | iOS                                                                          | Android                                                |
| ------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| Result time         | Manrope, strong weight, tabular digits, responsive size | System font, monospaced digits, `@ScaledMetric` relative to large-title role | Material headline/display role in `sp`, tabular digits |
| Event context       | Clear body/subheading above the time                    | Semantic subheadline/headline                                                | Material title/body role                               |
| Main controls       | Readable body/label                                     | Standard SwiftUI control typography                                          | Material component typography                          |
| Provenance and help | At least 12px base; zoom/reflow                         | Semantic caption/footnote with Dynamic Type                                  | Material body/label with font scaling                  |

The 4–32 spacing values describe logical rhythm, not physical screen pixels.
Web emits CSS px; native adapters use points/dp for layout and semantic scaled
text roles for typography. Custom cards/controls share softly rounded shapes.
The control radius does not replace native picker, button, tab or sheet geometry.
Do not force all screens into the same density, shrink readable text to preserve
a fixed card height, or cap accessibility text sizes. Reflow controls and let the
result scroll when large text or the keyboard needs space.

## Benchmark hierarchy

Choose the assessed swim before choosing a benchmark. The web uses one grouped
entered/converted selector with both times and courses, followed by a single
**Compare against** dropdown on its own row at every viewport width. Group its
options under **Time standards** (`USA Swimming · Youth`, `USA Swimming · Futures`,
`Junior Nationals` / `USA Swimming · Junior Nationals`, `NISCA · All-America`,
`USMS · Masters`) and **Points** (`World Aquatics points`); do not add a separate
mode switch or provider picker. Native screens keep their platform pickers in the
same order: SwiftUI menu sections on iOS and a grouped Material exposed dropdown
on Android. Existing benchmark and age preferences remain intact when switching
to points and back. Unsupported estimates never fall back to the entered swim.

A small mountain belongs to the converted choice only when an available engine
result includes a nonzero altitude deduction. Enabling the setting, entering an
elevation below the threshold, or selecting a policy with zero credit does not
show an adjusted marker. Keep the original swim unchanged and expose the
adjustment through accessible text and calculation details as well as the icon.

## Result and terminology contract

1. Destination event and actual distance/units, course and relevant category.
2. A dominant time. Hundredths may carry result emphasis; the complete time must
   remain one understandable accessible value.
3. Original input and any altitude correction remain distinguishable.
4. Kind stays visible: **Original time** (compact **Original**), **Published
   factor**, **Derived estimate**, or **Unavailable**. Invalid input shows no
   stale time. Native wording follows these kinds.
5. “How this is calculated” / native Details exposes the multiplier, source,
   edition and explanation. Benchmark/eligibility distinctions stay intact.

Use the engine's returned destination event; 500 yards can become 400 meters.
A saved conversion is not a recorded race, a personal best or a logged meet swim.
Keep conversion history and actual-swim history clearly named on each surface.
MCP text fallback must retain the same context and provenance as its future UI.

Native navigation is **Convert · My times**. **Log swim** confirms an actual
performance, date and optional meet. From Convert it prefills the entered swim;
from My times it starts with a blank time. **Recent / Best times** filters actual
records; a recorded swim can reopen a course comparison without changing the
performance. The current comparison draft persists, but comparison recents are
not implemented. Sharing remains directly available from Convert. An older saved
comparison stays accessible as **Previous saved comparison**, with explicit use
and removal actions; it never silently becomes an actual swim or personal best.
See [native product notes](NATIVE_PRODUCT_NOTES.md) for the workflow evidence and
entry-eligibility distinction.

Course education is optional supporting detail. A short explanation may use
100m as an example: three turns in SCM versus one in LCM. The converter uses
published factors, not an individual model of turns, push-offs or race splits.
Do not restore decorative lane animation or imply that turn counts explain the
numerical factor exactly. If counts are later shown, use the actual destination
event and supported whole pool lengths, not the entered distance for every course.

## Platform experience remains authoritative

- **iOS:** retain SwiftUI navigation, pickers, sheets, sharing, keyboard Done and
  system Liquid Glass controls. Convert uses a grouped Form and the existing
  native TabView. The signature numerical card uses the shared dark palette in both appearances,
  including contrasting action colors. Its subtle static gradient runs from dark
  `surfaceRaised` at the top leading corner to dark `surface` at the bottom
  trailing corner on both native platforms; both stops are opaque generated
  palette roles. Convert, standards and points share the same numerical surface,
  including a quiet static wave ribbon derived from the accent role. iOS hides
  that decoration with increased contrast or reduced transparency. Surrounding content uses the current
  appearance. This gives the result a stable identity without repainting native
  forms and navigation.
  System materials respond to accessibility preferences; do not replace the tab
  bar or sheet with a painted web imitation. Apple documents automatic Liquid
  Glass adoption in standard controls and its accessibility behavior in
  [Liquid Glass](https://developer.apple.com/documentation/technologyoverviews/liquid-glass)
  and [Materials](https://developer.apple.com/design/human-interface-guidelines/materials).
- **Android:** retain Compose/Material navigation, menus, sheets, back behavior,
  IME insets and touch semantics. Map brand colors into complete, contrasting
  Material roles; use separate custom result roles where necessary. Preserve
  default touch-target behavior and font scaling. Course/category selectors use
  native single-choice segmented rows; event and benchmark settings use exposed
  dropdown text fields. Summary cards share Convert's numerical surface, while
  supporting content uses grouped appearance-dependent Material cards. See [Material 3 theming](https://developer.android.com/develop/ui/compose/designsystems/material3)
  and [Compose accessibility defaults](https://developer.android.com/develop/ui/compose/accessibility/api-defaults).
  Wallpaper-derived dynamic color is an optional future preference, not a
  requirement to replace Turnmark's brand colors.
- **Web:** retain keyboard and browser navigation, reflow, theme preference,
  reduced motion and useful static HTML. Mobile web navigation follows Converter,
  Standards and History; methodology is contextual and in the footer.
- **Widget:** keep its compact embed contract, keyboard labels, small-width
  layout, host isolation and explicit/automatic appearance options. Identity and
  result hierarchy carry across without the website hero or navigation.

## Adoption and assets

The [shared swim glyphs](../design/ICONS.md) use one path catalog for web,
widget, MCP Apps and native template vectors. Keep their stroke proportions
consistent and let each host apply its existing semantic tint. Native menus,
navigation and actions retain their platform behavior.

The paired native adoption is separate from the web and widget adapters. Show light/dark and large-text screenshots using the
same sample swims. Review invalid, unavailable, original and derived results,
yard/metric mappings, focus, contrast, keyboard space and native sharing.
Update [CI selection](CI.md) as each generated adapter becomes a real consumer;
web-only layout changes must continue to skip native builds.

`design/wave.svg` owns the wave geometry. The brand exporter uses the shared
dark canvas/accent pair for the opaque navy/cyan mark, independent of the current
appearance. It regenerates raster favicons, PWA icons, the iOS app icon and Android
adaptive/monochrome exports together. The committed brand manifest checks source
and output hashes in the unit suite, preventing silent export drift. Raster
favicon URLs stay stable. Store screenshots and promotional
artwork follow the native adoption so they represent actual screens; layered iOS
icon artwork and physical-device/store release checks remain explicit work.

The [adaptive-layout brief](ADAPTIVE_LAYOUT.md) records the researched iPhone Duo
constraints, proposed expanded/compact workflows and simulator/physical-device
acceptance matrix for the paired native adoption.

## Shared vector glyphs

The [canonical glyph catalog](../design/ICONS.md) supplies native template/vector
assets and inline web/widget/MCP SVG paths. Supported stroke icons, distance and
course equivalents accompany labels and inherit semantic tint. The toolbar wave
derives from the existing brand geometry; the stopwatch-plus marks **Log swim**,
which confirms an actual performance. Web’s **Save comparison** bookmarks a
conversion setup without creating a performance record.

[Glyph board](screenshots/shared-swim-icons.png) ·
[Responsive widget](screenshots/widget-icons-dark.png) ·
[Mobile age selector](screenshots/web-age-mobile-dark.png) ·
[MCP card](screenshots/mcp-card-dark-narrow.png)

The mobile web age controls reserve room for the full selected label and the
native arrow. Their edition metadata wraps onto a separate row on narrow phones.

Web consumers can use the generated `.tm-result-surface` scope for the signature
numerical card. It applies the same canonical dark roles in either host
appearance, matching the generated native result palettes. Supporting forms and
navigation continue to use the host appearance; do not copy dark hex values into
consumer styles.
