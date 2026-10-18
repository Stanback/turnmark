// Mechanical exports of the existing web wave mark. Edit its SVG, then rerun.
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const svg = await readFile("public/icons/app-icon.svg", "utf8");
const path = svg.match(
  /<path d="([^"]+)"[^>]+stroke="([^"]+)"[^>]+stroke-width="([^"]+)"/,
);
const background = svg.match(/<rect[^>]+fill="([^"]+)"/)[1];
if (!path) throw new Error("Expected the canonical wave path in app-icon.svg");
const [, wave, stroke, width] = path;
const assets = "apps/ios/Sources/Assets.xcassets";
const res = "apps/android/src/main/res";
const json = (value) => JSON.stringify(value, null, 2) + "\n";
async function output(file, content) {
  await mkdir(file.slice(0, file.lastIndexOf("/")), { recursive: true });
  await writeFile(file, content);
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
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: 1024, height: 1024 },
    deviceScaleFactor: 1,
  });
  await page.setContent(
    `<style>html,body{margin:0;width:100%;height:100%}svg{display:block;width:100%;height:100%}</style>${svg}`,
  );
  await page.screenshot({ path: `${assets}/AppIcon.appiconset/AppIcon.png` });
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
console.log("Exported iOS and Android branding from public/icons/app-icon.svg");
