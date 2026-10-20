import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { affectedChecks, checksForEvent } from "./ci-changes.mjs";

const flags = (...selected) =>
  Object.fromEntries(
    ["web", "core", "ios", "android"].map((name) => [
      name,
      selected.includes(name),
    ]),
  );
const all = flags("web", "core", "ios", "android");

const engineWorkflow = readFileSync(
  new URL("../.github/workflows/shared-engine.yml", import.meta.url),
  "utf8",
);
const engineJob = (name) =>
  engineWorkflow.split(`\n  ${name}:\n`)[1].split(/\n  [\w-]+:\n/)[0];

test("consumer jobs depend on the fast core gate, not the browser suite", () => {
  for (const job of ["core-and-web", "mcp", "ios", "android"]) {
    assert.match(engineJob(job), /needs: \[changes, core\]/);
  }
  assert.match(engineJob("core"), /cargo test --locked --workspace/);
  assert.doesNotMatch(engineJob("core"), /playwright|test-ios|test-android/);
  assert.match(
    engineJob("engine-ci"),
    /needs: \[changes, core, core-and-web, ios, android, mcp\]/,
  );
});

test("native dependency conditions allow intentional core skips and block broken shared checks", () => {
  for (const platform of ["ios", "android"]) {
    // This workflow expression uses the shared JS/GitHub boolean subset.
    // Exercise the actual condition, including its explicit status check.
    const expression = engineJob(platform).match(/if: \$\{\{ (.*?) \}\}/)[1];
    const evaluate = new Function(
      "needs",
      "cancelled",
      `return (${expression})`,
    );
    const needs = (coreSelected, coreResult, selected = "true") => ({
      changes: {
        result: "success",
        outputs: { core: coreSelected, [platform]: selected },
      },
      core: { result: coreResult },
    });
    assert.equal(
      evaluate(needs("true", "success"), () => false),
      true,
    );
    assert.equal(
      evaluate(needs("false", "skipped"), () => false),
      true,
    );
    for (const result of ["failure", "cancelled", "skipped"]) {
      assert.equal(
        evaluate(needs("true", result), () => false),
        false,
      );
    }
    assert.equal(
      evaluate(needs("true", "success", "false"), () => false),
      false,
    );
    assert.equal(
      evaluate(needs("true", "success"), () => true),
      false,
    );
    const brokenSelection = needs("false", "skipped");
    brokenSelection.changes.result = "failure";
    assert.equal(
      evaluate(brokenSelection, () => false),
      false,
    );
  }
});

test("engine summary rejects unexpected skips, missing results and failed selected jobs", () => {
  const script = engineJob("engine-ci")
    .split("node --input-type=module <<'JS'\n")[1]
    .split("\n          JS")[0];
  const run = new Function("process", script);
  const gate = (jobs) => {
    let code = 0;
    run({
      env: { RESULTS: JSON.stringify(jobs) },
      exit: (value) => (code = value),
    });
    return code;
  };
  for (const core of ["true", "false"]) {
    for (const ios of ["true", "false"]) {
      for (const android of ["true", "false"]) {
        const selected = { core, ios, android };
        const jobs = {
          changes: { result: "success", outputs: selected },
          ...Object.fromEntries(
            Object.entries({
              core,
              "core-and-web": core,
              mcp: core,
              ios,
              android,
            }).map(([job, enabled]) => [
              job,
              { result: enabled === "true" ? "success" : "skipped" },
            ]),
          ),
        };
        assert.equal(gate(jobs), 0);
        for (const job of ["core", "core-and-web", "mcp", "ios", "android"]) {
          const changed = structuredClone(jobs);
          changed[job].result =
            jobs[job].result === "success" ? "skipped" : "success";
          assert.equal(gate(changed), 1, `${job}: unexpected skip/run`);
          for (const result of ["failure", "cancelled", undefined]) {
            changed[job].result = result;
            assert.equal(gate(changed), 1, `${job}: ${result}`);
          }
        }
        jobs.changes.result = "failure";
        assert.equal(gate(jobs), 1);
      }
    }
  }
});

