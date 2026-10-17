import {
  eventDistances,
  eventDistance,
  type Course,
  type Category,
  type Stroke as StrokeCode,
} from "./internal/events.js";
import { parseTime } from "./time.js";

export type { Course, Category } from "./internal/events.js";
export type Stroke =
  | "freestyle"
  | "backstroke"
  | "breaststroke"
  | "butterfly"
  | "individual-medley";
export interface SwimEvent {
  distance: number;
  stroke: Stroke;
  course: Course;
}
export interface Swim {
  time: string;
  event: SwimEvent;
}
export interface Provenance {
  id: string;
  title: string;
  url: string;
  revision: string;
  sha256?: string;
}
export type CoverageReason =
  | "event-not-published"
  | "course-not-supported"
  | "age-group-not-published"
  | "factor-not-published"
  | "no-time-published";
export type ValidationReason =
  | "invalid-input"
  | "invalid-time"
  | "invalid-course"
  | "invalid-stroke"
  | "invalid-distance"
  | "invalid-category"
  | "invalid-age-group"
  | "invalid-elevation"
  | "unsupported-method"
  | "unsupported-dataset"
  | "unsafe-result";
export type Invalid = {
  status: "invalid";
  field: string;
  reason: ValidationReason;
};
export type Unavailable = {
  status: "unavailable";
  reason: CoverageReason;
  provenance: Provenance;
};
export type Result<T> =
  | { status: "available"; value: T; provenance: Provenance }
  | Unavailable
  | Invalid;

export const strokeCodes: Readonly<Record<Stroke, StrokeCode>> = Object.freeze({
  freestyle: "FR",
  backstroke: "BK",
  breaststroke: "BR",
  butterfly: "FL",
  "individual-medley": "IM",
});
export function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
export function invalid(field: string, reason: ValidationReason): Invalid {
  return { status: "invalid", field, reason };
}
export function isCourse(value: unknown): value is Course {
  return value === "SCY" || value === "SCM" || value === "LCM";
}
export function isCategory(value: unknown): value is Category {
  return value === "women" || value === "men";
}
export function validateEvent(
  value: unknown,
  field = "swim.event",
): { event: SwimEvent; stroke: StrokeCode; distance: number } | Invalid {
  if (!record(value)) return invalid(field, "invalid-input");
  if (!isCourse(value.course))
    return invalid(`${field}.course`, "invalid-course");
  if (
    typeof value.stroke !== "string" ||
    !Object.hasOwn(strokeCodes, value.stroke)
  )
    return invalid(`${field}.stroke`, "invalid-stroke");
  const stroke = strokeCodes[value.stroke as Stroke];
  const distance = eventDistances(stroke).find(
    (candidate) =>
      eventDistance(candidate, value.course as Course, stroke) ===
      value.distance,
  );
  if (distance === undefined)
    return invalid(`${field}.distance`, "invalid-distance");
  return {
    event: {
      course: value.course,
      distance: value.distance as number,
      stroke: value.stroke as Stroke,
    },
    stroke,
    distance,
  };
}
export function validateSwim(
  value: unknown,
):
  | { event: SwimEvent; stroke: StrokeCode; distance: number; seconds: number }
  | Invalid {
  if (!record(value)) return invalid("swim", "invalid-input");
  const seconds = parseTime(value.time);
  if (seconds === null) return invalid("swim.time", "invalid-time");
  const normalized = validateEvent(value.event);
  return "status" in normalized ? normalized : { ...normalized, seconds };
}
