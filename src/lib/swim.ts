// Web-only labels, share links, and display helpers stay outside the SDK.
import type { StandardSystem } from "@turnmark/sdk";
import {
  availableEvent,
  courses,
  eventDistances,
  eventDistance,
  parseTime,
  type Age,
  type Category,
  type Course,
  type Stroke,
} from "@turnmark/sdk/compat";
import {
  conversionMethod,
  coloradoMethod,
  empiricalMethod,
  type ConversionMethod,
  type AltitudePolicy,
  convertSwim,
  adjustAltitude,
} from "@turnmark/sdk/conversion";
export {
  availableEvent,
  courses,
  eventDistances,
  eventDistance,
  parseTime,
  formatTime,
  truncateTime,
  toYardFactor,
  altitudeAdjustment,
  adjustedTime,
  convert,
  getStandards,
  standardStatus,
  type Age,
  type Category,
  type Course,
  type Stroke,
  type Conversion,
} from "@turnmark/sdk/compat";
export const strokes: { id: Stroke; name: string; short: string }[] = [
  { id: "FR", name: "Freestyle", short: "Free" },
  { id: "BK", name: "Backstroke", short: "Back" },
  { id: "BR", name: "Breaststroke", short: "Breast" },
  { id: "FL", name: "Butterfly", short: "Fly" },
  { id: "IM", name: "Individual medley", short: "IM" },
];
export const courseInfo = {
  SCY: { name: "Short course yards", pool: "25 yards", meters: 22.86 },
  SCM: { name: "Short course meters", pool: "25 meters", meters: 25 },
  LCM: { name: "Long course meters", pool: "50 meters", meters: 50 },
};
export const ages: { id: Age; label: string }[] = [
  { id: "10u", label: "10 & under" },
  ...(["11-12", "13-14", "15-16", "17-18"] as Age[]).map((id) => ({
    id,
    label: id.replace("-", "–"),
  })),
];
export const levels = ["B", "BB", "A", "AA", "AAA", "AAAA"];
export function eventLabel(distance: number, course: Course, stroke: Stroke) {
  return `${eventDistance(distance, course, stroke)} ${strokes.find((s) => s.id === stroke)!.short}`;
}
export const mastersAges = [
  "18-24",
  ...Array.from(
    { length: 12 },
    (_, index) => `${25 + index * 5}-${29 + index * 5}`,
  ),
  "85+",
];
export interface SwimState {
  time: string;
  stroke: Stroke;
  distance: number;
  course: Course;
  category: Category;
  age: Age;
  altitude: number;
  standardSystem: StandardSystem;
  futuresAge: string;
  mastersAge: string;
  method: ConversionMethod;
  altitudePolicy: AltitudePolicy;
}
export const defaultState: SwimState = {
  time: "58.32",
  stroke: "FR",
  distance: 100,
  course: "SCY",
  category: "women",
  age: "15-16",
  altitude: 0,
  standardSystem: "youth",
  mastersAge: "18-24",
  futuresAge: "18 & under",
  method: conversionMethod,
  altitudePolicy: "usa-swimming-altitude-2026",
};
export function readState(hash: string): SwimState {
  const p = new URLSearchParams(hash.replace(/^#/, ""));
  const state = { ...defaultState };
  if (parseTime(p.get("t") ?? "") !== null) state.time = p.get("t")!;
  if (strokes.some((x) => x.id === p.get("s")))
    state.stroke = p.get("s") as Stroke;
  const distance = Number(p.get("d"));
  if (eventDistances(state.stroke).includes(distance))
    state.distance = distance;
  if (courses.includes(p.get("c") as Course))
    state.course = p.get("c") as Course;
  if (!availableEvent(state.distance, state.course, state.stroke))
    state.course = "SCY";
  if (["women", "men"].includes(p.get("g") ?? ""))
    state.category = p.get("g") as Category;
  if (ages.some((x) => x.id === p.get("a"))) state.age = p.get("a") as Age;
  const altitude = Number(p.get("h"));
  if (Number.isFinite(altitude) && altitude >= 0 && altitude <= 20000)
    state.altitude = altitude;
  if (["masters", "futures", "juniors", "nisca"].includes(p.get("b") ?? ""))
    state.standardSystem = p.get("b") as StandardSystem;
  if (["18 & under", "19 & over"].includes(p.get("fa") ?? ""))
    state.futuresAge = p.get("fa")!;
  if (mastersAges.includes(p.get("ma") ?? "")) state.mastersAge = p.get("ma")!;
  if (p.get("m") === coloradoMethod || p.get("m") === empiricalMethod)
    state.method = p.get("m") as ConversionMethod;
  if (p.get("ap") === "ncaa-altitude-2026-27-d1")
    state.altitudePolicy = "ncaa-altitude-2026-27-d1";
  return state;
}
export function stateHash(state: SwimState) {
  return new URLSearchParams({
    t: state.time,
    s: state.stroke,
    d: String(state.distance),
    c: state.course,
    g: state.category,
    a: state.age,
    h: String(state.altitude),
    ...(state.altitudePolicy === "ncaa-altitude-2026-27-d1"
      ? { ap: state.altitudePolicy }
      : {}),
    ...(state.method !== conversionMethod ? { m: state.method } : {}),
    ...(state.standardSystem === "masters"
      ? { b: "masters", ma: state.mastersAge }
      : state.standardSystem !== "youth"
        ? {
            b: state.standardSystem,
            ...(state.standardSystem === "futures"
              ? { fa: state.futuresAge ?? "18 & under" }
              : {}),
          }
        : {}),
  }).toString();
}
export function csvCell(value: string | number) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

/** Piecewise scale keeps the live marker aligned with the six published thresholds. */
export function ladderPosition(time: number, times: number[]): number {
  if (time >= times[0]) return 0;
  if (time <= times[5]) return 100;
  for (let i = 0; i < 5; i++) {
    if (time <= times[i] && time >= times[i + 1])
      return i * 20 + ((times[i] - time) / (times[i] - times[i + 1])) * 20;
  }
  return 0;
}

const sdkStrokes = {
  FR: "freestyle",
  BK: "backstroke",
  BR: "breaststroke",
  FL: "butterfly",
  IM: "individual-medley",
} as const;
export function swimRequest(state: SwimState) {
  return {
    time: state.time,
    event: {
      distance: eventDistance(state.distance, state.course, state.stroke),
      stroke: sdkStrokes[state.stroke],
      course: state.course,
    },
  };
}
export function stateAltitude(state: SwimState) {
  return adjustAltitude({
    swim: swimRequest(state),
    elevation: { value: state.altitude, unit: "feet" },
    policy: state.altitudePolicy,
  });
}
export function convertState(state: SwimState, to: Course) {
  const result = convertSwim({
    swim: swimRequest(state),
    to,
    table: state.category,
    method: state.method,
    ...(state.altitude !== 0
      ? {
          elevation: { value: state.altitude, unit: "feet" as const },
          altitudePolicy: state.altitudePolicy,
        }
      : {}),
  });
  return result.status === "available"
    ? {
        time: result.value.seconds,
        factor: result.value.factor,
        offsetSeconds: result.value.offsetSeconds,
        caveat: result.value.caveat,
        kind: result.value.kind,
      }
    : {
        time: null,
        factor: null,
        kind: "unavailable" as const,
        reason: result.reason,
        caveat: undefined,
      };
}
