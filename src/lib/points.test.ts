import { describe, it, expect } from "vitest";
import { worldPoints } from "./points";
import data from "../data/points.json";
import type { Course, Stroke } from "./swim";

describe("World Aquatics points", () => {
  it("scores all 70 published base times at 1,000", () => {
    for (const row of data.events) {
      const distance = row.distance;
      for (const category of ["women", "men"] as const)
        expect(
          worldPoints(
            row[category],
            row.course as Course,
            distance,
            row.stroke as Stroke,
            category,
          ),
        ).toBe(1000);
    }
  });
  it("uses a cubic curve and truncates to whole points", () => {
    expect(worldPoints(99.86, "SCM", 100, "FR", "women")).toBe(125);
    expect(worldPoints(60, "LCM", 100, "FR", "men")).toBe(462);
    expect(worldPoints(45, "LCM", 100, "FR", "men")).toBeGreaterThan(1000);
  });
  it("leaves yards, unsupported events and invalid times unscored", () => {
    for (const time of [null, 0, -1, NaN, Infinity])
      expect(worldPoints(time, "LCM", 100, "FR", "women")).toBeNull();
    expect(worldPoints(58.32, "SCY", 100, "FR", "women")).toBeNull();
    expect(worldPoints(60, "LCM", 100, "IM", "women")).toBeNull();
  });
});
