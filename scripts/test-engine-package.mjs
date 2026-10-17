import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "turnmark-rust-package-"));
function run(command, args, cwd = root) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: "utf8",
    maxBuffer: 4 * 1024 * 1024,
  });
  assert.equal(
    result.status,
    0,
    `${command}: ${result.error ?? ""}\n${result.stdout}\n${result.stderr}`,
  );
  return result.stdout;
}
try {
  const tarballs = [];
  for (const name of ["@turnmark/sdk", "@turnmark/engine"]) {
    const [packed] = JSON.parse(
      run("npm", [
        "pack",
        "--workspace",
        name,
        "--pack-destination",
        temporary,
        "--json",
      ]),
    );
    if (name === "@turnmark/engine") {
      const files = new Set(packed.files.map(({ path }) => path));
      for (const required of [
        "LICENSE",
        "README.md",
        "dist/index.js",
        "dist/index.d.ts",
        "dist/generated/turnmark_wasm_bg.wasm",
      ])
        assert.ok(files.has(required), required);
    }
    tarballs.push(join(temporary, packed.filename));
  }
  await writeFile(
    join(temporary, "package.json"),
    JSON.stringify({ private: true, type: "module" }),
  );
  run(
    "npm",
    [
      "install",
      "--offline",
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      ...tarballs,
    ],
    temporary,
  );
  await writeFile(
    join(temporary, "consumer.mjs"),
    `
    import assert from 'node:assert/strict';
    import { readFile } from 'node:fs/promises';
    import { createEngine } from '@turnmark/engine';
    const engine = await createEngine({ wasm: await readFile(new URL(import.meta.resolve('@turnmark/engine/engine.wasm'))) });
    const result = engine.convert({ swim: { time: '1:00', event: {distance: 100, stroke: 'freestyle', course: 'LCM'} }, table: 'women', to: 'SCY' });
    assert.equal(result.status, 'available');
    assert.equal(result.value.hundredths, 5244);
    assert.equal(engine.parseTime('1:60'), null);
  `,
  );
  run("node", ["consumer.mjs"], temporary);
  await writeFile(
    join(temporary, "consumer.ts"),
    `
    import { createEngine, type Engine } from '@turnmark/engine';
    const engine: Readonly<Engine> = await createEngine({wasm: new Uint8Array()});
    const result = engine.convert({ swim: {time: '1:00', event: {distance: 100, stroke: 'freestyle', course: 'LCM'}}, table: 'women', to: 'SCY' });
    if (result.status === 'available') { const ticks: number = result.value.hundredths; console.log(ticks); }
    // @ts-expect-error actual stroke names are part of the public contract
    engine.convert({swim: {time: '1:00', event: {distance: 100, stroke: 'FR', course: 'LCM'}}, table: 'women', to: 'SCY'});
  `,
  );
  run(
    join(root, "node_modules/.bin/tsc"),
    [
      "--noEmit",
      "--strict",
      "--module",
      "NodeNext",
      "--moduleResolution",
      "NodeNext",
      "--target",
      "ES2022",
      "--ignoreConfig",
      "consumer.ts",
    ],
    temporary,
  );
  const artifact = await readFile(
    join(
      temporary,
      "node_modules/@turnmark/engine/dist/generated/turnmark_wasm_bg.wasm",
    ),
  );
  assert.ok(WebAssembly.validate(artifact));
  console.log(
    "Rust engine tarball: isolated offline install, Node consumer, asset export and declarations passed",
  );
} finally {
  await rm(temporary, { recursive: true, force: true });
}
