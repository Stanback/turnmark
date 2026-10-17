import data from "../data/masters.json";
import { eventDistance, type Course, type Category, type Stroke } from "./swim";
export const mastersSource = data.source;
export function getMastersTarget(
  age: string,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
): number | null {
  const index = data.ages.indexOf(age);
  if (index < 0 || course === "SCM") return null;
  return (
    data.records.find(
      (row) =>
        row.course === course &&
        row.category === category &&
        row.distance === eventDistance(distance, course, stroke) &&
        row.stroke === stroke,
    )?.times[index] ?? null
  );
}
