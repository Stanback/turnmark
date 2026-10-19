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
for (const [path, expected] of [
  ["src/App.svelte", flags("web")],
  ["src/app.css", flags("web")],
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
  ["crates/turnmark-wasm/src/lib.rs", flags("web", "core")],
  ["apps/ios/Sources/TurnmarkApp.swift", flags("ios")],
  ["apps/history/contract-v1.json", flags("ios", "android")],
  ["apps/history/import-cases.json", flags("ios", "android")],
  ["scripts/test-ios.mjs", flags("ios")],
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
