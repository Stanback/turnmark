import standards from "../data/standards.json" with { type: "json" };
import {
  eventDistance,
  type Age,
  type Category,
  type Course,
  type Stroke,
} from "./events.js";
export const standardsSource = standards.source;
export function getStandards(
  age: Age,
  category: Category,
  course: Course,
  distance: number,
  stroke: Stroke,
) {
  return (
    standards.records.find(
      (r) =>
        r.age === age &&
        r.category === category &&
        r.course === course &&
        r.distance === eventDistance(distance, course, stroke) &&
        r.stroke === stroke,
    )?.times ?? null
  );
}
export function standardStatus(time: number, times: number[]) {
  let achieved = -1;
  times.forEach((threshold, i) => {
    if (time <= threshold + 1e-8) achieved = i;
  });
  return { achieved, next: achieved < 5 ? achieved + 1 : null };
}
