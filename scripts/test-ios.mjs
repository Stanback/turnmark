import { rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { parseArgs } from "node:util";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import {
  iosSmoke,
  iosTestCases,
  selectTests,
  testInventory,
  timedRun,
  verifyCases,
} from "./native-test-support.mjs";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    suite: { type: "string", default: "full" },
    only: { type: "string", multiple: true, default: [] },
    workers: { type: "string" },
    device: { type: "string" },
    screenshots: { type: "boolean", default: false },
  },
});
const mode = positionals[0] ?? "core";
if (positionals.length > 1 || !["core", "app"].includes(mode))
  throw new Error("Use core or app");
const application = mode === "app";
if (
  !["full", "smoke", "unit"].includes(values.suite) ||
  (!application && values.suite !== "full") ||
  (values.only.length && values.suite !== "full")
)
  throw new Error(
    "Use --suite full|smoke|unit for the app, or --only Target/Class/test with full",
  );
const workers = Number(
  values.workers ??
    (application && values.suite === "full" && !values.only.length ? 2 : 1),
);
if (![1, 2].includes(workers) || (!application && workers !== 1))
  throw new Error("Use --workers 1 or 2 (core uses 1)");
const inventory = application
  ? [
      ...testInventory("apps/ios/Tests", "ios", "TurnmarkTests"),
      ...testInventory("apps/ios/UITests", "ios", "TurnmarkUITests"),
    ]
  : testInventory(
      "packages/swift/Tests/TurnmarkCoreTests",
      "ios",
      "TurnmarkCoreTests",
    );
const selectors =
  values.suite === "unit"
    ? ["TurnmarkTests"]
    : values.suite === "smoke"
      ? ["TurnmarkTests", ...iosSmoke]
      : values.only;
const expected = selectTests(inventory, selectors);
const suffix = values.only.length
  ? "-focused"
  : values.suite === "full"
    ? ""
    : `-${values.suite}`;
const output = `${application ? "ios-app-tests" : "ios-tests"}${suffix}`;
const bundle = `target/${output}.xcresult`;
const timing = timedRun(output, {
  suite: values.suite,
  workers,
  expectedTests: expected.length,
  screenshots: values.screenshots,
  compilationCache: resolve("target/xcode-compilation-cache"),
});
let passed = false;
try {
  await rm(bundle, { recursive: true, force: true });
  if (application) {
    timing.run(process.execPath, ["design/generate-icons.mjs", "--check"]);
    timing.run(process.execPath, ["design/generate.mjs", "--check"]);
  }
  const result = timing.run(
    "xcrun",
    ["simctl", "list", "devices", "available", "--json"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
  );
  const runtime = process.env.TURNMARK_IOS_RUNTIME;
  const devices = Object.entries(JSON.parse(result.stdout).devices)
    .filter(
      ([key]) =>
        key.includes(".iOS-") &&
        (!runtime ||
          key.includes(`.iOS-${runtime.replaceAll(".", "-")}-`) ||
          key.endsWith(`.iOS-${runtime.replaceAll(".", "-")}`)),
    )
    .sort(([a], [b]) => b.localeCompare(a, undefined, { numeric: true }))
    .flatMap(([, devices]) => devices)
    .filter((d) => d.isAvailable && d.name.startsWith("iPhone"));
  const udid = values.device ?? process.env.TURNMARK_IOS_DEVICE;
  if (!udid && devices.length > 1 && process.env.GITHUB_ACTIONS !== "true") {
    throw new Error(
      "Multiple iPhone simulators are available; set --device UUID or TURNMARK_IOS_DEVICE so tests do not interrupt another workspace",
    );
  }
  // Without an explicit device, prefer a standard "iPhone N" over special form
  // factors (such as iPhone Duo's side system rail) that newer runtimes may list first.
  const device = udid
    ? devices.find((d) => d.udid === udid)
    : (devices.find((d) => /^iPhone \d+$/.test(d.name)) ?? devices[0]);
  if (!device)
    throw new Error(
      "Choose an available iPhone simulator with --device UUID / TURNMARK_IOS_DEVICE and the matching TURNMARK_IOS_RUNTIME",
    );
  timing.report.device = device;
  console.log(
    `Testing ${expected.length} cases on ${device.name} (${device.udid}), ${workers} worker(s)`,
  );
  // Boot once before XCTest connects; simulator clones have isolated app stores.
  timing.run("xcrun", ["simctl", "bootstatus", device.udid, "-b"], {
    timeout: 180_000,
  });
  const cwd = application ? "." : "packages/swift";
  const common = [
    ...(application ? ["-project", "apps/ios/Turnmark.xcodeproj"] : []),
    "-scheme",
    application ? "Turnmark" : "TurnmarkCore",
    "-destination",
    `platform=iOS Simulator,id=${device.udid}`,
    "-derivedDataPath",
    application ? "target/ios-app" : "../../target/ios-tests",
    ...(application
      ? ["-testPlan", values.suite === "smoke" ? "Smoke" : "Full"]
      : []),
    "CODE_SIGNING_ALLOWED=NO",
    "COMPILATION_CACHE_ENABLE_CACHING=YES",
    "COMPILATION_CACHE_ENABLE_DIAGNOSTIC_REMARKS=YES",
    `COMPILATION_CACHE_CAS_PATH=${timing.report.compilationCache}`,
  ];
  // Always check/build current sources once; focused re-runs reuse incremental
  // products without an unsafe 'skip build' path accepting stale binaries.
  timing.run("xcodebuild", ["build-for-testing", ...common], { cwd });
  const testing = [
    "test-without-building",
    ...common,
    "-resultBundlePath",
    application ? bundle : `../../${bundle}`,
    "-parallel-testing-enabled",
    workers === 1 ? "NO" : "YES",
    "-parallel-testing-worker-count",
    String(workers),
    "-collect-test-diagnostics",
    "never",
    "-test-timeouts-enabled",
    "YES",
    "-default-test-execution-time-allowance",
    "240",
    "-maximum-test-execution-time-allowance",
    "300",
    ...(values.suite === "unit"
      ? ["-only-testing:TurnmarkTests"]
      : values.only.map((id) => `-only-testing:${id}`)),
  ];
  timing.run("xcodebuild", testing, {
    cwd,
    env: {
      ...process.env,
      TEST_RUNNER_TURNMARK_SCREENSHOTS: values.screenshots ? "1" : "0",
    },
  });
  const cases = spawnSync(
    "xcrun",
    [
      "xcresulttool",
      "get",
      "test-results",
      "tests",
      "--path",
      bundle,
      "--compact",
    ],
    { encoding: "utf8" },
  );
  if (cases.status !== 0) throw new Error("Cannot read fresh XCTest results");
  timing.report.tests = iosTestCases(JSON.parse(cases.stdout));
  verifyCases(timing.report.tests, expected);
  passed = true;
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  if (!passed && existsSync(bundle)) {
    const cases = spawnSync(
      "xcrun",
      [
        "xcresulttool",
        "get",
        "test-results",
        "tests",
        "--path",
        bundle,
        "--compact",
      ],
      { encoding: "utf8" },
    );
    if (cases.status === 0)
      timing.report.tests = iosTestCases(JSON.parse(cases.stdout));
  }
  timing.finish(passed);
}
