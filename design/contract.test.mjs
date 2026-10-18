import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import process from "node:process";
import { expect, test } from "vitest";

const tokens = JSON.parse(
  readFileSync(new URL("./turnmark.tokens.json", import.meta.url), "utf8"),
);
const luminance = (hex) => {
  const rgb = [1, 3, 5].map((start) => {
    const channel = parseInt(hex.slice(start, start + 2), 16) / 255;
    return channel <= 0.04045
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
};
const contrast = (first, second) => {
  const a = luminance(first),
    b = luminance(second);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
};

test("committed CSS matches the validated design contract", () => {
  const result = spawnSync(
    process.execPath,
    ["design/generate.mjs", "--check"],
    { encoding: "utf8" },
  );
  expect(result.status, result.stderr).toBe(0);
});
for (const mode of ["light", "dark"]) {
  test(`${mode} content, accent and error roles meet normal-text contrast`, () => {
    const color = (role) => tokens[mode][role].$value.hex;
    for (const foreground of [
      "text",
      "textMuted",
      "accent",
      "resultHighlight",
      "error",
    ])
      for (const background of [
        "canvas",
        "surface",
        "surfaceRaised",
        "surfaceInput",
        "selectedSurface",
      ])
        expect(
          contrast(color(foreground), color(background)),
          `${mode}: ${foreground} on ${background}`,
        ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrast(color("onAction"), color("actionFill")),
    ).toBeGreaterThanOrEqual(4.5);
  });
  test(`${mode} control borders remain distinct from their surfaces`, () => {
    for (const background of [
      "canvas",
      "surface",
      "surfaceRaised",
      "surfaceInput",
    ])
      expect(
        contrast(
          tokens[mode].borderControl.$value.hex,
          tokens[mode][background].$value.hex,
        ),
        `${mode}: borderControl on ${background}`,
      ).toBeGreaterThanOrEqual(3);
  });
}

test("committed brand exports match the wave and palette source", () => {
  const result = spawnSync(
    process.execPath,
    ["scripts/generate-brand-assets.mjs", "--check"],
    { encoding: "utf8" },
  );
  expect(result.status, result.stderr).toBe(0);
});
