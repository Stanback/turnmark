# Turnmark mark

The two-wave mark in `public/icons/app-icon.svg` is shared by the website and
native app icons. The navy field and white waves remain legible at launcher-icon
sizes; the platforms supply their own icon masks. The native converter opens
straight into its inputs, without a logo, app-name header or promotional title.
Saved and Method retain functional page titles.

On Android 12+, the system splash shows the launcher mark against a background
that matches the app's appearance. iOS uses a matching light/dark launch background
and opens directly into the form. Neither platform adds a timed splash or spinner.
See [the design review](NATIVE_DESIGN_REVIEW.md) for the store comparisons and
platform guidance behind this choice.

After editing the canonical SVG, regenerate the native assets:

```sh
# With npm dependencies and Playwright Chromium installed:
node scripts/generate-brand-assets.mjs
```

The exporter writes the opaque 1024px iOS app icon, Android adaptive launcher
foreground/background, and Android 13+ monochrome icon. Commit those generated resources. Ordinary native builds
do not need Node or a browser to produce their icons.

The iOS icon is a flat asset-catalog icon for now. Layered Icon Composer artwork
and its light/dark/clear/tinted previews remain part of store-artwork refinement.
No lighting, rounded mask, or simulated glass is baked into the app icon.
