import { compatibility } from "../core.js";
import type { Course, Category, Stroke } from "./events.js";
export { mastersSource } from "../masters.js";
export function getMastersEntry(
  age: string,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
): number | null | undefined {
  return compatibility<{ entry?: number | null }>("getMastersEntry", [
    age,
    category,
    course,
    distance,
    stroke,
  ]).entry;
}
export function getMastersTarget(
  age: string,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
): number | null {
  return getMastersEntry(age, category, course, distance, stroke) ?? null;
}
