import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import {
  androidSmoke,
  iosSmoke,
  iosTestCases,
  selectTests,
  testInventory,
  verifyCases,
} from "./native-test-support.mjs";

test("full inventories retain every native regression and smoke plans select real tests", () => {
  const ios = [
    ...testInventory("apps/ios/Tests", "ios", "TurnmarkTests"),
    ...testInventory("apps/ios/UITests", "ios", "TurnmarkUITests"),
  ];
  assert.equal(ios.length, 27);
  assert.equal(selectTests(ios, ["TurnmarkTests", ...iosSmoke]).length, 11);
  const full = JSON.parse(readFileSync("apps/ios/Full.xctestplan"));
  assert.equal(full.testTargets.length, 2);
  assert.ok(
    full.testTargets.every(
      (t) => !t.skippedTests?.length && !t.selectedTests?.length && !t.skipped,
    ),
  );
  const smoke = JSON.parse(readFileSync("apps/ios/Smoke.xctestplan"));
  assert.deepEqual(
    smoke.testTargets[1].selectedTests.map(
      (s) => `TurnmarkUITests/${s.replace(/\(\)$/, "")}`,
    ),
    iosSmoke,
  );
  const android = testInventory(
    "apps/android/src/androidTest/java/net/stanback/turnmark",
    "android",
  );
  assert.equal(android.length, 30);
  assert.equal(selectTests(android, androidSmoke).length, 4);
  const source = readFileSync(
    "apps/android/src/androidTest/java/net/stanback/turnmark/ConverterTest.kt",
    "utf8",
  );
  const annotated = [...source.matchAll(/@SmokeTest\s+@Test fun (\w+)\(/g)].map(
    (m) => `net.stanback.turnmark.ConverterTest#${m[1]}`,
  );
  assert.deepEqual(annotated.sort(), [...androidSmoke].sort());
  assert.throws(
    () => selectTests(ios, ["TurnmarkUITests/OldRenamedClass"]),
    /Unknown/,
  );
  assert.throws(
    () => selectTests(android, ["net.stanback.turnmark.ConverterTest#typo"]),
    /Unknown/,
  );
});

test("XCTest result validation rejects missing, extra, duplicate and skipped cases", () => {
  const expected = ["UITests/Entry/testTyping", "UITests/History/testSave"];
  const cases = iosTestCases({
    testNodes: [
      {
        children: expected.map((id) => ({
          nodeType: "Test Case",
          nodeIdentifierURL: `test://com.apple.xcode/App/${id}`,
          result: "Passed",
          durationInSeconds: 2,
        })),
      },
    ],
  });
  verifyCases(cases, expected);
  assert.throws(() => verifyCases(cases.slice(1), expected));
  assert.throws(() => verifyCases([...cases, cases[0]], expected));
  assert.throws(() => verifyCases([cases[0], cases[0]], expected));
  assert.throws(() =>
    verifyCases([{ ...cases[0], result: "Skipped" }, cases[1]], expected),
  );
  assert.throws(() => verifyCases([], []));
});

test("Android report validation requires the exact selection for connected and managed devices", () => {
  const directory = mkdtempSync(join(tmpdir(), "turnmark-test-results-"));
  try {
    const expected = join(directory, "expected.json");
    const cases = join(directory, "cases.json");
    writeFileSync(expected, JSON.stringify(["example.Entry#typing"]));
    for (const kind of ["connected", "managedDevice"]) {
      const reports = join(
        directory,
        "build/outputs/androidTest-results",
        kind,
        "debug",
        "phone",
      );
      mkdirSync(reports, { recursive: true });
      const xml = join(reports, "TEST-phone.xml");
      const check = () =>
        spawnSync(
          "python3",
          ["scripts/check-android-tests.py", directory, expected, cases, kind],
          { encoding: "utf8" },
        );
      assert.notEqual(check().status, 0, "no test report must fail");
      writeFileSync(
        xml,
        '<testsuite><testcase classname="example.Entry" name="typing" time="1.2"/></testsuite>',
      );
      assert.equal(check().status, 0);
      assert.equal(JSON.parse(readFileSync(cases))[0].seconds, 1.2);
      writeFileSync(join(reports, "test-result-exit-code.txt"), "1");
      assert.notEqual(
        check().status,
        0,
        "runner failure must override a passing XML case",
      );
      assert.equal(
        JSON.parse(readFileSync(cases)).length,
        1,
        "retain case timing on runner failure",
      );
      rmSync(join(reports, "test-result-exit-code.txt"));
      writeFileSync(
        expected,
        JSON.stringify(["example.Entry#typing", "example.Entry#save"]),
      );
      assert.notEqual(
        check().status,
        0,
        "a passing partial run must fail a full selection",
      );
      writeFileSync(expected, JSON.stringify(["example.Entry#typing"]));
      writeFileSync(
        xml,
        '<testsuite><testcase classname="example.Entry" name="typing"><skipped/></testcase></testsuite>',
      );
      assert.notEqual(check().status, 0);
      writeFileSync(
        xml,
        '<testsuite><testcase classname="example.Entry" name="typing"/><testcase classname="example.Entry" name="typing"/></testsuite>',
      );
      assert.notEqual(check().status, 0, "duplicate reports must fail");
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
