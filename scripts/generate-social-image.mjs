// Render the share card from existing brand assets, fonts and semantic tokens.
import { readFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const palette = JSON.parse(
  readFileSync("design/turnmark.tokens.json", "utf8"),
).dark;
const data = (path, mime) =>
  `data:${mime};base64,${readFileSync(path).toString("base64")}`;
const fonts = ["Manrope", "DM Sans"]
  .map((name) => {
    const slug = name.toLowerCase().replaceAll(" ", "-");
    return `@font-face { font-family: '${name}'; font-weight: 100 900; src: url('${data(`node_modules/@fontsource-variable/${slug}/files/${slug}-latin-wght-normal.woff2`, "font/woff2")}') format('woff2'); }`;
  })
  .join("\n");
const wave = readFileSync("design/wave.svg", "utf8")
  .replace('viewBox="0 0 512 512"', 'viewBox="96 96 320 320"')
  .replace("currentColor", palette.accent.$value.hex);
const html = readFileSync("design/social-card.html", "utf8")
  .replace("__FONTS__", fonts)
  .replace(
    "__TOKENS__",
    ["canvas", "text", "textMuted", "accent"]
      .map((role) => `--${role}: ${palette[role].$value.hex};`)
      .join("\n"),
  )
  .replace("__WATER__", data("public/images/water-ribbons.webp", "image/webp"))
  .replace(
    "__WAVE__",
    `data:image/svg+xml;base64,${Buffer.from(wave).toString("base64")}`,
  );
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 630 },
    deviceScaleFactor: 1,
  });
  await page.setContent(html);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((image) => image.decode()));
  });
  mkdirSync("public/images", { recursive: true });
  await page.screenshot({ path: "public/images/turnmark-social-v1.png" });
  console.log("Rendered 1200 × 630 Turnmark social card.");
} finally {
  await browser.close();
}
