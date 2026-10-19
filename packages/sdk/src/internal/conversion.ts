import { compatibility } from "../core.js";
import type { Stroke, Course, Category } from "./events.js";
import { conversionMethod, type ConversionMethod } from "../conversion.js";
export function toYardFactor(
  stroke: Stroke,
  distance: number,
  course: Course,
  category: Category,
): number | null {
  return compatibility("toYardFactor", [stroke, distance, course, category]);
}
export function altitudeAdjustment(distance: number, altitude: number): number {
  return compatibility("altitudeAdjustment", [distance, altitude]);
}
export function adjustedTime(
  time: number | null,
  distance: number,
  altitude: number,
): number | null {
  return compatibility("adjustedTime", [time, distance, altitude]);
}
export type Conversion = {
  time: number | null;
  factor: number | null;
  offsetSeconds?: number;
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
  method: ConversionMethod = conversionMethod,
): Conversion {
  return compatibility("convert", [
    time,
    stroke,
    distance,
    from,
    to,
    category,
    method,
  ]);
}
