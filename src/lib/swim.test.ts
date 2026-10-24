import { describe, it, expect } from "vitest";
import {
  altitudeAdjustment,
  availableEvent,
  convert,
  convertState,
  courses,
  defaultState,
  eventDistance,
  eventDistances,
  getStandards,
  ladderPosition,
  parseTime,
  readState,
  standardStatus,
  stateHash,
  strokes,
  formatTime,
} from "./swim";
import data from "../../data/standards.json";
import empirical from "../../data/empirical.json";
import { caveatText } from "./calculation-copy";
import type { Course, Stroke } from "./swim";

describe("swimmer time input and hundredths", () => {
  it.each([
    ["58.32", 58.32],
    ["1:02.45", 62.45],
    ["60", 60],
    ["0:00.01", 0.01],
    [" 2:16.71 ", 136.71],
    ["60:00", 3600],
  ])("parses %s", (input, expected) =>
    expect(parseTime(input as string)).toBe(expected),
  );
  it.each([
    "",
    "0",
    "-12",
    "1:60",
    "1:99.12",
    "1:2:3",
    "abc",
    "NaN",
    "Infinity",
    "12.345",
    "3601",
    "1e2",
    "<script>",
  ])("rejects invalid time %s", (input) => expect(parseTime(input)).toBeNull());
  it("retains hundredths at binary floating point boundaries", () => {
    expect(formatTime(59.99)).toBe("59.99");
    expect(formatTime(62.45)).toBe("1:02.45");
    expect(formatTime(59.999)).toBe("59.99");
  });
});
describe("verified NCAA conversion examples", () => {
  it("reproduces the rulebook’s 200 breaststroke men example exactly", () =>
    expect(convert(136.71, "BR", 200, "LCM", "SCY", "men").time).toBe(117.29));
  it("uses the event-specific distance factor for 400m → 500yd", () => {
    expect(convert(240, "FR", 400, "SCM", "SCY", "women").time).toBe(274.32);
    expect(eventDistance(400, "SCY", "FR")).toBe(500);
  });
  it("uses separate long-course tables for women and men", () => {
    expect(convert(60, "FR", 100, "LCM", "SCY", "women").time).toBe(52.44);
    expect(convert(60, "FR", 100, "LCM", "SCY", "men").time).toBe(51.78);
  });
  it("labels reciprocal and cross-metric estimates as derived", () => {
    expect(convert(60, "FR", 100, "SCY", "LCM", "men").kind).toBe("derived");
    expect(convert(60, "FR", 100, "SCM", "LCM", "women").factor).toBeCloseTo(
      0.896 / 0.874,
    );
  });
  it("never fabricates unsupported long-course events", () => {
    expect(convert(30, "FL", 50, "SCY", "LCM", "women").time).toBeNull();
    expect(convert(60, "IM", 100, "SCY", "LCM", "men").time).toBeNull();
    expect(availableEvent(100, "LCM", "IM")).toBe(false);
  });
  it("keeps the actual entered source time", () =>
    expect(convert(62.45, "FR", 100, "SCY", "SCY", "women")).toMatchObject({
      time: 62.45,
      kind: "swum",
    }));
  it("all supported events convert with consistent factors in both directions", () => {
    for (const stroke of strokes)
      for (const distance of eventDistances(stroke.id))
        for (const from of courses)
          for (const to of courses)
            for (const category of ["women", "men"] as const) {
              const result = convert(
                120.99,
                stroke.id,
                distance,
                from,
                to,
                category,
              );
              if (result.time === null) continue;
              expect(result.time).toBeGreaterThan(0);
              const reversed = convert(
                result.time,
                stroke.id,
                distance,
                to,
                from,
                category,
              );
              expect(Math.abs(reversed.time! - 120.99)).toBeLessThan(0.03);
            }
  });
});
describe("USA Swimming altitude policy", () => {
  it("honors every altitude band boundary", () => {
    expect(altitudeAdjustment(200, 2999)).toBe(0);
    expect(altitudeAdjustment(200, 3000)).toBe(0.5);
    expect(altitudeAdjustment(200, 4250)).toBe(0.5);
    expect(altitudeAdjustment(200, 4251)).toBe(1.2);
    expect(altitudeAdjustment(200, 6500)).toBe(1.2);
    expect(altitudeAdjustment(200, 6501)).toBe(1.6);
  });
  it("does not apply an adjustment to sprint events", () =>
    expect(altitudeAdjustment(100, 8000)).toBe(0));
  it("maps equivalent distance events to the published correction", () =>
    expect(altitudeAdjustment(400, 6000)).toBe(5));
});
describe("published motivational dataset", () => {
  it("contains the complete extracted individual-event table", () => {
    expect(data.records).toHaveLength(482);
    expect(
      data.records.reduce((total, row) => total + row.times.length, 0),
    ).toBe(2892);
    expect(
      new Set(
        data.records.map((x) =>
          [x.age, x.category, x.course, x.distance, x.stroke].join("/"),
        ),
      ).size,
    ).toBe(482);
  });
  it("matches independently inspected PDF cells and category ordering", () => {
    expect(getStandards("13-14", "men", "SCY", 50, "FR")).toEqual([
      29.89, 27.69, 25.59, 24.59, 23.49, 22.39,
    ]);
    expect(getStandards("15-16", "women", "SCY", 100, "FR")).toEqual([
      68.79, 63.79, 58.89, 56.49, 53.99, 51.59,
    ]);
    expect(getStandards("10u", "women", "SCY", 100, "FR")?.[0]).toBe(90.79);
  });
  it("every category has six strictly faster levels", () => {
    for (const row of data.records) {
      expect(row.times).toHaveLength(6);
      for (let i = 1; i < 6; i++)
        expect(row.times[i]).toBeLessThan(row.times[i - 1]);
    }
  });
  it("does not silently invent missing standards", () =>
    expect(getStandards("10u", "women", "SCY", 200, "FL")).toBeNull());
  it("counts the exact cut and identifies the next faster level", () => {
    const times = [70, 65, 60, 55, 50, 45];
    expect(standardStatus(60, times)).toEqual({ achieved: 2, next: 3 });
    expect(standardStatus(80, times)).toEqual({ achieved: -1, next: 0 });
    expect(standardStatus(40, times)).toEqual({ achieved: 5, next: null });
    expect(ladderPosition(60, times)).toBe(40);
    expect(ladderPosition(57.5, times)).toBe(50);
  });
});
describe("share links", () => {
  it("round-trips a complete swim", () => {
    const swim = {
      ...defaultState,
      time: "2:16.71",
      stroke: "BR" as const,
      distance: 200,
      course: "LCM" as const,
      altitude: 5280,
      method: "turnmark-empirical-2026" as const,
    };
    expect(readState(stateHash(swim))).toEqual(swim);
  });
  it("validates malicious or stale query values", () => {
    expect(readState("#t=Infinity&s=evil&d=999&c=XXX&g=no&a=99&h=-1")).toEqual(
      defaultState,
    );
    expect(readState("#s=IM&d=100&c=LCM").course).toBe("SCY");
  });
});

