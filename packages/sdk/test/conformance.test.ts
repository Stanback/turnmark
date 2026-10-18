import { describe, expect, it } from "vitest";
import {
  createEngine,
  assessSwimBenchmark,
  type BenchmarkRequest,
  convertSwim,
  adjustAltitude,
  parseTime,
  formatTime,
  type ConversionRequest,
  type AltitudeRequest,
} from "../dist/index.js";
import { getYouthStandards, type YouthRequest } from "../dist/youth.js";
import { getMastersTarget, type MastersRequest } from "../dist/masters.js";
import { getWorldPoints, type PointsRequest } from "../dist/points.js";
import fixtures from "../../../fixtures/sdk-conformance.json";
import pointData from "../../../data/points.json";

const operations: Record<string, (input: unknown) => unknown> = {
  parse: parseTime,
  benchmark: (input) => assessSwimBenchmark(input as BenchmarkRequest),
  convert: (input) => convertSwim(input as ConversionRequest),
  altitude: (input) => adjustAltitude(input as AltitudeRequest),
  youth: (input) => getYouthStandards(input as YouthRequest),
  masters: (input) => getMastersTarget(input as MastersRequest),
  points: (input) => getWorldPoints(input as PointsRequest),
};

describe("portable SDK conformance", () => {
  for (const fixture of fixtures.cases) {
    it(fixture.id, () => {
      const result = operations[fixture.operation](fixture.input);
      if (fixture.expected !== null && typeof fixture.expected === "object") {
        expect(result).toMatchObject(fixture.expected);
        if (
          "status" in fixture.expected &&
          fixture.expected.status !== "invalid"
        ) {
          expect(result).toHaveProperty("provenance.url");
          expect(result).toHaveProperty("provenance.revision");
        }
      } else expect(result).toBe(fixture.expected);
    });
  }
});

it("rejects non-JSON JavaScript values without throwing or coercing", () => {
  for (const value of [
    undefined,
    NaN,
    Infinity,
    -Infinity,
    true,
    Symbol("input"),
    () => {},
  ]) {
    for (const operation of [
      "convert",
      "altitude",
      "youth",
      "masters",
      "points",
    ]) {
      expect(operations[operation](value)).toEqual({
        status: "invalid",
        field: "request",
        reason: "invalid-input",
      });
    }
    expect(parseTime(value)).toBeNull();
  }
});

it("reuses the initialized engine and exposes the same conversion contract", async () => {
  const engine = await createEngine();
  const fixture = fixtures.cases.find(
    (entry) => entry.id === "ncaa-rulebook-example",
  )!;
  expect(engine.convert(fixture.input as ConversionRequest)).toEqual(
    convertSwim(fixture.input as ConversionRequest),
  );
  expect(Object.isFrozen(engine)).toBe(true);
});

it("returns independent result data so callers cannot change subsequent calculations", () => {
  const request: YouthRequest = {
    event: { distance: 100, stroke: "freestyle", course: "SCY" },
    table: "women",
    age: "15-16",
  };
  const first = getYouthStandards(request);
  if (first.status !== "available")
    throw new Error("Missing verified source row");
  first.value.times[0] = 0;
  first.value.levels[0] = "changed";
  first.provenance.url = "changed";
  first.value.event.distance = 999;
  expect(getYouthStandards(request)).toMatchObject({
    status: "available",
    value: {
      times: [68.79, 63.79, 58.89, 56.49, 53.99, 51.59],
      levels: ["B", "BB", "A", "AA", "AAA", "AAAA"],
      event: { distance: 100 },
    },
  });
});

it("scores all published base times and verifies the slowest hundredth at each next milestone", () => {
  const strokes = {
    FR: "freestyle",
    BK: "backstroke",
    BR: "breaststroke",
    FL: "butterfly",
    IM: "individual-medley",
  } as const;
  for (const row of pointData.events)
    for (const table of ["women", "men"] as const) {
      const event = {
        distance: row.distance,
        stroke: strokes[row.stroke as keyof typeof strokes],
        course: row.course as "SCM" | "LCM",
      };
      const base = getWorldPoints({
        swim: { time: formatTime(row[table]), event },
        table,
      });
      expect(base).toMatchObject({
        status: "available",
        value: { points: 1000 },
      });
      for (const multiplier of [1, 1.2, 1.6, 2.5]) {
        const current = getWorldPoints({
          swim: { time: formatTime(row[table] * multiplier), event },
          table,
        });
        if (current.status !== "available")
          throw new Error("Missing supported metric event");
        const target = current.value.nextMilestone;
        const atTarget = getWorldPoints({
          swim: { time: target.time, event },
          table,
        });
        const afterTarget = getWorldPoints({
          swim: { time: formatTime(target.seconds + 0.01), event },
          table,
        });
        if (
          atTarget.status !== "available" ||
          afterTarget.status !== "available"
        )
          throw new Error("Invalid milestone result");
        expect(atTarget.value.points).toBeGreaterThanOrEqual(target.points);
        expect(afterTarget.value.points).toBeLessThan(target.points);
      }
    }
});
