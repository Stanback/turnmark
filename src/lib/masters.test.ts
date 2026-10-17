import { expect, it } from "vitest";
import data from "../../data/masters.json";
import { getMastersTarget } from "./masters";
import { defaultState, readState, stateHash } from "./swim";
it("matches independently checked USMS table cells and course distance mapping", () => {
  expect(getMastersTarget("18-24", "women", "SCY", 100, "FR")).toBe(64.07);
  expect(getMastersTarget("25-29", "men", "LCM", 100, "FR")).toBe(62.23);
  expect(getMastersTarget("25-29", "women", "SCY", 400, "FR")).toBe(361.63);
  expect(data.records).toHaveLength(70);
  expect(
    data.records.flatMap((row) => row.times).filter((x) => x !== null),
  ).toHaveLength(904);
});
it("leaves NO TIME cells, ages 85+, and SCM unfilled", () => {
  expect(getMastersTarget("80-84", "women", "LCM", 1500, "FR")).toBeNull();
  expect(getMastersTarget("85+", "men", "SCY", 100, "FR")).toBeNull();
  expect(getMastersTarget("18-24", "women", "SCM", 100, "FR")).toBeNull();
});
it("preserves adult standards context in shared and saved swims", () => {
  const state = {
    ...defaultState,
    standardSystem: "masters" as const,
    mastersAge: "40-44",
  };
  expect(readState(stateHash(state))).toEqual(state);
  expect(readState("#b=unrecognized&ma=999")).toEqual(defaultState);
});
