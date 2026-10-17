import { readFile, writeFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { createEngine } from "../packages/engine/dist/index.js";
const wasm = await readFile(
  new URL(
    "../packages/engine/dist/generated/turnmark_wasm_bg.wasm",
    import.meta.url,
  ),
);
const started = performance.now();
const engine = await createEngine({ wasm });
const initialized = performance.now();
engine.convert({
  swim: {
    time: "1:00",
    event: { distance: 100, stroke: "freestyle", course: "LCM" },
  },
  to: "SCY",
  table: "women",
});
const firstCall = performance.now();
const data = {};
for (const name of [
  "conversions",
  "standards",
  "masters",
  "points",
  "sources",
]) {
  const bytes = await readFile(
    new URL(`../data/${name}.json`, import.meta.url),
  );
  data[name] = createHash("sha256").update(bytes).digest("hex");
}
const result = {
  version: engine.version,
  sourceCommit: spawnSync("git", ["rev-parse", "HEAD"], {
    encoding: "utf8",
  }).stdout.trim(),
  sourceDirty:
    spawnSync("git", ["status", "--porcelain"], { encoding: "utf8" }).stdout
      .length > 0,
  runtime: `${process.version} ${process.platform}/${process.arch}`,
  rust: spawnSync("rustc", ["--version"], { encoding: "utf8" }).stdout.trim(),
  dataSha256: data,
  wasmBytes: wasm.length,
  wasmGzipBytes: gzipSync(wasm, { level: 9 }).length,
  initializationMs: initialized - started,
  firstConversionMs: firstCall - initialized,
};
await writeFile(
  "target/engine-metrics.json",
  JSON.stringify(result, null, 2) + "\n",
);
console.log(JSON.stringify(result, null, 2));
