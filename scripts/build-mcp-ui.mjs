import { build } from "esbuild";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const bundle = await build({
  absWorkingDir: process.cwd(),
  entryPoints: ["packages/mcp/ui/app.ts"],
  bundle: true,
  write: false,
  metafile: true,
  minify: true,
  format: "iife",
  target: "es2022",
});
// Carry the actual installed licenses for every bundled browser dependency.
// Derive this from the build graph so a dependency change cannot silently drop
// redistribution notices from the single-file resource or npm archive.
const roots = new Set();
for (const input of Object.keys(bundle.metafile.inputs)) {
  const matches = [
    ...input.matchAll(/(?:^|\/)node_modules\/((?:@[^/]+\/)?[^/]+)/g),
  ];
  const last = matches.at(-1);
  if (last) roots.add(input.slice(0, last.index + last[0].length));
}
const notices = [];
for (const root of [...roots].sort()) {
  const metadata = JSON.parse(await readFile(`${root}/package.json`, "utf8"));
  const files = (await readdir(root))
    .filter((name) => /^(licen[sc]e|notice)(\..*)?$/i.test(name))
    .sort();
  if (!files.length)
    throw new Error(`Review bundled license notices for ${metadata.name}`);
  notices.push(
    `${metadata.name}@${metadata.version}\n` +
      (
        await Promise.all(
          files.map((name) => readFile(`${root}/${name}`, "utf8")),
        )
      ).join("\n"),
  );
}
const licenseNotices = notices.join(
  "\n\n========================================\n\n",
);
await writeFile("packages/mcp/THIRD_PARTY_NOTICES.txt", licenseNotices);
const licenseJSON = JSON.stringify({ notices: licenseNotices }).replaceAll(
  "<",
  "\\u003c",
);
const css =
  (await readFile("src/generated/design-tokens.css", "utf8")) +
  (await readFile("packages/mcp/ui/app.css", "utf8"));
const wave = (await readFile("design/wave.svg", "utf8"))
  .trim()
  .replace("<svg ", '<svg aria-hidden="true" ');
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Turnmark conversion</title><style>${css}</style></head><body><main><header>${wave}<span class="wordmark">turnmark<span class="brand-dot" aria-hidden="true">.</span></span></header><section id="result" class="tm-result-surface" aria-label="Conversion result" aria-live="polite"><p>Waiting for your swim…</p></section><div id="convert" role="group" aria-label="Update comparison"><div class="edit-heading"><h2>Edit comparison</h2><p id="original"></p></div><label>Your time<input id="time" name="time" inputmode="text" maxlength="128" required autocomplete="off"></label><label>Compare in<span class="select-wrap"><select id="course" name="course"><option>SCY</option><option>SCM</option><option>LCM</option></select><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span></label><details class="calculation-options" id="calculation-options"><summary>Calculation options</summary><label>Course conversion<span class="select-wrap"><select id="method" name="method"><option value="ncaa-2025-27">NCAA (default)</option><option value="colorado-teamunify-2026">Colorado Timing</option><option value="turnmark-empirical-2026">Turnmark Equivalence</option></select><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span></label><section class="altitude-controls" aria-label="Altitude adjustment"><h3>Altitude adjustment</h3><label class="altitude-enable"><input type="checkbox" id="altitude-enabled">Adjust for altitude</label><div id="altitude-fields" hidden><label>Pool elevation<input id="elevation" type="number" min="0" max="20000" step="any" value="0"></label><label>Elevation unit<select id="elevation-unit"><option value="feet">Feet</option><option value="meters">Meters</option></select></label><label>Altitude policy<select id="altitude-policy"><option value="usa-swimming-altitude-2026">USA Swimming (default)</option><option value="ncaa-altitude-2026-27-d1">NCAA · 2026–27 Division I</option></select></label><p>Deduct altitude first, then convert courses. Meters are rounded to the nearest foot.</p></div></section></details><button id="update" type="button" disabled>Update comparison</button><button id="cancel" type="button" hidden>Cancel update</button></div><p id="status" role="status"></p></main><script>${bundle.outputFiles[0].text.replaceAll("</script", "<\\/script")}</script><script type="application/json" id="turnmark-licenses">${licenseJSON}</script></body></html>`;
if (Buffer.byteLength(html) > 750000)
  throw new Error("MCP card exceeds 750 KB budget");
await mkdir("packages/mcp/src/generated", { recursive: true });
await writeFile(
  "packages/mcp/src/generated/ui.ts",
  `// Generated by scripts/build-mcp-ui.mjs. Do not edit.\nexport const conversionHtml: string = ${JSON.stringify(html)};\n`,
);
console.log(`Bundled network-free MCP card: ${Buffer.byteLength(html)} bytes`);
