import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseTime } from "../packages/sdk/dist/time.js";
import {
  convertSwim,
  adjustAltitude,
} from "../packages/sdk/dist/conversion.js";
import { getYouthStandards } from "../packages/sdk/dist/youth.js";
import { getMastersTarget } from "../packages/sdk/dist/masters.js";
import { getWorldPoints } from "../packages/sdk/dist/points.js";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const mode = process.argv[2] ?? "wasm";
const read = async (path) => JSON.parse(await readFile(path, "utf8"));
const cases = (await read("fixtures/sdk-conformance.json")).cases;
const implementations = {
  parse: parseTime,
  convert: convertSwim,
  altitude: adjustAltitude,
  youth: getYouthStandards,
  masters: getMastersTarget,
  points: getWorldPoints,
};
const strokes = {
  FR: "freestyle",
  BK: "backstroke",
  BR: "breaststroke",
  FL: "butterfly",
  IM: "individual-medley",
};
let count = 0;
function add(operation, input) {
  cases.push({
    id: `differential-${++count}`,
    operation,
    input,
    expected: implementations[operation](input),
  });
}
function event(row) {
  return {
    distance: row.distance,
    stroke: strokes[row.stroke],
    course: row.course,
  };
}
for (const row of (await read("data/standards.json")).records)
  add("youth", { event: event(row), table: row.category, age: row.age });
const masters = await read("data/masters.json");
for (const row of masters.records)
  for (const age of masters.ages)
    add("masters", { event: event(row), table: row.category, age });
for (const row of (await read("data/points.json")).events) {
  for (const table of ["women", "men"])
    for (const time of [row[table].toFixed(2), "0.01", "59.99", "60:00"]) {
      add("points", { swim: { event: event(row), time }, table });
    }
}
for (const course of ["SCY", "SCM", "LCM"])
  for (const stroke of Object.values(strokes)) {
    const distances =
      stroke === "freestyle"
        ? [
            50,
            100,
            200,
            ...(course === "SCY" ? [500, 1000, 1650] : [400, 800, 1500]),
          ]
        : stroke === "individual-medley"
          ? [100, 200, 400]
          : [50, 100, 200];
    for (const distance of distances)
      for (const table of ["women", "men"])
        for (const time of ["0.01", "1:02.45", "2:16.71", "60:00"]) {
          const swim = { time, event: { course, stroke, distance } };
          for (const to of ["SCY", "SCM", "LCM"])
            add("convert", { swim, to, table });
          for (const value of [2999, 3000, 4250, 4251, 6500, 6501, 20000])
            add("altitude", { swim, elevation: { value, unit: "feet" } });
        }
  }
