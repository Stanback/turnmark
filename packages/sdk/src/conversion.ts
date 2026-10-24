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
  /**
   * Multiplier applied to the entered seconds. For `turnmark-empirical-2026`
   * (Turnmark Equivalence) it is equivalent seconds / entered seconds, so it
   * varies with the entered time.
   */
  factor: number;
  /** Add after multiplication, before final truncation. Omitted when zero; Turnmark Equivalence never sets it. */
  offsetSeconds?: number;
  kind: "swum" | "published" | "derived";
  /**
   * How the engine computed `time`: `none` (same course), `multiplier`
   * (× factor), `multiplier-offset` (× factor + offsetSeconds) or `equivalent`
   * (Turnmark Equivalence's mapping). Describe the arithmetic from this field
   * rather than from the method.
   */
  formula: "none" | "multiplier" | "multiplier-offset" | "equivalent";
  event: SwimEvent;
  altitude?: { value: AltitudeValue; provenance: Provenance };
  /**
   * Engine-owned limitation to show with the result. `empirical-out-of-range`
   * marks a Turnmark Equivalence time outside the model's fitted range for this
   * event and course pair, which extrapolates beyond the available fit.
   * `empirical-low-evidence` marks one from a cell with fewer than 100 effective
   * swimmers or where the conversion's bootstrap interval is wider than 1%.
   */
  caveat?:
    | "colorado-short-course-distance"
    | "empirical-low-evidence"
    | "empirical-out-of-range";
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
