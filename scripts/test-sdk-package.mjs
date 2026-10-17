import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build, createServer } from "vite";
import { chromium } from "@playwright/test";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "turnmark-sdk-"));
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
    "dist/index.js",
    "dist/index.d.ts",
    "src/index.ts",
    "dist/data/standards.json",
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
    export async function run() {
      const engine = await createEngine();
      const operations = { parse: parseTime, convert: engine.convert, altitude: engine.adjustAltitude, youth: getYouthStandards, masters: getMastersTarget, points: getWorldPoints };
      return fixtures.cases.map((fixture) => operations[fixture.operation](fixture.input));
    }
  `,
  );
  await writeFile(
    join(temporary, "node-consumer.mjs"),
    `
    globalThis.fetch = () => { throw new Error('SDK attempted a network request'); };
    const { run } = await import('./consumer.js');
    process.stdout.write(JSON.stringify(await run()));
  `,
  );
  const results = JSON.parse(
    command(process.execPath, ["node-consumer.mjs"], temporary),
  );
  fixtures.cases.forEach((fixture, index) =>
    subset(results[index], fixture.expected, `Node: ${fixture.id}`),
  );

  await writeFile(
    join(temporary, "consumer.ts"),
    `
    import { createEngine, type ConversionRequest, type Result } from '@turnmark/sdk';
    import { getYouthStandards } from '@turnmark/sdk/youth';
    import { getMastersTarget } from '@turnmark/sdk/masters';
    import { getWorldPoints } from '@turnmark/sdk/points';
    const engine = await createEngine();
    const request: ConversionRequest = { swim: { time: '2:16.71', event: { distance: 200, stroke: 'breaststroke', course: 'LCM' } }, to: 'SCY', table: 'men' };
    const result = engine.convert(request);
    if (result.status === 'available') { const hundredths: number = result.value.hundredths; void hundredths; }
    const unused: Result<number> = { status: 'invalid', field: 'test', reason: 'invalid-time' }; void unused;
    getYouthStandards({ event: request.swim.event, table: 'women', age: '15-16' });
    getMastersTarget({ event: request.swim.event, table: 'women', age: '18-24' });
    getWorldPoints({ swim: request.swim, table: 'men' });
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
    '<!doctype html><html lang="en"><title>SDK consumer</title><script type="module">import { run } from "./consumer.js"; globalThis.sdkResults = await run();</script></html>',
  );
  server = await createServer({
    configFile: false,
    root: temporary,
    logLevel: "error",
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
    `Conversion-only browser bundle: ${bytes.toLocaleString()} bytes minified; no benchmark/points tables or runtime dependencies.`,
  );
} finally {
  await browser?.close();
  await server?.close();
  await rm(temporary, { recursive: true, force: true });
}
