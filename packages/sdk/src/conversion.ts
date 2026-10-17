import { convert, altitudeAdjustment } from "./internal/conversion.js";
import { eventDistance, availableEvent } from "./internal/events.js";
import { conversionSource, altitudeSource } from "./data/conversions.js";
import sources from "./data/sources.json" with { type: "json" };
import { formatTime } from "./time.js";
import {
  record,
  invalid,
  isCourse,
  isCategory,
  validateSwim,
  type Swim,
  type SwimEvent,
  type Course,
  type Category,
  type Provenance,
  type Result,
} from "./contracts.js";
export { conversionSource, altitudeSource } from "./data/conversions.js";
export type {
  Course,
  Category,
  Swim,
  SwimEvent,
  Result,
  Provenance,
} from "./contracts.js";

export const conversionMethod = "ncaa-2025-27";
export const conversionProvenance: Readonly<Provenance> = Object.freeze({
  id: conversionMethod,
  ...conversionSource,
  sha256: sources.ncaa.sha256,
});
export const altitudeProvenance: Readonly<Provenance> = Object.freeze({
  id: "usa-swimming-altitude-2026",
  title: altitudeSource.title,
  url: altitudeSource.url,
  revision: altitudeSource.verified,
});
export interface ConversionRequest {
  swim: Swim;
  to: Course;
  table: Category;
  method?: typeof conversionMethod;
}
export interface ConversionValue {
  time: string;
  seconds: number;
  hundredths: number;
  factor: number;
  kind: "swum" | "published" | "derived";
  event: SwimEvent;
}
export function convertSwim(
  request: ConversionRequest,
): Result<ConversionValue>;
export function convertSwim(request: unknown): Result<ConversionValue> {
  if (!record(request)) return invalid("request", "invalid-input");
  if (request.method !== undefined && request.method !== conversionMethod)
    return invalid("method", "unsupported-method");
  if (!isCourse(request.to)) return invalid("to", "invalid-course");
  if (!isCategory(request.table)) return invalid("table", "invalid-category");
  const swim = validateSwim(request.swim);
  if ("status" in swim) return swim;
  const provenance = { ...conversionProvenance };
  if (
    !availableEvent(swim.distance, swim.event.course, swim.stroke) ||
    !availableEvent(swim.distance, request.to, swim.stroke)
  )
    return { status: "unavailable", reason: "event-not-published", provenance };
  const result = convert(
    swim.seconds,
    swim.stroke,
    swim.distance,
    swim.event.course,
    request.to,
    request.table,
  );
  if (
    result.time === null ||
    result.factor === null ||
    result.kind === "unavailable"
  )
    return {
      status: "unavailable",
      reason: "factor-not-published",
      provenance,
    };
  return {
    status: "available",
    provenance,
    value: {
      time: formatTime(result.time),
      seconds: result.time,
      hundredths: Math.round(result.time * 100),
      factor: result.factor,
      kind: result.kind,
      event: {
        ...swim.event,
        course: request.to,
        distance: eventDistance(swim.distance, request.to, swim.stroke),
      },
    },
  };
}
export interface AltitudeRequest {
  swim: Swim;
  elevation: { value: number; unit: "feet" | "meters" };
}
export interface AltitudeValue {
  rawTime: string;
  adjustedTime: string;
  rawSeconds: number;
  adjustedSeconds: number;
  adjustmentSeconds: number;
  elevationFeet: number;
  kind: "swum" | "altitude-adjusted";
}
export function adjustAltitude(request: AltitudeRequest): Result<AltitudeValue>;
export function adjustAltitude(request: unknown): Result<AltitudeValue> {
  if (!record(request)) return invalid("request", "invalid-input");
  const swim = validateSwim(request.swim);
  if ("status" in swim) return swim;
  const elevation = request.elevation;
  if (
    !record(elevation) ||
    (elevation.unit !== "feet" && elevation.unit !== "meters") ||
    typeof elevation.value !== "number" ||
    !Number.isFinite(elevation.value) ||
    elevation.value < 0 ||
    elevation.value > (elevation.unit === "meters" ? 6096 : 20000) ||
    (elevation.unit === "feet" && !Number.isInteger(elevation.value))
  )
    return invalid("elevation", "invalid-elevation");
  const provenance = { ...altitudeProvenance };
  if (!availableEvent(swim.distance, swim.event.course, swim.stroke))
    return { status: "unavailable", reason: "event-not-published", provenance };
  const feet =
    elevation.unit === "meters"
      ? Math.round(elevation.value / 0.3048)
      : elevation.value;
  const adjustment = altitudeAdjustment(swim.distance, feet);
  if (swim.seconds <= adjustment) return invalid("swim.time", "invalid-time");
  const adjustedSeconds =
    Math.round(swim.seconds * 100 - adjustment * 100) / 100;
  return {
    status: "available",
    provenance,
    value: {
      rawTime: formatTime(swim.seconds),
      adjustedTime: formatTime(adjustedSeconds),
      rawSeconds: swim.seconds,
      adjustedSeconds,
      adjustmentSeconds: adjustment,
      elevationFeet: feet,
      kind: adjustment > 0 ? "altitude-adjusted" : "swum",
    },
  };
}
