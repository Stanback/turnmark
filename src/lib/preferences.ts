import {
  ages,
  courses,
  defaultState,
  mastersAges,
  type SwimState,
} from "./swim";

export type SwimPreferences = Pick<
  SwimState,
  | "age"
  | "mastersAge"
  | "futuresAge"
  | "standardSystem"
  | "category"
  | "course"
  | "altitude"
  | "altitudePolicy"
  | "method"
> & {
  elevationUnit: "ft" | "m";
  standardMode: "targets" | "points";
};

/** Only validated preferences become defaults; race inputs belong in history. */
export function readPreferences(value: unknown): SwimPreferences {
  const preferences: SwimPreferences = {
    age: defaultState.age,
    mastersAge: defaultState.mastersAge,
    futuresAge: defaultState.futuresAge,
    standardSystem: defaultState.standardSystem,
    category: defaultState.category,
    course: defaultState.course,
    altitude: defaultState.altitude,
    altitudePolicy: defaultState.altitudePolicy,
    method: defaultState.method,
    elevationUnit: "ft",
    standardMode: "targets",
  };
  if (!value || typeof value !== "object" || Array.isArray(value))
    return preferences;
  const raw = value as Record<string, unknown>;
  if (raw.altitudePolicy === "ncaa-altitude-2026-27-d1")
    preferences.altitudePolicy = raw.altitudePolicy;
  if (raw.method === "ncaa-2025-27" || raw.method === "colorado-teamunify-2026")
    preferences.method = raw.method;
  if (ages.some((age) => age.id === raw.age))
    preferences.age = raw.age as SwimState["age"];
  if (
    typeof raw.mastersAge === "string" &&
    mastersAges.includes(raw.mastersAge)
  )
    preferences.mastersAge = raw.mastersAge;
  if (
    typeof raw.standardSystem === "string" &&
    ["youth", "masters", "futures", "juniors", "nisca"].includes(
      raw.standardSystem,
    )
  )
    preferences.standardSystem =
      raw.standardSystem as SwimState["standardSystem"];
  if (raw.futuresAge === "18 & under" || raw.futuresAge === "19 & over")
    preferences.futuresAge = raw.futuresAge;
  if (raw.category === "women" || raw.category === "men")
    preferences.category = raw.category;
  if (courses.includes(raw.course as SwimState["course"]))
    preferences.course = raw.course as SwimState["course"];
  if (
    typeof raw.altitude === "number" &&
    Number.isInteger(raw.altitude) &&
    raw.altitude >= 0 &&
    raw.altitude <= 20000
  )
    preferences.altitude = raw.altitude;
  if (raw.elevationUnit === "ft" || raw.elevationUnit === "m")
    preferences.elevationUnit = raw.elevationUnit;
  if (raw.standardMode === "targets" || raw.standardMode === "points")
    preferences.standardMode = raw.standardMode;
  return preferences;
}
