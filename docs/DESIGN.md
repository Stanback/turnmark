# Visual direction

The web converter follows Bri’s October 18, 2026 desktop and mobile references:
quiet navy surfaces in dark appearance, cyan accents, and lime highlighting for
the selected course and result hundredths. Light appearance uses the same
hierarchy on pale surfaces. The wave mark stays in the compact website header.

The event picker combines stroke and distance. Direct time entry updates results
as you type; the mobile results button moves to the result rather than submitting
a calculation. One large result carries its destination event and pool length,
with the original input and selectable course equivalents below. Published
factors, derived estimates, altitude corrections and unavailable results retain
their distinctions. Displayed event distances come from the shared engine’s
mapping, so a 500-yard swim can have a 400-meter equivalent.

The photograph and animated pool diagram are absent from the converter. Keep
results readable rather than adding decorative race or lane visualizations.
History starts empty and shows real local activity. Detailed standards, points,
methodology and FAQs remain below the main converter, with navigation to each.
Mobile keeps its results shortcut and persistent Converter/History/Standards
navigation. Methodology is available beside the result and in the footer.

The [shared design contract](DESIGN_CONTRACT.md) owns the semantic palette and
records how widget/native adoption preserves platform conventions.

Converter styles live in `src/converter.css`; `src/app.css` holds the shared
foundation and secondary views. Review both appearances, keyboard operation,
long times and narrow-screen wrapping when changing the hierarchy. These are
web conventions; native apps retain their platform-specific presentation.

The earlier generated swimming photograph remains a social-preview asset. See
[image asset provenance](IMAGE_ASSETS.md) for its generation details.

## Converter screenshots

Captured from the production build with sample inputs. Mobile images show the
initial viewport and the result reached with “See your results.” The full page
also includes history, standards and methodology below these views.

| View          | Dark                                             | Light                                             |
| ------------- | ------------------------------------------------ | ------------------------------------------------- |
| Desktop       | [Converter](screenshots/web-desktop-dark.png)    | [Converter](screenshots/web-desktop-light.png)    |
| Mobile input  | [Input](screenshots/web-mobile-dark.png)         | [Input](screenshots/web-mobile-light.png)         |
| Mobile result | [Result](screenshots/web-mobile-result-dark.png) | [Result](screenshots/web-mobile-result-light.png) |