function mcpLiveVerifier({ staleLists = 0, wrongPreview = false } = {}) {
  const workflow = readFileSync(
    new URL("../.github/workflows/shared-engine.yml", import.meta.url),
    "utf8",
  );
  const step = workflow
    .split("      - name: Verify service, conversion and Apps resource\n")[1]
    .split("  engine-ci:\n")[0];
  const script = step
    .split("node --input-type=module <<'JS'\n")[1]
    .split("\n          JS")[0]
    .replace(/^          /gm, "")
    .replace(/^import .*;\n/gm, "");
  const run = new Function(
    "assert",
    "readFileSync",
    "fetch",
    "setTimeout",
    "console",
    `return (async () => {${script}})()`,
  );
  const uri = "ui://turnmark/conversion/0.3.0-r6.html";
  const names = [
    "adjust_altitude",
    "assess_swim_benchmark",
    "convert_swim",
    "get_masters_target",
    "get_sources",
    "get_world_points",
    "get_youth_standards",
  ];
  const calls = [];
  const waits = [];
  let lists = 0;
  const fetch = async (url, request) => {
    assert.equal(url, "https://mcp.turnmark.app/mcp");
    assert.equal(request.method, "POST");
    const { method, params } = JSON.parse(request.body);
    calls.push({ method, params });
    let result;
    if (method === "tools/list") {
      lists++;
      result = {
        tools: names.map((name) => ({
          name,
          inputSchema: { properties: { preview: { type: "object" } } },
          _meta: {
            ui: {
              resourceUri: lists <= staleLists ? uri.replace("r6", "r5") : uri,
            },
          },
        })),
      };
    } else if (method === "resources/read") {
      assert.equal(params.uri, uri);
      result = {
        contents: [
          {
            mimeType: "text/html;profile=mcp-app",
            text: "<button>Update comparison</button>",
            _meta: {
              ui: {
                csp: {
                  connectDomains: [],
                  resourceDomains: [],
                  frameDomains: [],
                },
              },
            },
          },
        ],
      };
    } else {
      assert.equal(method, "tools/call");
      const { swim } = params.arguments;
      result = {
        structuredContent:
          params.name === "convert_swim"
            ? { value: { time: "1:06.72" } }
            : {
                status: "available",
                assessmentContext: {
                  basis: wrongPreview ? "entered-swim" : "converted-estimate",
                  originalSwim: swim,
                  assessedSwim: {
                    time: "1:06.72",
                    event: { ...swim.event, course: "LCM" },
                  },
                },
              },
      };
    }
    // Exercise the real deploy verifier's Streamable HTTP/SSE decoding too.
    return new Response(
      "event: message\ndata: " +
        JSON.stringify({ jsonrpc: "2.0", id: 2, result }) +
        "\n\n",
    );
  };
  return {
    calls,
    waits,
    run: () =>
      run(
        assert,
        (path) => {
          assert.equal(path, "packages/mcp/src/server.ts");
          return `export const conversionResourceUri = "${uri}";`;
        },
        fetch,
        (resolve, delay) => {
          waits.push(delay);
          resolve();
        },
        { warn() {}, log() {} },
      ),
  };
}

test("MCP live verification waits for the current resource, then checks previews", async () => {
  const verifier = mcpLiveVerifier({ staleLists: 2 });
  await verifier.run();
  assert.deepEqual(verifier.waits, [5000, 5000]);
  assert.equal(
    verifier.calls.filter((c) => c.method === "tools/list").length,
    3,
  );
  assert.deepEqual(
    verifier.calls
      .filter((c) => c.method === "tools/call")
      .map((c) => c.params.name),
    ["convert_swim", "get_world_points", "assess_swim_benchmark"],
  );
});

test("MCP live verification fails after a bounded stale rollout", async () => {
  const verifier = mcpLiveVerifier({ staleLists: Infinity });
  await assert.rejects(verifier.run(), /strictly equal/);
  assert.equal(verifier.calls.length, 12);
  assert.equal(verifier.waits.length, 11);
});

test("MCP live verification rejects entered-swim fallback for a requested preview", async () => {
  const verifier = mcpLiveVerifier({ wrongPreview: true });
  await assert.rejects(verifier.run(), /strictly equal/);
  assert.equal(verifier.waits.length, 11);
  assert.equal(
    verifier.calls.filter(
      (c) => c.method === "tools/call" && c.params.name === "get_world_points",
    ).length,
    12,
  );
});

