import { spawnSync } from "node:child_process";
import { rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const inventory = spawnSync(
  "xcrun",
  ["simctl", "list", "devices", "available", "--json"],
  { encoding: "utf8" },
);
if (inventory.status !== 0) throw new Error(inventory.stderr);
const device = Object.values(JSON.parse(inventory.stdout).devices)
  .flat()
  .find((d) => d.isAvailable && d.name.startsWith("iPhone"));
if (!device) throw new Error("Install an iOS simulator in Xcode first");
await rm("target/ios-tests.xcresult", { recursive: true, force: true });
const result = spawnSync(
  "xcodebuild",
  [
    "test",
    "-scheme",
    "TurnmarkCore",
    "-destination",
    `platform=iOS Simulator,id=${device.udid}`,
    "-derivedDataPath",
    "../../target/ios-tests",
    "-resultBundlePath",
    "../../target/ios-tests.xcresult",
    "CODE_SIGNING_ALLOWED=NO",
  ],
  { cwd: "packages/swift", stdio: "inherit" },
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
