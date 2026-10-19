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
  | "standardSystem"
  | "category"
  | "course"
  | "altitude"
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
    standardSystem: defaultState.standardSystem,
    category: defaultState.category,
    course: defaultState.course,
    altitude: defaultState.altitude,
    method: defaultState.method,
    elevationUnit: "ft",
    standardMode: "targets",
  };
  if (!value || typeof value !== "object" || Array.isArray(value))
    return preferences;
  const raw = value as Record<string, unknown>;
  if (raw.method === "ncaa-2025-27" || raw.method === "colorado-teamunify-2026")
    preferences.method = raw.method;
  if (ages.some((age) => age.id === raw.age))
    preferences.age = raw.age as SwimState["age"];
  if (
    typeof raw.mastersAge === "string" &&
    mastersAges.includes(raw.mastersAge)
  )
    preferences.mastersAge = raw.mastersAge;
  if (raw.standardSystem === "youth" || raw.standardSystem === "masters")
    preferences.standardSystem = raw.standardSystem;
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
