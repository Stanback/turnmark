import { spawnSync } from "node:child_process";
import {
  readdirSync,
  readFileSync,
  writeFileSync,
  appendFileSync,
  mkdirSync,
} from "node:fs";
import { performance } from "node:perf_hooks";

export const iosSmoke = [
  "TurnmarkUITests/ConversionUITests/testBlankArrivalEntryAndResetKeepEntryFirst",
  "TurnmarkUITests/ConversionUITests/testUnsupportedComparisonStaysUnavailable",
  "TurnmarkUITests/BenchmarkUITests/testBenchmarkPreviewScoresEstimateAndKeepsOriginal",
  "TurnmarkUITests/HistoryUITests/testTimeCanBeRecordedDirectlyFromMyTimesAndFiltered",
];
export const androidSmoke = [
  "net.stanback.turnmark.ConverterTest#blankArrivalEntryAndResetKeepEntryFirst",
  "net.stanback.turnmark.ConverterTest#benchmarkPreviewScoresEstimateAndKeepsOriginal",
  "net.stanback.turnmark.ConverterTest#actualTimeCanBeRecordedDirectlyFromMyTimes",
  "net.stanback.turnmark.ConverterTest#unsupportedComparisonStaysUnavailable",
];

// Test files deliberately contain one concrete test class each. Refuse an
// ambiguous inventory instead of silently accepting fewer tests after a split.
export function testInventory(directory, platform, target) {
  return readdirSync(directory)
    .filter((file) => file.endsWith(platform === "ios" ? ".swift" : ".kt"))
    .flatMap((file) => {
      const source = readFileSync(`${directory}/${file}`, "utf8");
      const methods = [
        ...source.matchAll(
          platform === "ios" ? /\bfunc (test\w+)\(/g : /@Test\s+fun (\w+)\(/g,
        ),
      ].map((m) => m[1]);
      if (!methods.length) return [];
      const classes = [...source.matchAll(/\bclass (\w+)/g)];
      if (classes.length !== 1)
        throw new Error(`Expected one test class in ${file}`);
      const prefix =
        platform === "ios"
          ? `${target}/${classes[0][1]}/`
          : `${source.match(/^package (\S+)/m)?.[1]}.${classes[0][1]}#`;
      return methods.map((method) => `${prefix}${method}`);
    });
}

export function selectTests(inventory, selectors) {
  if (!inventory.length || new Set(inventory).size !== inventory.length)
    throw new Error("Missing or duplicate native test inventory");
  for (const selector of selectors) {
    if (
      !inventory.some(
        (id) =>
          id === selector ||
          id.startsWith(`${selector}/`) ||
          id.startsWith(`${selector}#`),
      )
    )
      throw new Error(`Unknown native test selector: ${selector}`);
  }
  return selectors.length
    ? inventory.filter((id) =>
        selectors.some(
          (s) => id === s || id.startsWith(`${s}/`) || id.startsWith(`${s}#`),
        ),
      )
    : inventory;
}

export function iosTestCases(report) {
  const cases = [];
  function visit(node) {
    if (node.nodeType === "Test Case") {
      const id = new URL(node.nodeIdentifierURL).pathname
        .split("/")
        .slice(-3)
        .join("/");
      cases.push({
        id,
        result: node.result,
        seconds: node.durationInSeconds ?? 0,
      });
    }
    for (const child of node.children ?? []) visit(child);
  }
  for (const node of report.testNodes ?? []) visit(node);
  return cases;
}

export function verifyCases(cases, expected) {
  if (
    !expected.length ||
    cases.length !== expected.length ||
    new Set(cases.map((c) => c.id)).size !== cases.length ||
    expected.some((id) => !cases.some((c) => c.id === id)) ||
    cases.some((c) => c.result !== "Passed")
  )
    throw new Error(
      "Native results must contain exactly the selected tests, all passing (no skips)",
    );
}

export function timedRun(name, settings) {
  const started = performance.now();
  const report = { name, ...settings, steps: [], tests: [] };
  report.host = {
    platform: process.platform,
    architecture: process.arch,
    node: process.version,
    revision: process.env.GITHUB_SHA ?? "local working tree",
  };
  return {
    report,
    run(command, args, options = {}) {
      const start = performance.now();
      const result = spawnSync(command, args, { stdio: "inherit", ...options });
      report.steps.push({
        command: [command, ...args].join(" "),
        seconds: (performance.now() - start) / 1000,
        exitCode: result.status,
      });
      if (result.error) throw result.error;
      if (result.status !== 0)
        throw new Error(`${command} failed with exit code ${result.status}`);
      return result;
    },
    finish(passed) {
      report.passed = passed;
      report.wallSeconds = (performance.now() - started) / 1000;
      mkdirSync("target", { recursive: true });
      writeFileSync(
        `target/${name}-metrics.json`,
        `${JSON.stringify(report, null, 2)}\n`,
      );
      const slowest = [...report.tests]
        .sort((a, b) => b.seconds - a.seconds)
        .slice(0, 5);
      const summary = `### ${name}\n\n${passed ? "Passed" : "Failed"} · ${report.wallSeconds.toFixed(1)}s wall time · ${report.tests.length} test results\n\n${slowest.map((t) => `- ${t.id}: ${t.seconds.toFixed(2)}s`).join("\n")}\n`;
      console.log(summary);
      if (process.env.GITHUB_STEP_SUMMARY)
        appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary);
    },
  };
}
