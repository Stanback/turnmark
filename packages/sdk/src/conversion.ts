import { callCore } from "./core.js";
import metadata from "./generated/metadata.json" with { type: "json" };
import {
  conversionSource,
  altitudeSource,
  coloradoSource,
} from "./data/conversions.js";
import type {
  Swim,
  SwimEvent,
  Course,
  Category,
  Provenance,
  Result,
} from "./contracts.js";
export { conversionSource, altitudeSource, coloradoSource };
export type {
  Course,
  Category,
  Swim,
  SwimEvent,
  Result,
  Provenance,
} from "./contracts.js";

export const conversionMethod = "ncaa-2025-27";
export const coloradoMethod = "colorado-teamunify-2026";
export type ConversionMethod = typeof conversionMethod | typeof coloradoMethod;
export const conversionMethods = [
  { id: conversionMethod, label: "NCAA (default)", source: conversionSource },
  { id: coloradoMethod, label: "Colorado Timing", source: coloradoSource },
] as const;
export const conversionProvenance: Readonly<Provenance> = Object.freeze({
  id: conversionMethod,
  ...conversionSource,
  sha256: metadata.sources.ncaa.sha256,
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
  method?: ConversionMethod;
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
}
export function convertSwim(
  request: ConversionRequest,
): Result<ConversionValue>;
export function convertSwim(request: unknown): Result<ConversionValue> {
  return callCore("convert", request);
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
  return callCore("altitude", request);
}
