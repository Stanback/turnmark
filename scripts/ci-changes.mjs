import { spawnSync } from "node:child_process";
import { appendFileSync, readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const all = () => ({ web: true, core: true, ios: true, android: true });

// Dependency boundaries, not file extensions: native consumers do not depend
// on the web UI or JS adapter. Unknown paths deliberately select every check.
export function affectedChecks(paths) {
  const checks = { web: false, core: false, ios: false, android: false };
  const select = (...names) => names.forEach((name) => (checks[name] = true));
  for (const path of paths) {
    if (
      path.startsWith("docs/") ||
      path.startsWith(".github/ISSUE_TEMPLATE/") ||
      path === ".github/pull_request_template.md" ||
      /^[^/]+\.md$/.test(path) ||
      /(^|\/)README\.md$/.test(path)
    )
      continue;
    if (
      path.startsWith(".github/workflows/") ||
      path.startsWith(".github/actions/") ||
      path.startsWith("scripts/ci-") ||
      path.startsWith("crates/turnmark-core/") ||
      path.startsWith("data/") ||
      path.startsWith("fixtures/") ||
      path.startsWith(".cargo/") ||
      [
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        "scripts/build-shared.mjs",
        "scripts/test-shared.mjs",
      ].includes(path) ||
      path.startsWith("scripts/import-")
    )
      return all();
    if (path.startsWith("apps/history/")) select("ios", "android");
    else if (
      path.startsWith("apps/ios/") ||
      path.startsWith("packages/swift/") ||
      path === "bindings/tests/main.swift" ||
      ["scripts/package-ios.mjs", "scripts/test-ios.mjs"].includes(path)
    )
      select("ios");
    else if (
      path.startsWith("apps/android/") ||
      path.startsWith("packages/android/") ||
      path.startsWith("gradle/") ||
      path.startsWith("gradlew") ||
      [
        "build.gradle.kts",
        "settings.gradle.kts",
        "gradle.properties",
        "bindings/tests/Main.kt",
        "scripts/package-android.mjs",
        "scripts/test-android.mjs",
        "scripts/check-android-tests.py",
        "scripts/check-android-libraries.mjs",
      ].includes(path)
    )
      select("android");
    else if (path === "scripts/test-native-host.mjs") select("ios", "android");
    else if (
      [
        "design/turnmark.tokens.json",
        "design/generate.mjs",
        "design/wave.svg",
      ].includes(path)
    )
      select("web", "core", "ios", "android");
    else if (
      [
        "scripts/generate-brand-assets.mjs",
        "design/brand-manifest.json",
      ].includes(path)
    )
      select("web", "ios", "android");
    else if (path === "src/generated/design-tokens.css") select("web", "core");
    else if (
      path.startsWith("crates/turnmark-wasm/") ||
      path.startsWith("packages/sdk/") ||
      [
        "package.json",
        "package-lock.json",
        "scripts/build-sdk.mjs",
        "scripts/generate-sdk-data.mjs",
        "scripts/test-sdk-package.mjs",
      ].includes(path)
    )
      select("web", "core");
    else if (
      path.startsWith("packages/mcp/") ||
      path.startsWith("packages/mcp-worker/") ||
      [
        "scripts/test-mcp.mjs",
        "scripts/test-mcp-ui.mjs",
        "scripts/build-mcp-ui.mjs",
        "scripts/engine-metrics.mjs",
      ].includes(path)
    )
      select("core");
    else if (
      [
        "src/",
        "design/",
        "apps/embed/",
        "embed/",
        "mcp/",
        "public/",
        "tests/",
        "tests-production/",
      ].some((prefix) => path.startsWith(prefix)) ||
      /^(vite|vitest|svelte|playwright(?:\.production)?)\.config\./.test(
        path,
      ) ||
      /^tsconfig(?:\.[^/]+)?\.json$/.test(path) ||
      path.startsWith("deployment/") ||
      path === "wrangler.jsonc" ||
      ["index.html", "scripts/finish-build.mjs"].includes(path)
    )
      select("web");
    else return all();
  }
  return checks;
}

export function checksForEvent(eventName, event, diff) {
  if (eventName === "workflow_dispatch") return all();
  if (!["pull_request", "push"].includes(eventName)) return all();
  const base =
    eventName === "pull_request" ? event.pull_request?.base.sha : event.before;
  const head = eventName === "pull_request" ? "HEAD" : event.after;
  // New branches and unfamiliar events have no trustworthy comparison.
  if (!base || /^0+$/.test(base) || !head) return all();
  return affectedChecks(diff(base, head));
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  const event = JSON.parse(readFileSync(process.env.GITHUB_EVENT_PATH, "utf8"));
  const checks = checksForEvent(
    process.env.GITHUB_EVENT_NAME,
    event,
    (base, head) => {
      // Include both sides of renames; NUL separators preserve unusual filenames.
      const result = spawnSync(
        "git",
        ["diff", "--no-renames", "--name-only", "-z", base, head, "--"],
        { encoding: "utf8" },
      );
      if (result.error || result.status !== 0)
        throw new Error(
          "Cannot determine changed paths; refusing to skip checks",
        );
      return result.stdout.split("\0").filter(Boolean);
    },
  );
  const output = Object.entries(checks)
    .map(([name, enabled]) => `${name}=${enabled}\n`)
    .join("");
  appendFileSync(process.env.GITHUB_OUTPUT, output);
  if (process.env.GITHUB_STEP_SUMMARY) {
    appendFileSync(
      process.env.GITHUB_STEP_SUMMARY,
      `### Selected checks\n\n${Object.entries(checks)
        .map(([name, enabled]) => `- ${name}: ${enabled ? "run" : "skip"}`)
        .join("\n")}\n`,
    );
  }
  console.log(output);
}
