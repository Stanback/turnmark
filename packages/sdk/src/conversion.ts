import { callCore } from "./core.js";
import type {
  Swim,
  SwimEvent,
  Course,
  Category,
  Provenance,
  Result,
} from "./contracts.js";
import type { ConversionMethod, AltitudePolicy } from "./conversion-methods.js";
export * from "./conversion-methods.js";
export type {
  Course,
  Category,
  Swim,
  SwimEvent,
  Result,
  Provenance,
} from "./contracts.js";

export interface Elevation {
  value: number;
  unit: "feet" | "meters";
}
export interface ConversionRequest {
  swim: Swim;
  to: Course;
  table: Category;
  method?: ConversionMethod;
  elevation?: Elevation;
  altitudePolicy?: AltitudePolicy;
}
export interface ConversionValue {
  time: string;
  seconds: number;
  hundredths: number;
  factor: number;
  /** Add after multiplication, before final truncation. Omitted when zero. */
  offsetSeconds?: number;
  kind: "swum" | "published" | "derived";
  event: SwimEvent;
  altitude?: { value: AltitudeValue; provenance: Provenance };
  caveat?: "colorado-short-course-distance";
}
export function convertSwim(
  request: ConversionRequest,
): Result<ConversionValue>;
export function convertSwim(request: unknown): Result<ConversionValue> {
  return callCore("convert", request);
}

export interface AltitudeRequest {
  swim: Swim;
  elevation: Elevation;
  policy?: AltitudePolicy;
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
  return callCore("altitude", request);
}