// All existing JS outputs are an independent migration oracle. Remove the TS
// implementation once the web app switches to the generated WASM library.
function subset(actual, expected, path) {
  if (typeof expected === "number") {
    assert.equal(typeof actual, "number", path);
    assert.ok(
      Math.abs(actual - expected) < 1e-9,
      `${path}: ${actual} != ${expected}`,
    );
  } else if (Array.isArray(expected)) {
    assert.ok(Array.isArray(actual), path);
    assert.equal(actual.length, expected.length, path);
    expected.forEach((value, i) => subset(actual[i], value, `${path}[${i}]`));
  } else if (expected !== null && typeof expected === "object") {
    for (const [key, value] of Object.entries(expected))
      subset(actual?.[key], value, `${path}.${key}`);
  } else assert.equal(actual, expected, path);
}
function verify(results, runtime) {
  assert.equal(results.length, cases.length, `${runtime} result count`);
  results.forEach((result, i) =>
    subset(result, cases[i].expected, `${runtime}:${cases[i].id}`),
  );
  console.log(
    `${runtime}: ${cases.length} conformance and differential cases passed`,
  );
}
await mkdir("target/conformance", { recursive: true });
await writeFile("target/conformance/cases.json", JSON.stringify(cases));
if (mode === "wasm") {
  const { createEngine } = await import("../packages/engine/dist/index.js");
  const { evaluate } =
    await import("../packages/engine/dist/generated/turnmark_wasm.js");
  const engine = await createEngine({
    wasm: await readFile(
      "packages/engine/dist/generated/turnmark_wasm_bg.wasm",
    ),
  });
  const methods = {
    parse: "parseTime",
    convert: "convert",
    altitude: "adjustAltitude",
    youth: "youth",
    masters: "masters",
    points: "points",
  };
  verify(
    cases.map(({ operation, input }) => engine[methods[operation]](input)),
    "WebAssembly/Node",
  );
  assert.equal(engine.parseTime(1n), null);
  assert.equal(engine.parseTime(Symbol("not a clock")), null);
  assert.throws(() => evaluate("convert", "{"), /Malformed JSON/);
  // Exercise the browser's real fetch/instantiate path too.
  const { createServer } = await import("node:http");
  const server = createServer(async (req, res) => {
    try {
      const name =
        req.url === "/cases.json"
          ? "target/conformance/cases.json"
          : req.url === "/"
            ? null
            : `packages/engine/dist/${req.url.slice(1)}`;
      if (name === null) {
        res.setHeader("Content-Type", "text/html");
        res.end("<!doctype html><title>Turnmark WASM conformance</title>");
        return;
      }
      if (
        ![
          "target/conformance/cases.json",
          "packages/engine/dist/index.js",
          "packages/engine/dist/generated/turnmark_wasm.js",
          "packages/engine/dist/generated/turnmark_wasm_bg.wasm",
        ].includes(name)
      ) {
        res.writeHead(404);
        res.end();
        return;
      }
      res.setHeader(
        "Content-Type",
        name.endsWith(".wasm")
          ? "application/wasm"
          : name.endsWith(".js")
            ? "text/javascript"
            : "application/json",
      );
      res.end(await readFile(name));
    } catch {
      res.writeHead(500);
      res.end();
    }
  });
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  let browser;
  try {
    const { chromium } = await import("@playwright/test");
    browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const result = await page.evaluate(async () => {
      const { createEngine } = await import("/index.js");
      const engine = await createEngine();
      const cases = await (await fetch("/cases.json")).json();
      // Calculations after initialization must work with no network available.
      globalThis.fetch = () => {
        throw new Error("Unexpected network access");
      };
      const methods = {
        parse: "parseTime",
        convert: "convert",
        altitude: "adjustAltitude",
        youth: "youth",
        masters: "masters",
        points: "points",
      };
      return cases.map(({ operation, input }) =>
        engine[methods[operation]](input),
      );
    });
    verify(result, "WebAssembly/Chromium");
  } finally {
    await browser?.close();
    server.close();
  }
} else if (mode === "swift" || mode === "kotlin") {
  const protocol = cases
    .map(
      ({ operation, input }) =>
        `${operation}\t${Buffer.from(JSON.stringify(input)).toString("base64")}\n`,
    )
    .join("");
  let result;
  if (mode === "swift")
    result = spawnSync("target/conformance/swift-test", [], {
      input: protocol,
      encoding: "utf8",
      maxBuffer: 32 * 1024 * 1024,
    });
  else
    result = spawnSync(
      process.env.JAVA_HOME ? `${process.env.JAVA_HOME}/bin/java` : "java",
      [
        "-Djna.library.path=" + resolve("target/debug"),
        "-cp",
        `target/conformance/kotlin-test.jar:${process.env.JNA_JAR}`,
        "MainKt",
      ],
      { input: protocol, encoding: "utf8", maxBuffer: 32 * 1024 * 1024 },
    );
  if (result.error) throw result.error;
  assert.equal(result.status, 0, result.stderr);
  verify(
    result.stdout
      .trim()
      .split("\n")
      .map((line) => JSON.parse(line)),
    mode,
  );
} else throw new Error("Use wasm, swift or kotlin");
