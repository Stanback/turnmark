import { compatibility } from "../core.js";
import type { Age, Category, Course, Stroke } from "./events.js";
export { standardsSource } from "../youth.js";
export function getStandards(
  age: Age,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
): number[] | null {
  return compatibility("getStandards", [
    age,
    category,
    course,
    distance,
    stroke,
  ]);
}
export function standardStatus(
  time: number,
  times: number[],
): { achieved: number; next: number | null } {
  return compatibility("standardStatus", [time, times]);
}
