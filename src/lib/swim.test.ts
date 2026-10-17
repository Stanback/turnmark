import { describe, it, expect } from "vitest";
import {
  altitudeAdjustment,
  availableEvent,
  convert,
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
