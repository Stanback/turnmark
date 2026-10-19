import { spawnSync } from "node:child_process";
import { rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const mode = process.argv[2] ?? "sdk";
if (!["sdk", "app"].includes(mode)) throw new Error("Use sdk or app");
if (mode === "app") {
  const icons = spawnSync(
    process.execPath,
    ["design/generate-icons.mjs", "--check"],
    { stdio: "inherit" },
  );
  if (icons.error) throw icons.error;
  if (icons.status !== 0) process.exit(icons.status ?? 1);
  const tokens = spawnSync(
    process.execPath,
    ["design/generate.mjs", "--check"],
    { stdio: "inherit" },
  );
  if (tokens.error) throw tokens.error;
  if (tokens.status !== 0) process.exit(tokens.status ?? 1);
}
const moduleName = mode === "app" ? "app-android" : "sdk-android";
const directory = mode === "app" ? "apps/android" : "packages/android";
function run(command, args) {
  const result = spawnSync(command, args, { stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
// AGP may exit successfully after an instrumentation-runner installation error.
// Delete stale results and require a fresh, passing report with real test cases.
await rm(`${directory}/build/outputs/androidTest-results`, {
  recursive: true,
  force: true,
});
run("./gradlew", [`:${moduleName}:connectedDebugAndroidTest`]);
run("python3", ["scripts/check-android-tests.py", directory]);
