import { altitudeAdjustments, longCourseFactors } from "../data/conversions";
import standards from "../data/standards.json";

export type Course = "SCY" | "SCM" | "LCM";
export type Stroke = "FR" | "BK" | "BR" | "FL" | "IM";
export type Category = "women" | "men";
export type Age = "10u" | "11-12" | "13-14" | "15-16" | "17-18";
export const courses: Course[] = ["SCY", "SCM", "LCM"];
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
export function eventDistances(stroke: Stroke): number[] {
  return stroke === "FR"
    ? [50, 100, 200, 400, 800, 1500]
    : stroke === "IM"
      ? [100, 200, 400]
      : [50, 100, 200];
}
export function eventDistance(
  distance: number,
  course: Course,
  stroke: Stroke,
): number {
  return course === "SCY" && stroke === "FR"
    ? ({ 400: 500, 800: 1000, 1500: 1650 }[distance] ?? distance)
    : distance;
}
export function eventLabel(distance: number, course: Course, stroke: Stroke) {
  return `${eventDistance(distance, course, stroke)} ${strokes.find((s) => s.id === stroke)!.short}`;
}
export function availableEvent(
  distance: number,
  course: Course,
  stroke: Stroke,
) {
  return !(stroke === "IM" && distance === 100 && course === "LCM");
}
/** Strict human time input, up to hundredths; no silent coercion, negative times or invalid clock fields. */
export function parseTime(input: string): number | null {
  const value = input.trim();
  if (!/^(?:\d+:)?\d+(?:\.\d{1,2})?$/.test(value)) return null;
  const pieces = value.split(":");
  if (pieces.length === 2 && Number(pieces[1]) >= 60) return null;
  const seconds =
    pieces.length === 2
      ? Number(pieces[0]) * 60 + Number(pieces[1])
      : Number(pieces[0]);
  return Number.isFinite(seconds) && seconds > 0 && seconds <= 3600
    ? seconds
    : null;
}
/** NCAA instruction: drop all units smaller than a hundredth. Epsilon only corrects binary representation. */
export function truncateTime(seconds: number) {
  return Math.floor(seconds * 100 + 1e-8) / 100;
}
export function formatTime(seconds: number | null, round = false): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return "—";
  const ticks = round
    ? Math.round(seconds * 100)
    : Math.floor(seconds * 100 + 1e-8);
  const mins = Math.floor(ticks / 6000),
    secs = Math.floor(ticks / 100) % 60,
    hundredths = ticks % 100;
  return `${mins > 0 ? `${mins}:${String(secs).padStart(2, "0")}` : secs}.${String(hundredths).padStart(2, "0")}`;
}
export function toYardFactor(
  stroke: Stroke,
  distance: number,
  course: Course,
  category: Category,
): number | null {
  if (!availableEvent(distance, course, stroke)) return null;
  if (course === "SCY") return 1;
  if (course === "SCM")
    return stroke === "FR" && [400, 800].includes(distance)
      ? 1.143
      : stroke === "FR" && distance === 1500
        ? 1.003
        : 0.896;
  return longCourseFactors[category][`${distance}-${stroke}`] ?? null;
}
export function altitudeAdjustment(distance: number, altitude: number): number {
  if (!Number.isFinite(altitude) || altitude < 3000) return 0;
  const band = altitude <= 4250 ? 0 : altitude <= 6500 ? 1 : 2;
  return altitudeAdjustments[distance]?.[band] ?? 0;
}
export type Conversion = {
  time: number | null;
  factor: number | null;
  kind: "swum" | "published" | "derived" | "unavailable";
  reason?: string;
};
export function convert(
  time: number,
  stroke: Stroke,
  distance: number,
  from: Course,
  to: Course,
  category: Category,
): Conversion {
  if (
    !availableEvent(distance, from, stroke) ||
    !availableEvent(distance, to, stroke)
  )
    return {
      time: null,
      factor: null,
      kind: "unavailable",
      reason: "100 IM is a short-course event.",
    };
  if (!Number.isFinite(time) || time <= 0)
    return {
      time: null,
      factor: null,
      kind: "unavailable",
      reason: "Enter a valid positive time.",
    };
  if (from === to) return { time, factor: 1, kind: "swum" };
  const sourceFactor = toYardFactor(stroke, distance, from, category),
    targetFactor = toYardFactor(stroke, distance, to, category);
  if (sourceFactor === null || targetFactor === null)
    return {
      time: null,
      factor: null,
      kind: "unavailable",
      reason: "No published NCAA long-course factor for this event.",
    };
  const factor = sourceFactor / targetFactor;
  return {
    time: truncateTime(time * factor),
    factor,
    kind: to === "SCY" ? "published" : "derived",
  };
}
export function getStandards(
  age: Age,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
) {
  return (
    standards.records.find(
      (r) =>
        r.age === age &&
        r.category === category &&
        r.course === course &&
        r.distance === eventDistance(distance, course, stroke) &&
        r.stroke === stroke,
    )?.times ?? null
  );
}
export function standardStatus(time: number, times: number[]) {
  let achieved = -1;
  times.forEach((threshold, i) => {
    if (time <= threshold + 1e-8) achieved = i;
  });
  return { achieved, next: achieved < 5 ? achieved + 1 : null };
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
  standardSystem: "youth" | "masters";
  mastersAge: string;
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
  if (p.get("b") === "masters") state.standardSystem = "masters";
  if (mastersAges.includes(p.get("ma") ?? "")) state.mastersAge = p.get("ma")!;
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
    ...(state.standardSystem === "masters"
      ? { b: "masters", ma: state.mastersAge }
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
