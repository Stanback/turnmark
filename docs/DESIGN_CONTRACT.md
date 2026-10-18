# Turnmark design contract

Turnmark should be recognizable across the web, embedded widget, native apps and
future MCP Apps: the same wave identity, navy/cyan palette, restrained lime result
emphasis, readable times and precise event context. Platform adapters implement
that identity using their own controls and accessibility behavior.

## Ownership and current adoption

`design/turnmark.tokens.json` owns semantic light/dark colors, a small spacing
scale and default custom-content radii. It uses the literal color and dimension
subset of the [DTCG Format Module 2025.10](https://www.designtokens.org/tr/2025.10/format/),
with Turnmark contract version 1 in `$extensions`. Light and dark are explicit
groups, not an implementation of the separate DTCG Resolver specification.

| Consumer                      | Current status                                               | Adapter boundary                                                               |
| ----------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Web converter                 | Uses the generated palette and selected spacing/radius roles | CSS variables; responsive web layout                                           |
| Web history/standards/dialogs | Inherits base text roles; some older styles remain           | Further component-by-component adoption                                        |
| Embedded widget               | Existing independent palette; adoption next                  | Its own compact stylesheet and appearance selection                            |
| iOS                           | Shared launcher palette; screen palette adoption next        | Generated named colors or a small SwiftUI palette; semantic system text styles |
| Android                       | Shared launcher palette; screen palette adoption next        | Generated Kotlin colors mapped into Material 3 roles and custom result roles   |
| MCP Apps                      | Research/design only                                         | Shared web tokens plus host theme and accessibility preferences                |

The contract is a foundation, not a claim that every screen is already aligned.
Do not create a shared UI runtime, move styling into the calculation SDK, or add
runtime JSON parsing to native screens. Add each generated native adapter when
its consuming screen adopts it, and verify both native platforms together.

Edit source values, then regenerate and verify the committed web output:

```sh
node design/generate.mjs
node design/generate.mjs --check
node scripts/generate-brand-assets.mjs
node scripts/generate-brand-assets.mjs --check
npm test
```

`src/generated/design-tokens.css` is derived output. The small generator supports
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

Cyan identifies actions and the brand. Lime emphasizes the selected comparison;
it does not mean a qualifying time, success or permission to enter a meet. Keep
published benchmark status separate. Never rely on color alone for selection,
availability or errors. The lighter action fill needs its dark `onAction` text;
use `accent` for a readable link on a light surface. Do not map the light action
fill blindly to every Material primary/text role.

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

## Result and terminology contract

1. Destination event and actual distance/units, course and relevant category.
2. A dominant time. Hundredths may carry result emphasis; the complete time must
   remain one understandable accessible value.
3. Original input and any altitude correction remain distinguishable.
4. Kind stays visible: **Original time** (compact **Original**), **Published
   factor**, **Derived estimate**, or **Unavailable**. Invalid input shows no
   stale time. Native wording will be aligned during adoption.
5. “How this is calculated” / native Details exposes the multiplier, source,
   edition and explanation. Benchmark/eligibility distinctions stay intact.

Use the engine's returned destination event; 500 yards can become 400 meters.
A saved conversion is not a recorded race, a personal best or a logged meet swim.
Keep conversion history and actual-swim history clearly named on each surface.
MCP text fallback must retain the same context and provenance as its future UI.

Course education is optional supporting detail. A short explanation may use
100m as an example: three turns in SCM versus one in LCM. The converter uses
published factors, not an individual model of turns, push-offs or race splits.
Do not restore decorative lane animation or imply that turn counts explain the
numerical factor exactly. If counts are later shown, use the actual destination
event and supported whole pool lengths, not the entered distance for every course.

## Platform experience remains authoritative

- **iOS:** retain SwiftUI navigation, pickers, sheets, sharing, keyboard Done and
  system Liquid Glass controls. Opaque numerical content uses the shared palette.
  System materials respond to accessibility preferences; do not replace the tab
  bar or sheet with a painted web imitation. Apple documents automatic Liquid
  Glass adoption in standard controls and its accessibility behavior in
  [Liquid Glass](https://developer.apple.com/documentation/technologyoverviews/liquid-glass)
  and [Materials](https://developer.apple.com/design/human-interface-guidelines/materials).
- **Android:** retain Compose/Material navigation, menus, sheets, back behavior,
  IME insets and touch semantics. Map brand colors into complete, contrasting
  Material roles; use separate custom result roles where necessary. Preserve
  default touch-target behavior and font scaling. See [Material 3 theming](https://developer.android.com/develop/ui/compose/designsystems/material3)
  and [Compose accessibility defaults](https://developer.android.com/develop/ui/compose/accessibility/api-defaults).
  Wallpaper-derived dynamic color is an optional future preference, not a
  requirement to replace Turnmark's brand colors.
- **Web:** retain keyboard and browser navigation, reflow, theme preference,
  reduced motion and useful static HTML. Mobile navigation prioritizes Converter,
  History and Standards; methodology is contextual and in the footer.
- **Widget:** keep its compact embed contract, keyboard labels, small-width
  layout, host isolation and explicit/automatic appearance options. Identity and
  result hierarchy carry across without the website hero or navigation.

## Adoption and assets

After the web direction is reviewed, adopt the widget and then the paired native
screens in separate PRs. Show light/dark and large-text screenshots using the
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
