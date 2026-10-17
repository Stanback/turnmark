import { altitudeAdjustments, longCourseFactors } from "../data/conversions.js";
import {
  availableEvent,
  type Stroke,
  type Course,
  type Category,
} from "./events.js";
import { truncateTime } from "../time.js";
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
