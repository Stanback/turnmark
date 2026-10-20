import { rm } from "node:fs/promises";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { parseArgs } from "node:util";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import {
  androidSmoke,
  selectTests,
  testInventory,
  timedRun,
} from "./native-test-support.mjs";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    suite: { type: "string", default: "full" },
    only: { type: "string", multiple: true, default: [] },
    managed: { type: "boolean", default: false },
    serial: { type: "string" },
    screenshots: { type: "boolean", default: false },
  },
});
const mode = positionals[0] ?? "sdk";
if (positionals.length > 1 || !["sdk", "app"].includes(mode))
  throw new Error("Use sdk or app");
if (values.only.length > 1)
  throw new Error(
    "Use one --only package.Class or package.Class#method selector per Android run",
  );
if (
  !["full", "smoke"].includes(values.suite) ||
  (mode === "sdk" && values.suite !== "full") ||
  (values.only.length && values.suite !== "full") ||
  (values.managed && values.serial)
)
  throw new Error(
    "Use --suite full|smoke for the app, or --only package.Class#method with full; --serial applies to connected devices only",
  );
const moduleName = mode === "app" ? "app-android" : "sdk-android";
const directory = mode === "app" ? "apps/android" : "packages/android";
const testDirectory = `${directory}/src/androidTest/java/${mode === "app" ? "net/stanback/turnmark" : "org/turnmark/sdk"}`;
const expected = selectTests(
  testInventory(testDirectory, "android"),
  values.suite === "smoke" ? androidSmoke : values.only,
);
const suffix = values.only.length
  ? "-focused"
  : values.suite === "full"
    ? ""
    : "-smoke";
const output = `android-${mode}-tests${suffix}`;
const resultKind = values.managed ? "managedDevice" : "connected";
const timing = timedRun(output, {
  suite: values.suite,
  device: values.managed
    ? "turnmarkPhone: Pixel 2 / API 37 / Google APIs / 4 KB"
    : (values.serial ??
      process.env.ANDROID_SERIAL ??
      "single connected device"),
  expectedTests: expected.length,
  screenshots: values.screenshots,
});
const expectedPath = `target/${output}-expected.json`;
const casesPath = `target/${output}-cases.json`;
mkdirSync("target", { recursive: true });
writeFileSync(expectedPath, JSON.stringify(expected));
let passed = false;
try {
  await rm(`${directory}/build/outputs/androidTest-results/${resultKind}`, {
    recursive: true,
    force: true,
  });
  await rm(casesPath, { force: true });
  if (mode === "app") {
    timing.run(process.execPath, ["design/generate-icons.mjs", "--check"]);
    timing.run(process.execPath, ["design/generate.mjs", "--check"]);
  }
  if (!values.managed) {
    const adb = process.env.ANDROID_HOME
      ? `${process.env.ANDROID_HOME}/platform-tools/adb`
      : "adb";
    const inventory = timing.run(adb, ["devices"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "inherit"],
    });
    const devices = inventory.stdout
      .split("\n")
      .filter((line) => /\tdevice\s*$/.test(line))
      .map((line) => line.split("\t")[0]);
    const serial =
      values.serial ??
      process.env.ANDROID_SERIAL ??
      (devices.length === 1 ? devices[0] : undefined);
    if (!serial || !devices.includes(serial))
      throw new Error(
        "Choose one online Android device with --serial or ANDROID_SERIAL, or use --managed",
      );
    const ready = timing.run(
      adb,
      ["-s", serial, "shell", "getprop", "sys.boot_completed"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
    );
    if (ready.stdout.trim() !== "1")
      throw new Error("The selected Android device must finish booting first");
    values.serial = serial;
    timing.report.device = serial;
  }
  // A fresh execution is required; Gradle may otherwise restore a cached GMD
  // result. Keep compilation incremental, force only the device-test task.
  const selectors = values.suite === "smoke" ? androidSmoke : values.only;
  const args = [
    `:${moduleName}:${values.managed ? "turnmarkPhone" : "connected"}DebugAndroidTest`,
    "--rerun",
    ...(values.managed
      ? [
          "-Pandroid.testoptions.manageddevices.emulator.gpu=swiftshader_indirect",
        ]
      : []),
    ...(values.suite === "smoke"
      ? [
          "-Pandroid.testInstrumentationRunnerArguments.annotation=net.stanback.turnmark.SmokeTest",
        ]
      : selectors.length
        ? [`-Pandroid.testInstrumentationRunnerArguments.class=${selectors[0]}`]
        : []),
    ...(values.screenshots
      ? [
          "-Pandroid.testInstrumentationRunnerArguments.turnmarkScreenshots=true",
        ]
      : []),
  ];
  timing.run("./gradlew", args, {
    env: {
      ...process.env,
      ...(values.serial ? { ANDROID_SERIAL: values.serial } : {}),
    },
  });
  timing.run("python3", [
    "scripts/check-android-tests.py",
    directory,
    expectedPath,
    casesPath,
    resultKind,
  ]);
  timing.report.tests = JSON.parse(readFileSync(casesPath, "utf8"));
  passed = true;
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  if (!passed)
    spawnSync(
      "python3",
      [
        "scripts/check-android-tests.py",
        directory,
        expectedPath,
        casesPath,
        resultKind,
      ],
      { stdio: "inherit" },
    );
  if (existsSync(casesPath))
    timing.report.tests = JSON.parse(readFileSync(casesPath, "utf8"));
  timing.finish(passed);
}
