import { describe, expect, it } from "vitest";
import {
  benchmarkPreview,
  benchmarkTimeStandardChoices,
} from "./benchmark-preview";
import { defaultState, swimRequest } from "./swim";

describe("converted benchmark previews", () => {
  it("orders time standard choices with USA Swimming grouped before NISCA and Masters", () => {
    expect(benchmarkTimeStandardChoices()).toEqual([
      { id: "youth", label: "USA Swimming · Youth" },
      { id: "futures", label: "USA Swimming · Futures" },
      { id: "juniors", label: "Junior Nationals" },
      { id: "nisca", label: "NISCA · All-America" },
      { id: "masters", label: "USMS · Masters" },
    ]);
  });
  it("uses the selected method and enabled altitude without changing the entered swim", () => {
    const entered = {
      ...defaultState,
      method: "colorado-teamunify-2026" as const,
    };
    expect(benchmarkPreview(entered, "LCM")?.time).toBe("1:06.33");
    const altitude = {
      ...defaultState,
      altitude: 5000,
      altitudePolicy: "ncaa-altitude-2026-27-d1" as const,
    };
    expect(benchmarkPreview(altitude, "LCM")?.time).toBe("1:06.61");
    expect(entered.time).toBe("58.32");
    expect(altitude.altitude).toBe(5000);
  });
  it("retains the engine's unequal-distance destination event", () => {
    const preview = benchmarkPreview(
      { ...defaultState, distance: 1650, time: "17:00.00" },
      "LCM",
    );
    expect(preview).not.toBeNull();
    expect(swimRequest(preview!).event).toEqual({
      distance: 1500,
      stroke: "freestyle",
      course: "LCM",
    });
    expect(preview!.altitude).toBe(0); // The already adjusted estimate must not be adjusted twice.
  });
  it("does not substitute entered swims for unavailable or invalid conversions", () => {
    expect(
      benchmarkPreview({ ...defaultState, stroke: "IM", distance: 100 }, "LCM"),
    ).toBeNull();
    expect(
      benchmarkPreview(
        { ...defaultState, altitude: 5000, time: "0.01", distance: 200 },
        "LCM",
      ),
    ).toBeNull();
  });
});