type Knots = [number, number][];
type EquivalenceCell = Record<Course, { knots: Knots }>;
const equivalenceCells = Object.entries(
  empirical.cells as unknown as Record<string, EquivalenceCell>,
).map(([key, cell]) => {
  const [event, category] = key.split("|") as [string, "men" | "women"];
  const [distance, stroke] = event.split("-") as [string, Stroke];
  return { key, event, category, distance: Number(distance), stroke, cell };
});
const coursePairs = courses.flatMap((from) =>
  courses.filter((to) => to !== from).map((to) => [from, to] as const),
);
const equivalenceSwim = (
  item: (typeof equivalenceCells)[number],
  course: Course,
  seconds: number,
) => ({
  ...defaultState,
  method: "turnmark-empirical-2026" as const,
  stroke: item.stroke,
  distance: item.distance,
  category: item.category,
  course,
  time: formatTime(seconds),
});
// The equivalence model, from its documented definition: each course maps onto a shared latent
// scale through piecewise-linear knots in log seconds, with slope 1 beyond the outer knots.
const knotMap = (knots: Knots, x: number, inverse: boolean) => {
  const [i, o] = inverse ? [1, 0] : [0, 1];
  const first = knots[0]!;
  const last = knots[knots.length - 1]!;
  if (x <= first[i]) return first[o] + (x - first[i]);
  if (x >= last[i]) return last[o] + (x - last[i]);
  let k = 0;
  while (knots[k + 1]![i] <= x) k++;
  const lo = knots[k]!;
  const hi = knots[k + 1]!;
  return lo[o] + ((x - lo[i]) * (hi[o] - lo[o])) / (hi[i] - lo[i]);
};
const latentOf = (cell: EquivalenceCell, from: Course, x: number) =>
  knotMap(cell[from].knots, Math.log(x), true);
const equivalentSeconds = (
  cell: EquivalenceCell,
  from: Course,
  to: Course,
  x: number,
) => Math.exp(knotMap(cell[to].knots, latentOf(cell, from, x), false));
// A typical entered time: the middle knot of the source course's map.
const typicalSeconds = (cell: EquivalenceCell, from: Course) => {
  const knots = cell[from].knots;
  return Math.exp(knots[Math.floor(knots.length / 2)]![1]);
};
const expectedCaveat = (
  item: (typeof equivalenceCells)[number],
  from: Course,
  to: Course,
  x: number,
) => {
  const u = latentOf(item.cell, from, x);
  const a = item.cell[from].knots;
  const b = item.cell[to].knots;
  const lo = Math.max(a[0]![0], b[0]![0]);
  const hi = Math.min(a[a.length - 1]![0], b[b.length - 1]![0]);
  if (!(lo <= u && u <= hi)) return "empirical-out-of-range";
  const key = `${from}->${to}|${item.event}|${item.category}`;
  const precise = (
    empirical.preciseLatentRanges as unknown as Record<
      string,
      [number, number] | null
    >
  )[key];
  if (
    empirical.lowEvidenceCells.includes(key) ||
    !precise ||
    !(precise[0] <= u && u <= precise[1])
  )
    return "empirical-low-evidence";
  return undefined;
};

