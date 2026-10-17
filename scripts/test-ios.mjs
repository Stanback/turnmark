import { spawnSync } from "node:child_process";
import { rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const mode = process.argv[2] ?? "core";
if (!["core", "app"].includes(mode)) throw new Error("Use core or app");
const application = mode === "app";
const output = application ? "ios-app-tests" : "ios-tests";
const inventory = spawnSync(
  "xcrun",
  ["simctl", "list", "devices", "available", "--json"],
  { encoding: "utf8" },
);
if (inventory.status !== 0) throw new Error(inventory.stderr);
const requiredRuntime = process.env.TURNMARK_IOS_RUNTIME;
const runtimes = Object.entries(JSON.parse(inventory.stdout).devices)
  .filter(
    ([key]) =>
      key.includes(".iOS-") &&
      (!requiredRuntime ||
        key.includes(`.iOS-${requiredRuntime.replaceAll(".", "-")}-`) ||
        key.endsWith(`.iOS-${requiredRuntime.replaceAll(".", "-")}`)),
  )
  .sort(([a], [b]) => b.localeCompare(a, undefined, { numeric: true }));
const device = runtimes
  .flatMap(([, devices]) => devices)
  .find((d) => d.isAvailable && d.name.startsWith("iPhone"));
if (!device)
  throw new Error(
    `Install an iOS ${requiredRuntime ?? ""} simulator in Xcode first`,
  );
console.log(`Testing on ${device.name} (${device.udid})`);
await rm(`target/${output}.xcresult`, { recursive: true, force: true });
const result = spawnSync(
  "xcodebuild",
  [
    "test",
    ...(application ? ["-project", "apps/ios/Turnmark.xcodeproj"] : []),
    "-scheme",
    application ? "Turnmark" : "TurnmarkCore",
    "-destination",
    `platform=iOS Simulator,id=${device.udid}`,
    "-derivedDataPath",
    application ? "target/ios-app" : "../../target/ios-tests",
    "-resultBundlePath",
    application
      ? `target/${output}.xcresult`
      : `../../target/${output}.xcresult`,
    "CODE_SIGNING_ALLOWED=NO",
  ],
  { cwd: application ? "." : "packages/swift", stdio: "inherit" },
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
