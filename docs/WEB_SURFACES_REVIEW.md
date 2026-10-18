# Water, light and interaction

The converter header now has a decorative inline SVG with uneven water contours,
a small cyan origin and three outward ripples. Motion ends after 4.8 seconds;
reduced-motion settings retain the still illustration. A radial wash fades into
the header. The illustration and wash are hidden at 760 pixels and below so the
mobile form stays close to the heading. There is no image download, animation
library, pointer tracker or calculation change.

Input and result cards use layered radial lighting; the result has the stronger
upper-corner glow. Fine-pointer hover and keyboard focus add a small glow without
moving the card. Action/course buttons shift their sheen. Reduced motion disables
those transitions. Course rows have a wider rounded hit/hover area while their
labels, times and dividers keep the existing alignment.

Three decorative marks mirror the selected SCY, SCM or LCM result. The top source
chip is removed; the calculation explanation and official NCAA source remain in
the methodology. Reset has a glyph, the privacy note lives in the footer, and
its wordmark uses the same type weight and colored dot as the header. The theme
controls have a named Appearance landmark.

Validation: Svelte/TypeScript; unit, browser and production suites; direct
Chromium and WebKit checks in light/dark with no Axe violations, stable hover
bounds, all three indicator states, 320–1440-pixel layouts without horizontal
overflow, reduced motion and finite animation. Screenshots use actual calculated
values, not illustrative conversion ratios. This web-only change needs no native
rebuild.

![Dark converter with ripple and pooled cyan light](screenshots/web-liquid-surfaces-dark.png)

![Light appearance and result controls](screenshots/web-liquid-surfaces-light.png)
