// Wave geometry and semantic palette own every launcher/favicon export.
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const geometry = await readFile("design/wave.svg", "utf8");
const tokens = JSON.parse(
  await readFile("design/turnmark.tokens.json", "utf8"),
);
const background = tokens.dark.canvas.$value.hex;
const stroke = tokens.dark.accent.$value.hex;
const path = geometry.match(/<path d="([^"]+)"[^>]+stroke-width="([^"]+)"/);
if (!path)
  throw new Error("Expected the canonical wave path in design/wave.svg");
const [, wave, width] = path;
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="${background}"/><path d="${wave}" fill="none" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round"/></svg>\n`;
const digest = (content) => createHash("sha256").update(content).digest("hex");
const sourceHash = digest(
  geometry +
    background +
    stroke +
    tokens.light.canvas.$value.hex +
    (await readFile(fileURLToPath(import.meta.url), "utf8")),
);
const manifestPath = "design/brand-manifest.json";
const exported = [];
if (process.argv.includes("--check")) {
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  if (manifest.sourceHash !== sourceHash)
    throw new Error(
      "Brand sources changed. Run node scripts/generate-brand-assets.mjs.",
    );
  for (const [file, hash] of Object.entries(manifest.files))
    if (digest(await readFile(file)) !== hash)
      throw new Error(`Brand export changed: ${file}. Regenerate the assets.`);
  console.log(
    "Verified committed brand exports against their source and palette.",
  );
  process.exit(0);
}
const assets = "apps/ios/Sources/Assets.xcassets";
const res = "apps/android/src/main/res";
const json = (value) => JSON.stringify(value, null, 2) + "\n";
async function output(file, content) {
  await mkdir(file.slice(0, file.lastIndexOf("/")), { recursive: true });
  await writeFile(file, content);
  exported.push(file);
}
const info = { author: "xcode", version: 1 };
await output(`${assets}/Contents.json`, json({ info }));
await output(
  `${assets}/AppIcon.appiconset/Contents.json`,
  json({
    images: [
      {
        filename: "AppIcon.png",
        idiom: "universal",
        platform: "ios",
        size: "1024x1024",
      },
    ],
    info,
  }),
);
await output("public/icons/app-icon.svg", svg);
await output("public/favicon.svg", svg);
const webManifest = JSON.parse(
  await readFile("public/manifest.webmanifest", "utf8"),
);
webManifest.background_color = tokens.light.canvas.$value.hex;
webManifest.theme_color = background;
await output("public/manifest.webmanifest", json(webManifest));
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: 1024, height: 1024 },
    deviceScaleFactor: 1,
  });
  await page.setContent(
    `<style>html,body{margin:0;width:100%;height:100%}svg{display:block;width:100%;height:100%}</style>${svg}`,
  );
  for (const [size, file] of [
    [1024, `${assets}/AppIcon.appiconset/AppIcon.png`],
    [512, "public/icons/icon-512.png"],
    [192, "public/icons/icon-192.png"],
    [180, "public/icons/icon-180.png"],
  ]) {
    await page.setViewportSize({ width: size, height: size });
    await page.screenshot({ path: file });
    exported.push(file);
  }
} finally {
  await browser.close();
}
const declaration = '<?xml version="1.0" encoding="utf-8"?>\n';
const vector = (size, body) =>
  `${declaration}<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="${size}dp" android:height="${size}dp" android:viewportWidth="512" android:viewportHeight="512">\n${body}\n</vector>\n`;
const wavePath = `    <path android:pathData="${wave}" android:strokeColor="${stroke}" android:strokeWidth="${width}" android:strokeLineCap="round" android:fillColor="@android:color/transparent" />`;
// The waves occupy the adaptive icon safe zone; the OS supplies the mask/effects.
await output(
  `${res}/drawable/ic_launcher_foreground.xml`,
  vector(108, wavePath),
);
await output(
  `${res}/values/brand.xml`,
  `${declaration}<resources>\n    <color name="launcher_background">${background}</color>\n</resources>\n`,
);
for (const version of [26, 33]) {
  await output(
    `${res}/mipmap-anydpi-v${version}/ic_launcher.xml`,
    `${declaration}<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n    <background android:drawable="@color/launcher_background" />\n    <foreground android:drawable="@drawable/ic_launcher_foreground" />\n${version >= 33 ? '    <monochrome android:drawable="@drawable/ic_launcher_foreground" />\n' : ""}</adaptive-icon>\n`,
  );
}
await output(
  manifestPath,
  json({
    sourceHash,
    files: Object.fromEntries(
      await Promise.all(
        exported.map(async (file) => [file, digest(await readFile(file))]),
      ),
    ),
  }),
);
console.log(
  "Exported web, iOS and Android branding from design/wave.svg and the shared palette",
);
