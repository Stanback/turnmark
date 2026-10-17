import { compatibility } from "../core.js";
import type { Course, Stroke } from "./events.js";
export { pointsSource, pointsValidity } from "../points.js";
export function worldPoints(
  time: number | null,
  course: Course,
  distance: number,
  stroke: Stroke,
  category: "women" | "men",
): number | null {
  return compatibility("worldPoints", [
    time,
    course,
    distance,
    stroke,
    category,
  ]);
}
export function worldPointsContext(
  time: number | null,
  course: Course,
  distance: number,
  stroke: Stroke,
  category: "women" | "men",
): { base: number; nextMark: number; target: number; gap: number } | null {
  return compatibility("worldPointsContext", [
    time,
    course,
    distance,
    stroke,
    category,
  ]);
}
