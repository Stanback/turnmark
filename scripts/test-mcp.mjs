import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import {
  mkdtemp,
  readFile,
  writeFile,
  copyFile,
  mkdir,
  rm,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, basename } from "node:path";
import { fileURLToPath } from "node:url";
import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import { CfWorkerJsonSchemaValidator } from "@modelcontextprotocol/server/validators/cf-worker";
import { unstable_dev } from "wrangler";
import { createEngine } from "@turnmark/sdk/node";
import { conversionHtml } from "../packages/mcp/dist/generated/ui.js";
const htmlDigest = createHash("sha256").update(conversionHtml).digest("hex");

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "turnmark-mcp-"));
const engine = await createEngine();
const tools = {
  convert: "convert_swim",
  altitude: "adjust_altitude",
  youth: "get_youth_standards",
  masters: "get_masters_target",
  points: "get_world_points",
};
const operations = {
  convert: engine.convert,
  altitude: engine.adjustAltitude,
  youth: engine.youth,
  masters: engine.masters,
  points: engine.points,
};
const fixtures = JSON.parse(
  await readFile(join(root, "fixtures/sdk-conformance.json"), "utf8"),
).cases.filter((c) => Object.hasOwn(tools, c.operation));
const validator = new CfWorkerJsonSchemaValidator();
let worker;
function command(args) {
  const r = spawnSync("npm", args, {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 4 * 1024 * 1024,
  });
  assert.equal(r.status, 0, `${r.error ?? ""}\n${r.stdout}\n${r.stderr}`);
  return r.stdout;
}
async function verify(transport, mode, label, ui = false) {
  const client = new Client(
    { name: "turnmark-test", version: "0.1.0" },
    {
      versionNegotiation: { mode },
      capabilities: ui
        ? {
            extensions: {
              "io.modelcontextprotocol/ui": {
                mimeTypes: ["text/html;profile=mcp-app"],
              },
            },
          }
        : {},
    },
  );
  const errors = [];
  client.onerror = (e) => errors.push(e);
  try {
    await client.connect(transport);
    assert.equal(client.getServerVersion().version, "0.2.1");
    const listed = (await client.listTools()).tools;
    assert.deepEqual(
      listed.map((t) => t.name).sort(),
      [...Object.values(tools), "get_sources"].sort(),
    );
    const uri = "ui://turnmark/conversion/0.2.1.html";
    assert.equal(
      listed.find((t) => t.name === "convert_swim")._meta.ui.resourceUri,
      uri,
    );
    const resources = (await client.listResources()).resources;
    assert.equal(resources.length, 1);
    assert.equal(resources[0].uri, uri);
    const resource = (await client.readResource({ uri })).contents[0];
    assert.equal(resource.mimeType, "text/html;profile=mcp-app");
    assert.match(resource.text, /Update comparison/);
    assert.equal(
      createHash("sha256").update(resource.text).digest("hex"),
      htmlDigest,
      "Packed/HTTP UI must match the browser-tested bundle",
    );
    assert.ok(Buffer.byteLength(resource.text) <= 750000);
    assert.deepEqual(resource._meta.ui.csp, {
      connectDomains: [],
      resourceDomains: [],
      frameDomains: [],
    });
    await assert.rejects(
      client.readResource({ uri: "ui://turnmark/unknown.html" }),
    );
    const schemas = new Map(
      listed.map((t) => [t.name, validator.getValidator(t.inputSchema)]),
    );
    for (const tool of listed) {
      assert.equal(tool.annotations.readOnlyHint, true);
      assert.equal(tool.annotations.openWorldHint, false);
      assert.ok(tool.outputSchema);
    }
    let semantic = 0,
      malformed = 0;
    for (const f of fixtures) {
      const name = tools[f.operation];
      const shape = schemas.get(name)(f.input).valid;
      let result, error;
      try {
        result = await client.callTool({ name, arguments: f.input });
      } catch (e) {
        error = e;
      }
      if (!shape) {
        assert.equal(f.expected.status, "invalid", f.id);
        assert.ok(
          error || result?.isError,
          `${label}: ${f.id} must fail protocol validation`,
        );
        malformed++;
      } else {
        assert.ifError(error);
        assert.ok(!result.isError, `${label}: ${f.id}`);
        assert.deepEqual(
          result.structuredContent,
          operations[f.operation](f.input),
          `${label}: ${f.id}`,
        );
        assert.deepEqual(
          JSON.parse(result.content[0].text),
          result.structuredContent,
        );
        semantic++;
      }
    }
    const source = await client.callTool({
      name: "get_sources",
      arguments: {},
    });
    assert.equal(source.structuredContent.engineVersion, engine.version);
    assert.equal(
      source.structuredContent.masters.edition,
      "usms-nationals-2026",
    );
    await assert.rejects(async () => {
      const r = await client.callTool({ name: "not_a_tool", arguments: {} });
      if (r.isError) throw new Error("unknown tool");
    });
    await assert.rejects(async () => {
      const r = await client.callTool({
        name: "get_sources",
        arguments: { path: "/private/history" },
      });
      if (r.isError) throw new Error("extra argument");
    });
    const controller = new AbortController();
    controller.abort();
    await assert.rejects(
      client.callTool(
        { name: "get_sources", arguments: {} },
        { signal: controller.signal },
      ),
    );
    // A cancelled call must not poison the next calculation.
    assert.equal(
      (await client.callTool({ name: "get_sources", arguments: {} }))
        .structuredContent.engineVersion,
      engine.version,
    );
    assert.deepEqual(errors, []);
    console.log(
      `${label}: ${semantic} SDK-equal outcomes, ${malformed} malformed requests, discovery, sources, cancellation and recovery passed.`,
    );
  } finally {
    await client.close();
  }
}
try {
  await copyFile(join(root, "LICENSE"), join(root, "packages/mcp/LICENSE"));
  const packed = [];
  for (const workspace of ["@turnmark/sdk", "@turnmark/mcp"]) {
    const [p] = JSON.parse(
      command([
        "pack",
        "--workspace",
        workspace,
        "--ignore-scripts",
        "--pack-destination",
        temporary,
        "--json",
      ]),
    );
    for (const file of [
      "LICENSE",
      "README.md",
      ...(workspace.endsWith("/mcp") ? ["THIRD_PARTY_NOTICES.txt"] : []),
      "dist/" + (workspace.endsWith("/mcp") ? "cli.js" : "node.js"),
    ])
      assert.ok(
        p.files.some((f) => f.path === file),
        file,
      );
    packed.push(join(temporary, p.filename));
  }
  await writeFile(
    join(temporary, "package.json"),
    JSON.stringify({
      name: "external-mcp-consumer",
      private: true,
      type: "module",
    }),
  );
  const installed = spawnSync(
    "npm",
    ["install", "--ignore-scripts", "--no-audit", "--no-fund", ...packed],
    { cwd: temporary, encoding: "utf8" },
  );
  assert.equal(installed.status, 0, installed.stderr);
  const guard = join(temporary, "offline.mjs");
  await writeFile(
    guard,
    "globalThis.fetch = () => { throw new Error('Unexpected runtime network request'); };\n",
  );
  const cli = join(temporary, "node_modules/@turnmark/mcp/dist/cli.js");
  for (const mode of ["legacy", { pin: "2026-07-28" }])
    for (const ui of [false, true])
      await verify(
        new StdioClientTransport({
          command: process.execPath,
          args: ["--import", guard, cli],
          cwd: temporary,
          stderr: "pipe",
        }),
        mode,
        `Packed offline stdio ${JSON.stringify(mode)} Apps=${ui}`,
        ui,
      );
  // Verify the adapter against its actual published SDK dependency as well as
  // the workspace tarball. Adapter and engine versions are independent.
  const registry = join(temporary, "registry");
  await mkdir(registry);
  await writeFile(
    join(registry, "package.json"),
    JSON.stringify({
      name: "registry-sdk-mcp-check",
      private: true,
      type: "module",
    }),
  );
  const registryInstall = spawnSync(
    "npm",
    ["install", "--ignore-scripts", "--no-audit", "--no-fund", packed[1]],
    { cwd: registry, encoding: "utf8" },
  );
  assert.equal(registryInstall.status, 0, registryInstall.stderr);
  for (const mode of ["legacy", { pin: "2026-07-28" }])
    await verify(
      new StdioClientTransport({
        command: process.execPath,
        args: [
          "--import",
          guard,
          join(registry, "node_modules/@turnmark/mcp/dist/cli.js"),
        ],
        cwd: registry,
        stderr: "pipe",
      }),
      mode,
      `Registry SDK stdio ${JSON.stringify(mode)}`,
      true,
    );
  // Missing bundled Wasm fails before accepting protocol messages, with no stdout.
  const wasm = join(
    temporary,
    "node_modules/@turnmark/sdk/dist/generated/turnmark_wasm_bg.wasm",
  );
  await rm(wasm);
  const failed = spawnSync(process.execPath, [cli], {
    cwd: temporary,
    encoding: "utf8",
    timeout: 10000,
  });
  assert.equal(failed.status, 1);
  assert.equal(failed.stdout, "");
  assert.match(failed.stderr, /could not initialize/);
  worker = await unstable_dev(join(root, "packages/mcp-worker/src/index.ts"), {
    config: join(root, "packages/mcp-worker/wrangler.jsonc"),
    local: true,
    port: 0,
    ip: "127.0.0.1",
    logLevel: "error",
    persist: false,
    experimental: {
      disableExperimentalWarning: true,
      disableDevRegistry: true,
      watch: false,
    },
  });
  const base = `http://${worker.address}:${worker.port}`;
  for (const mode of ["legacy", { pin: "2026-07-28" }])
    for (const ui of [false, true])
      await verify(
        new StreamableHTTPClientTransport(new URL(`${base}/mcp`), {
          requestInit: {
            headers: {
              "CF-Connecting-IP": `test-${JSON.stringify(mode)}-${ui}`,
            },
          },
        }),
        mode,
        `Workers HTTP ${JSON.stringify(mode)} Apps=${ui}`,
        ui,
      );
  assert.equal((await fetch(`${base}/`)).status, 200);
  assert.equal((await fetch(`${base}/missing`)).status, 404);
  assert.equal((await fetch(`${base}/mcp`)).status, 405);
  assert.equal(
    (
      await fetch(`${base}/mcp`, {
        method: "POST",
        headers: {
          Origin: "https://evil.example",
          "Content-Type": "application/json",
        },
        body: "{}",
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await fetch(`${base}/mcp`, {
        method: "POST",
        headers: { Origin: "null", "Content-Type": "application/json" },
        body: "{}",
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await fetch(`${base}/mcp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: " ".repeat(16385),
      })
    ).status,
    413,
  );
  assert.equal(
    (await fetch(`${base}/mcp`, { method: "POST", body: "{}" })).status,
    415,
  );
  // Exhaust the actual local binding rather than replacing it with a mock.
  let limited = false;
  for (let i = 0; i < 181; i++) {
    const r = await fetch(`${base}/mcp`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
      },
      body: '{"jsonrpc":"2.0","method":"notifications/initialized"}',
    });
    await r.arrayBuffer();
    if (r.status === 429) {
      assert.equal(r.headers.get("Retry-After"), "60");
      limited = true;
      break;
    }
  }
  assert.ok(limited, "Worker rate limit must be enforced");
  // The aggregate guard must also reject health probes, independent of the
  // much higher per-IP limit. Use a separate local runtime and real binding.
  await worker.stop();
  worker = undefined;
  const aggregateConfig = join(temporary, "aggregate.jsonc");
  await writeFile(
    aggregateConfig,
    (
      await readFile(join(root, "packages/mcp-worker/wrangler.jsonc"), "utf8")
    ).replace('"limit": 600', '"limit": 3'),
  );
  worker = await unstable_dev(join(root, "packages/mcp-worker/src/index.ts"), {
    config: aggregateConfig,
    local: true,
    port: 0,
    ip: "127.0.0.1",
    logLevel: "error",
    persist: false,
    envFiles: [],
    experimental: {
      disableExperimentalWarning: true,
      disableDevRegistry: true,
      watch: false,
    },
  });
  const limitedBase = `http://${worker.address}:${worker.port}`;
  for (let i = 0; i < 3; i++)
    assert.equal((await fetch(limitedBase)).status, 200);
  const busy = await fetch(limitedBase);
  assert.equal(busy.status, 429);
  assert.equal(busy.headers.get("Retry-After"), "60");
  assert.match(await busy.text(), /Service busy/);
  console.log(
    "Worker boundaries: route, method, Origin, body limit and rate limit passed.",
  );
  if (process.argv[2] === "release") {
    const destination = join(root, "release");
    await mkdir(destination, { recursive: true });
    const filename = basename(packed[1]);
    const bytes = await readFile(packed[1]);
    await copyFile(packed[1], join(destination, filename));
    await writeFile(
      join(destination, "SHA256SUMS"),
      `${createHash("sha256").update(bytes).digest("hex")}  ${filename}\n`,
    );
    console.log(`Verified release tarball: ${join(destination, filename)}`);
  }
} finally {
  await worker?.stop();
  await rm(temporary, { recursive: true, force: true });
}