describe("Turnmark Equivalence conversions", () => {
  it("covers every published event in the equivalence data", () => {
    for (const item of equivalenceCells)
      for (const course of courses)
        expect(
          availableEvent(item.distance, course, item.stroke),
          item.key,
        ).toBe(true);
  });
  it("returns the equivalent time from the fitted course maps, truncated once", () => {
    for (const item of equivalenceCells)
      for (const [from, to] of coursePairs)
        for (const ratio of [0.6, 0.85, 1, 1.2, 1.8]) {
          const entered =
            Math.floor(typicalSeconds(item.cell, from) * ratio * 100) / 100;
          const expected = equivalentSeconds(item.cell, from, to, entered);
          const result = convertState(equivalenceSwim(item, from, entered), to);
          const label = `${item.key} ${from}→${to} ${entered}`;
          expect(result.time, label).not.toBeNull();
          expect(result.time!, label).toBeLessThanOrEqual(expected + 1e-9);
          expect(expected - result.time!, label).toBeLessThan(0.01);
          expect(result.offsetSeconds ?? 0, label).toBe(0);
          expect(result.factor!, label).toBeCloseTo(expected / entered, 9);
        }
  });
  it("converts there and back to the entered time or a few hundredths faster", () => {
    for (const item of equivalenceCells)
      for (const [from, to] of coursePairs)
        for (const ratio of [0.6, 0.9, 1, 1.1, 1.8]) {
          const entered =
            Math.floor(typicalSeconds(item.cell, from) * ratio * 100) / 100;
          const there = convertState(
            equivalenceSwim(item, from, entered),
            to,
          ).time!;
          const back = convertState(
            equivalenceSwim(item, to, there),
            from,
          ).time!;
          const label = `${item.key} ${from}→${to}→${from} ${entered}`;
          expect(back, label).toBeLessThanOrEqual(entered + 1e-9);
          expect(entered - back, label).toBeLessThanOrEqual(0.05 + 1e-9);
        }
  });
  it("never converts a faster entered time slower", () => {
    for (const item of equivalenceCells)
      for (const [from, to] of coursePairs) {
        const typical = typicalSeconds(item.cell, from);
        let previous = 0;
        for (let step = 0; step <= 60; step++) {
          const entered = Math.floor(typical * (0.6 + step * 0.02) * 100) / 100;
          const converted = convertState(
            equivalenceSwim(item, from, entered),
            to,
          ).time!;
          expect(
            converted,
            `${item.key} ${from}→${to} ${entered}`,
          ).toBeGreaterThanOrEqual(previous);
          previous = converted;
        }
      }
  });
});

describe("Turnmark Equivalence caveats", () => {
  const empiricalSwim = {
    ...defaultState,
    method: "turnmark-empirical-2026" as const,
  };
  it("marks thin cells as low evidence", () => {
    expect(empirical.lowEvidenceCells).toContain("SCY->SCM|200-FL|women");
    const thin = convertState(
      {
        ...empiricalSwim,
        time: "2:20.00",
        stroke: "FL" as const,
        distance: 200,
        course: "SCY",
        category: "women",
      },
      "SCM",
    );
    expect(thin.time).toBeCloseTo(156.49, 9);
    expect(thin.caveat).toBe("empirical-low-evidence");
    expect(caveatText(thin.caveat)).toBe(
      "Limited data: few swimmers in Turnmark’s data swam this event in both of these courses at this level, so this equivalent time is less certain and leans on related events and pool geometry.",
    );
  });
  it("marks times beyond the data as out of range", () => {
    const mile = convertState(
      {
        ...empiricalSwim,
        time: "14:13.00",
        distance: 1650,
        course: "SCY",
        category: "men",
      },
      "LCM",
    );
    expect(mile.caveat).toBe("empirical-out-of-range");
    expect(caveatText(mile.caveat)).toBe(
      "Outside the model’s fitted range: this estimate extrapolates beyond the available fit.",
    );
  });
  it("follows the out-of-range, thin-cell and precision rules at every entered time", () => {
    for (const item of equivalenceCells)
      for (const [from, to] of coursePairs)
        for (const ratio of [0.5, 0.8, 1, 1.25, 2]) {
          const entered =
            Math.floor(typicalSeconds(item.cell, from) * ratio * 100) / 100;
          const key = `${item.key} ${from}→${to} ${entered}`;
          expect(
            convertState(equivalenceSwim(item, from, entered), to).caveat,
            key,
          ).toBe(expectedCaveat(item, from, to, entered));
        }
  });
  it("leaves well-supported times and other methods unmarked", () => {
    expect(empirical.lowEvidenceCells).not.toContain("SCY->LCM|100-FR|women");
    expect(convertState(empiricalSwim, "LCM").caveat).toBeUndefined();
    expect(
      convertState(
        {
          ...defaultState,
          time: "16:00.00",
          distance: 1500,
          course: "LCM",
          category: "men",
        },
        "SCM",
      ).caveat,
    ).toBeUndefined();
    expect(caveatText(undefined)).toBe("");
  });
});
