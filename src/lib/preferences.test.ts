import { describe, expect, it } from "vitest";
import { readPreferences } from "./preferences";

describe("stored preferences", () => {
  it("rejects malformed records and invalid fields without dropping valid preferences", () => {
    const defaults = readPreferences(null);
    for (const raw of [[], "invalid", 123, false])
      expect(readPreferences(raw)).toEqual(defaults);
    expect(
      readPreferences({
        age: "40-44",
        mastersAge: "40-44",
        category: "other",
        course: "pool",
        altitude: "5280",
        elevationUnit: "yards",
        standardMode: "unknown",
        standardSystem: "unknown",
      }),
    ).toEqual({ ...defaults, mastersAge: "40-44" });
  });

  it("only remembers whole-foot elevations within the supported range", () => {
    for (const altitude of [-1, 20001, 100.5, NaN, Infinity])
      expect(readPreferences({ altitude }).altitude).toBe(0);
    for (const altitude of [0, 3000, 5280, 20000])
      expect(readPreferences({ altitude }).altitude).toBe(altitude);
  });

  it("does not restore race inputs from preference storage", () => {
    expect(
      readPreferences({
        time: "12:34",
        stroke: "BR",
        distance: 200,
        category: "men",
        course: "LCM",
        age: "17-18",
        elevationUnit: "m",
        standardMode: "points",
        standardSystem: "masters",
      }),
    ).toEqual({
      ...readPreferences(null),
      category: "men",
      course: "LCM",
      age: "17-18",
      elevationUnit: "m",
      standardMode: "points",
      standardSystem: "masters",
    });
  });
});
