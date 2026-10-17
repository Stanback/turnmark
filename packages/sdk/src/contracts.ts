import type { Course, Stroke as StrokeCode } from "./internal/events.js";
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
  verified?: string;
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
