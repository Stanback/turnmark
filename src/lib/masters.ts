import data from "../data/masters.json";
import { eventDistance, type Course, type Category, type Stroke } from "./swim";
export const mastersSource = data.source;
/** A null cell means USMS explicitly lists NO TIME; undefined means no matching entry. */
export function getMastersEntry(
  age: string,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
): number | null | undefined {
  const index = data.ages.indexOf(age);
  if (index < 0 || course === "SCM") return undefined;
  return data.records.find(
    (row) =>
      row.course === course &&
      row.category === category &&
      row.distance === eventDistance(distance, course, stroke) &&
      row.stroke === stroke,
  )?.times[index];
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