test("MCP deploy requires passing checks but permits skipped native ancestors", () => {
  const workflow = readFileSync(
    new URL("../.github/workflows/shared-engine.yml", import.meta.url),
    "utf8",
  );
  const job = workflow.split("  mcp-deploy:\n")[1].split("  engine-ci:\n")[0];
  const expression = job.match(/    if: \$\{\{ (.+) \}\}/)?.[1];
  assert.ok(expression, "Use an explicit deploy status expression");
  // GitHub adds success() implicitly unless a status function is present.
  assert.match(expression, /\b(?:cancelled|always|success|failure)\(/);
  const evaluate = new Function(
    "github",
    "needs",
    "cancelled",
    `return (${expression.replaceAll("needs.engine-ci", 'needs["engine-ci"]')});`,
  );
  const github = { ref: "refs/heads/main", event_name: "push" };
  const needs = {
    mcp: { result: "success" },
    "engine-ci": { result: "success" },
    ios: { result: "skipped" },
    android: { result: "skipped" },
  };
  assert.equal(
    evaluate(github, needs, () => false),
    true,
  );
  assert.equal(
    evaluate(github, needs, () => true),
    false,
  );
  assert.equal(
    evaluate({ ...github, event_name: "pull_request" }, needs, () => false),
    false,
  );
  assert.equal(
    evaluate({ ...github, ref: "refs/heads/feature" }, needs, () => false),
    false,
  );
  for (const name of ["mcp", "engine-ci"])
    for (const result of ["failure", "cancelled", "skipped"])
      assert.equal(
        evaluate(github, { ...needs, [name]: { result } }, () => false),
        false,
      );
});
for (const [path, expected] of [
  ["src/App.svelte", flags("web")],
  ["src/app.css", flags("web")],
  ["scripts/generate-social-image.mjs", flags("web")],
  ["design/turnmark.tokens.json", all],
  ["design/wave.svg", all],
  ["design/swim-icons.json", all],
  ["design/generate-icons.mjs", all],
  ["design/brand-manifest.json", flags("web", "ios", "android")],
  ["design/generate.mjs", all],
  ["apps/embed/Widget.svelte", flags("web")],
  ["embed/v1/index.html", flags("web")],
  ["mcp/index.html", flags("web")],
  ["public/icons/app-icon.svg", flags("web")],
  ["tests-production/app.spec.ts", flags("web")],
  ["playwright.production.config.ts", flags("web")],
  ["wrangler.jsonc", flags("web")],
  ["deployment/package-lock.json", flags("web")],
  ["deployment/package.json", flags("web")],
  ["packages/sdk/src/core.ts", flags("web", "core")],
  ["package-lock.json", flags("web", "core")],
  ["packages/mcp/src/server.ts", flags("core")],
  ["packages/mcp-worker/wrangler.jsonc", flags("core")],
  ["scripts/test-mcp.mjs", flags("core")],
  ["scripts/test-mcp-ui.mjs", flags("core")],
  ["scripts/build-mcp-ui.mjs", flags("core")],
  ["packages/mcp/ui/app.ts", flags("core")],
  ["packages/mcp/ui/app.css", flags("core")],
  ["packages/mcp/test/host.ts", flags("core")],
  ["src/generated/design-tokens.css", flags("web", "core")],
  ["src/lib/elevation-display.ts", flags("web", "core")],
  ["src/lib/calculation-copy.ts", flags("web", "core")],
  ["crates/turnmark-wasm/src/lib.rs", flags("web", "core")],
  ["apps/ios/Sources/TurnmarkApp.swift", flags("ios")],
  ["apps/history/contract-v1.json", flags("ios", "android")],
  ["apps/history/import-cases.json", flags("ios", "android")],
  ["scripts/test-ios.mjs", flags("ios")],
  ["scripts/native-test-support.mjs", flags("ios", "android")],
  ["scripts/native-test-support.test.mjs", flags("ios", "android")],
  ["packages/swift/Package.swift", flags("ios")],
  [
    "apps/android/src/main/java/net/stanback/turnmark/MainActivity.kt",
    flags("android"),
  ],
  ["settings.gradle.kts", flags("android")],
  ["gradle/wrapper/gradle-wrapper.jar", flags("android")],
  ["scripts/check-android-tests.py", flags("android")],
  ["crates/turnmark-core/src/engine.rs", all],
  ["data/conversions.json", all],
  ["fixtures/sdk-conformance.json", all],
  ["Cargo.lock", all],
  ["rust-toolchain.toml", all],
  ["scripts/build-shared.mjs", all],
  ["scripts/ci-changes.mjs", all],
  [".github/workflows/website.yml", all],
  ["future-package/calculations.rs", all],
  ["docs/NATIVE_APPS.md", flags()],
  ["AGENTS.md", flags()],
  ["CLAUDE.md", flags()],
  ["packages/sdk/README.md", flags()],
  [".github/ISSUE_TEMPLATE/bug_report.yml", flags()],
])
  test(path, () => assert.deepEqual(affectedChecks([path]), expected));

test("mixed changes accumulate across platform boundaries", () => {
  assert.deepEqual(
    affectedChecks(["apps/ios/Info.plist", "src/App.svelte"]),
    flags("web", "ios"),
  );
});
test("rename out of a shared directory still selects its old consumers", () => {
  assert.deepEqual(
    affectedChecks(["data/conversions.json", "docs/conversions.json"]),
    all,
  );
});
test("full git diff has no 300-file filtering limit", () => {
  assert.deepEqual(
    affectedChecks([
      ...Array(400).fill("docs/example.md"),
      "data/sources.json",
    ]),
    all,
  );
});
test("manual runs and new branches run every platform", () => {
  const noDiff = () => assert.fail("should not diff");
  assert.deepEqual(checksForEvent("workflow_dispatch", {}, noDiff), all);
  assert.deepEqual(
    checksForEvent("push", { before: "0".repeat(40), after: "abc" }, noDiff),
    all,
  );
});
test("PRs compare the base against the tested merge checkout", () => {
  assert.deepEqual(
    checksForEvent(
      "pull_request",
      { pull_request: { base: { sha: "base" } } },
      (base, head) => {
        assert.equal(base, "base");
        assert.equal(head, "HEAD");
        return ["src/App.svelte"];
      },
    ),
    flags("web"),
  );
});
test("pushes compare the entire pushed range", () => {
  assert.deepEqual(
    checksForEvent(
      "push",
      { before: "before", after: "after" },
      (base, head) => {
        assert.equal(base, "before");
        assert.equal(head, "after");
        return ["apps/ios/Info.plist"];
      },
    ),
    flags("ios"),
  );
});

test("CLI uses real Git history, preserves deleted paths and fails on missing refs", (t) => {
  const repo = mkdtempSync(join(tmpdir(), "turnmark-ci-"));
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  const git = (...args) => {
    const result = spawnSync("git", args, { cwd: repo, encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  const commit = () => {
    git("add", "--all");
    git(
      "-c",
      "user.name=CI test",
      "-c",
      "user.email=ci@example.invalid",
      "commit",
      "-m",
      "fixture",
    );
    return git("rev-parse", "HEAD");
  };
  const run = (event) => {
    const eventPath = join(repo, ".git", "ci-event.json");
    const outputPath = join(repo, ".git", "ci-output.txt");
    writeFileSync(eventPath, JSON.stringify(event));
    writeFileSync(outputPath, "");
    const result = spawnSync(
      process.execPath,
      [fileURLToPath(new URL("./ci-changes.mjs", import.meta.url))],
      {
        cwd: repo,
        encoding: "utf8",
        env: {
          ...process.env,
          GITHUB_EVENT_NAME: "push",
          GITHUB_EVENT_PATH: eventPath,
          GITHUB_OUTPUT: outputPath,
          GITHUB_STEP_SUMMARY: "",
        },
      },
    );
    return { result, output: readFileSync(outputPath, "utf8") };
  };
  git("init");
  mkdirSync(join(repo, "data"));
  mkdirSync(join(repo, "src"));
  writeFileSync(join(repo, "data", "tables.json"), "{}");
  writeFileSync(join(repo, "src", "unusual\nname.svelte"), "before");
  const base = commit();
  writeFileSync(join(repo, "src", "unusual\nname.svelte"), "after");
  const web = commit();
  let checked = run({ before: base, after: web });
  assert.equal(checked.result.status, 0, checked.result.stderr);
  assert.equal(
    checked.output,
    "web=true\ncore=false\nios=false\nandroid=false\n",
  );
  mkdirSync(join(repo, "docs"));
  renameSync(
    join(repo, "data", "tables.json"),
    join(repo, "docs", "tables.json"),
  );
  const moved = commit();
  checked = run({ before: web, after: moved });
  assert.equal(checked.result.status, 0, checked.result.stderr);
  assert.equal(checked.output, "web=true\ncore=true\nios=true\nandroid=true\n");
  checked = run({ before: "missing-commit", after: moved });
  assert.notEqual(checked.result.status, 0);
  assert.equal(checked.output, "");
});
