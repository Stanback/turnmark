# Turnmark mark

The two-wave mark in `public/icons/app-icon.svg` is shared by the website and
native apps. The native headers pair it with the system-font `turnmark.`
wordmark. The navy field and white waves remain legible at launcher-icon sizes;
the platforms supply their own icon masks.

After editing the canonical SVG, regenerate the native assets:

```sh
# With npm dependencies and Playwright Chromium installed:
node scripts/generate-brand-assets.mjs
```

The exporter writes the iOS vector header asset and opaque 1024px app icon,
Android vector header mark, adaptive launcher foreground/background, and Android
13+ monochrome icon. Commit those generated resources. Ordinary native builds
do not need Node or a browser to produce their icons.

The iOS icon is a flat asset-catalog icon for now. Layered Icon Composer artwork
and its light/dark/clear/tinted previews remain part of store-artwork refinement.
No lighting, rounded mask, or simulated glass is baked into the app icon.
