import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  mkdtemp,
  writeFile,
  readFile,
  rm,
  mkdir,
  copyFile,
} from "node:fs/promises";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build, createServer } from "vite";
import { chromium } from "@playwright/test";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "turnmark-sdk-"));
const destination = process.argv[2] && resolve(process.argv[2]);
let browser;
let server;
function command(name, args, cwd = root) {
  const result = spawnSync(name, args, {
    cwd,
    encoding: "utf8",
    maxBuffer: 4 * 1024 * 1024,
  });
  assert.equal(
    result.status,
    0,
    `${name} ${args.join(" ")}\n${result.error ?? ""}\n${result.stdout}\n${result.stderr}`,
  );
  return result.stdout;
}
function subset(actual, expected, label) {
  if (
    Array.isArray(expected) ||
    expected === null ||
    typeof expected !== "object"
  ) {
    assert.deepEqual(actual, expected, label);
    return;
  }
  assert.ok(actual !== null && typeof actual === "object", label);
  for (const [key, value] of Object.entries(expected))
    subset(actual[key], value, `${label}.${key}`);
}
try {
  const [packed] = JSON.parse(
    command("npm", [
      "pack",
      "--workspace",
      "@turnmark/sdk",
      "--pack-destination",
      temporary,
      "--json",
    ]),
  );
  const files = new Set(packed.files.map((file) => file.path));
  for (const required of [
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "dist/index.js",
    "dist/index.d.ts",
    "dist/node.js",
    "dist/node.d.ts",
    "src/index.ts",
    "dist/generated/turnmark_wasm_bg.wasm",
    "dist/converter.js",
    "dist/converter.d.ts",
    "dist/standards.js",
    "dist/standards.d.ts",
    "dist/generated/converter/turnmark_wasm_bg.wasm",
  ])
    assert.ok(files.has(required), `Missing packed file: ${required}`);
  await writeFile(
    join(temporary, "package.json"),
    JSON.stringify({
      name: "turnmark-sdk-consumer",
      private: true,
      type: "module",
    }),
  );
  command(
    "npm",
    [
      "install",
      "--offline",
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      join(temporary, packed.filename),
    ],
    temporary,
  );
  const fixtures = JSON.parse(
    await readFile(join(root, "fixtures/sdk-conformance.json"), "utf8"),
  );
  await writeFile(join(temporary, "fixtures.json"), JSON.stringify(fixtures));
  await writeFile(
    join(temporary, "consumer.js"),
    `
    import { createEngine, parseTime } from '@turnmark/sdk';
    import { getYouthStandards } from '@turnmark/sdk/youth';
    import { getMastersTarget } from '@turnmark/sdk/masters';
    import { getWorldPoints } from '@turnmark/sdk/points';
    import fixtures from './fixtures.json' with { type: 'json' };
    export async function run(options) {
      const engine = await createEngine(options);
      const operations = { parse: parseTime, convert: engine.convert, altitude: engine.adjustAltitude, youth: getYouthStandards, masters: getMastersTarget, points: getWorldPoints, benchmark: engine.benchmark };
      return fixtures.cases.map((fixture) => operations[fixture.operation](fixture.input));
    }
  `,
  );
  await writeFile(
    join(temporary, "node-consumer.mjs"),
    `
    globalThis.fetch = () => { throw new Error('SDK attempted a network request'); };
    const assert = (await import('node:assert/strict')).default;
    const {readFile} = await import('node:fs/promises');
    const {createEngine, parseTime} = await import('@turnmark/sdk');
    assert.throws(() => parseTime('58.32'), /Initialize the Turnmark SDK/);
    await assert.rejects(createEngine({wasm:new Uint8Array()}));
    const { run } = await import('./consumer.js');
    const wasm = await readFile(new URL(import.meta.resolve('@turnmark/sdk/engine.wasm')));
    process.stdout.write(JSON.stringify(await run({wasm})));
  `,
  );
  const results = JSON.parse(
    command(process.execPath, ["node-consumer.mjs"], temporary),
  );
  fixtures.cases.forEach((fixture, index) =>
    subset(results[index], fixture.expected, `Node: ${fixture.id}`),
  );

  await writeFile(
    join(temporary, "modular-consumer.mjs"),
    `
    import assert from 'node:assert/strict';
    import {readFile} from 'node:fs/promises';
    import {createConverter} from '@turnmark/sdk/converter';
    import {createStandardsEngine} from '@turnmark/sdk/standards';
    import {parseTime} from '@turnmark/sdk';
    import fixtures from './fixtures.json' with {type:'json'};
    globalThis.fetch = () => {throw new Error('Unexpected network request')};
    await assert.rejects(createConverter({wasm:new Uint8Array()}));
    const lean = await readFile(new URL(import.meta.resolve('@turnmark/sdk/converter.wasm')));
    const full = await readFile(new URL(import.meta.resolve('@turnmark/sdk/standards.wasm')));
    assert.ok(lean.length < full.length * 0.65, 'Converter must omit the benchmark payload');
    const [converter, again] = await Promise.all([createConverter({wasm:lean}),createConverter({wasm:lean})]);
    assert.ok(Object.isFrozen(converter)); assert.equal(converter.version,again.version);
    assert.throws(() => parseTime('58.32'), /Initialize the Turnmark SDK/);
    await assert.rejects(createStandardsEngine({wasm:new Uint8Array()}));
    const standards = await createStandardsEngine({wasm:full});
    assert.ok(Object.isFrozen(standards));
    const operations = {parse:converter.parseTime,convert:converter.convert,altitude:converter.adjustAltitude,
      youth:standards.youth,masters:standards.masters,points:standards.points,benchmark:standards.benchmark};
    process.stdout.write(JSON.stringify(fixtures.cases.map(f => operations[f.operation](f.input))));
  `,
  );
  const modularResults = JSON.parse(
    command(process.execPath, ["modular-consumer.mjs"], temporary),
  );
  fixtures.cases.forEach((fixture, index) =>
    subset(
      modularResults[index],
      fixture.expected,
      `Modular Node: ${fixture.id}`,
    ),
  );

  // A fresh process verifies first initialization through the documented Node
  // entry, including recovery from a bad Wasm input and no fetch dependency.
  await writeFile(
    join(temporary, "automatic-node-consumer.mjs"),
    `
    globalThis.fetch = () => { throw new Error('SDK attempted a network request'); };
    const assert = (await import('node:assert/strict')).default;
    const {createEngine} = await import('@turnmark/sdk/node');
    await assert.rejects(createEngine({wasm: new Uint8Array()}));
    const engines = await Promise.all([createEngine(), createEngine()]);
    assert.equal(engines[0].version, ${JSON.stringify(JSON.parse(await readFile(join(root, "packages/sdk/package.json"), "utf8")).version)});
    assert.ok(Object.isFrozen(engines[0]));
    const {run} = await import('./consumer.js');
    process.stdout.write(JSON.stringify(await run()));
  `,
  );
  const automaticResults = JSON.parse(
    command(process.execPath, ["automatic-node-consumer.mjs"], temporary),
  );
  fixtures.cases.forEach((fixture, index) =>
    subset(
      automaticResults[index],
      fixture.expected,
      `Node automatic: ${fixture.id}`,
    ),
  );

  await writeFile(
    join(temporary, "consumer.ts"),
    `
    import { createEngine, type ConversionRequest, type Result } from '@turnmark/sdk';
    import { getYouthStandards } from '@turnmark/sdk/youth';
    import { getMastersTarget } from '@turnmark/sdk/masters';
    import { getWorldPoints } from '@turnmark/sdk/points';
    import { createEngine as createNodeEngine } from '@turnmark/sdk/node';
    import { createConverter } from '@turnmark/sdk/converter';
    import { createStandardsEngine } from '@turnmark/sdk/standards';
    const engine = await createEngine();
    const nodeEngine: typeof engine = await createNodeEngine(); void nodeEngine;
    const request: ConversionRequest = { swim: { time: '2:16.71', event: { distance: 200, stroke: 'breaststroke', course: 'LCM' } }, to: 'SCY', table: 'men' };
    const result = engine.convert(request);
    const converter = await createConverter(); converter.convert(request);
    const standards = await createStandardsEngine(); standards.points({swim:request.swim,table:'men'});
    // @ts-expect-error converter-only engines do not expose benchmarks.
    converter.points({swim:request.swim,table:'men'});
    if (result.status === 'available') { const hundredths: number = result.value.hundredths; void hundredths; }
    const unused: Result<number> = { status: 'invalid', field: 'test', reason: 'invalid-time' }; void unused;
    getYouthStandards({ event: request.swim.event, table: 'women', age: '15-16' });
    getMastersTarget({ event: request.swim.event, table: 'women', age: '18-24' });
    getWorldPoints({ swim: request.swim, table: 'men' });
    const benchmark = engine.benchmark({ swim: request.swim, table: 'men', age: '15-16', system: 'youth' });
    if (benchmark.status === 'available') { const met: boolean = benchmark.value.targets[0].met; void met; }
    // @ts-expect-error public types reject unknown benchmark systems.
    engine.benchmark({ swim: request.swim, table: 'men', age: '15-16', system: 'unknown' });
    // @ts-expect-error public types reject unknown courses.
    engine.convert({ ...request, to: 'invalid' });
    // @ts-expect-error public types reject numeric times.
    engine.convert({ ...request, swim: { ...request.swim, time: 60 } });
  `,
  );
  command(
    process.execPath,
    [
      join(root, "node_modules/typescript/bin/tsc"),
      "--noEmit",
      "--strict",
      "--skipLibCheck",
      "--module",
      "NodeNext",
      "--target",
      "ES2022",
      "consumer.ts",
    ],
    temporary,
  );

  await writeFile(
    join(temporary, "index.html"),
    '<!doctype html><html lang="en"><title>SDK consumer</title><script type="module">import { run } from "./consumer.js"; import wasmUrl from "@turnmark/sdk/engine.wasm?url"; globalThis.sdkResults = await run({wasm:wasmUrl});</script></html>',
  );
  server = await createServer({
    configFile: false,
    root: temporary,
    logLevel: "error",
    // Measure one engine fetch, not Vite dependency discovery/HMR reloads.
    optimizeDeps: { noDiscovery: true },
    server: { host: "127.0.0.1", port: 0 },
  });
  await server.listen();
  const address = server.httpServer.address();
  assert.ok(address && typeof address !== "string");
  browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", (route) => {
    if (new URL(route.request().url()).hostname === "127.0.0.1")
      return route.continue();
    errors.push(`Unexpected remote request: ${route.request().url()}`);
    return route.abort();
  });
  await page.goto(`http://127.0.0.1:${address.port}/`);
  await page.waitForFunction(() => Array.isArray(globalThis.sdkResults));
  const browserResults = await page.evaluate(() => globalThis.sdkResults);
  assert.deepEqual(errors, []);
  fixtures.cases.forEach((fixture, index) =>
    subset(browserResults[index], fixture.expected, `Browser: ${fixture.id}`),
  );

  await writeFile(
    join(temporary, "focused.html"),
    `<html lang="en"><title>Focused converter</title><script type="module">
    import {createConverter} from '@turnmark/sdk/converter';
    import wasmUrl from '@turnmark/sdk/converter.wasm?url';
    import fixtures from './fixtures.json';
    const engine = await createConverter({wasm:wasmUrl});
    const operations={parse:engine.parseTime,convert:engine.convert,altitude:engine.adjustAltitude};
    globalThis.focusedResults=fixtures.cases.filter(f=>f.operation in operations).map(f=>operations[f.operation](f.input));
  </script></html>`,
  );
  const focusedRequests = [];
  page.on("request", (request) => {
    if (
      request.resourceType() === "fetch" &&
      new URL(request.url()).pathname.endsWith(".wasm")
    )
      focusedRequests.push(request.url());
  });
  await page.goto(`http://127.0.0.1:${address.port}/focused.html`);
  await page.waitForFunction(() => Array.isArray(globalThis.focusedResults));
  const focusedResults = await page.evaluate(() => globalThis.focusedResults);
  fixtures.cases
    .filter((f) => ["parse", "convert", "altitude"].includes(f.operation))
    .forEach((fixture, index) =>
      subset(
        focusedResults[index],
        fixture.expected,
        `Focused browser: ${fixture.id}`,
      ),
    );
  assert.equal(
    focusedRequests.length,
    1,
    `Focused page must fetch one engine asset: ${JSON.stringify(focusedRequests)}`,
  );
  assert.ok(
    focusedRequests[0].includes("/converter/"),
    "Focused browser must load only converter.wasm",
  );
  const focusedBuild = await build({
    configFile: false,
    root: temporary,
    logLevel: "error",
    build: {
      write: false,
      assetsInlineLimit: 0,
      rolldownOptions: { input: join(temporary, "focused.html") },
    },
  });
  const focusedAssets = (
    Array.isArray(focusedBuild) ? focusedBuild : [focusedBuild]
  )
    .flatMap((r) => r.output)
    .filter((o) => o.type === "asset" && o.fileName.endsWith(".wasm"));
  assert.equal(
    focusedAssets.length,
    1,
    "Focused production bundle must emit one Wasm asset",
  );
  assert.equal(
    Buffer.byteLength(focusedAssets[0].source),
    (
      await readFile(
        join(
          temporary,
          "node_modules/@turnmark/sdk/dist/generated/converter/turnmark_wasm_bg.wasm",
        ),
      )
    ).length,
  );
  assert.deepEqual(errors, []);

  await writeFile(
    join(temporary, "conversion-only.js"),
    "export { convertSwim } from '@turnmark/sdk/conversion';",
  );
  const built = await build({
    configFile: false,
    root: temporary,
    logLevel: "error",
    build: {
      write: false,
      minify: true,
      lib: { entry: resolve(temporary, "conversion-only.js"), formats: ["es"] },
    },
  });
  const outputs = (Array.isArray(built) ? built : [built]).flatMap(
    (result) => result.output,
  );
  let bytes = 0;
  for (const output of outputs) {
    if (output.type !== "chunk") continue;
    bytes += Buffer.byteLength(output.code);
    for (const module of Object.keys(output.modules))
      assert.ok(
        !/\/data\/(standards|masters|points)\.json/.test(module),
        `Conversion-only import included ${module}`,
      );
  }
  console.log(
    `Packed SDK: ${fixtures.cases.length} conformance cases pass in isolated Node and browser consumers; TypeScript declarations resolve.`,
  );
  console.log(
    `Conversion-only browser bundle: ${bytes.toLocaleString()} bytes minified; tables live in the shared Wasm asset; no JavaScript calculation dependencies.`,
  );
  if (destination) {
    await mkdir(destination, { recursive: true });
    const tarball = await readFile(join(temporary, packed.filename));
    const checksum = createHash("sha256").update(tarball).digest("hex");
    await copyFile(
      join(temporary, packed.filename),
      join(destination, packed.filename),
    );
    await writeFile(
      join(destination, "SHA256SUMS"),
      `${checksum}  ${packed.filename}\n`,
    );
    console.log(
      `Verified release tarball: ${join(destination, packed.filename)}`,
    );
  }
} finally {
  await browser?.close();
  await server?.close();
  await rm(temporary, { recursive: true, force: true });
}
