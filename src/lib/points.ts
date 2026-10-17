import data from "../data/points.json";
import { eventDistance, type Course, type Stroke } from "./swim";

export const pointsSource = data.source;
export const pointsValidity = data.validity;

/** Score an entered metric swim, using the published integer truncation rule. */
export function worldPoints(
  time: number | null,
  course: Course,
  distance: number,
  stroke: Stroke,
  category: "women" | "men",
): number | null {
  if (course === "SCY" || time === null || !Number.isFinite(time) || time <= 0)
    return null;
  const row = data.events.find(
    (x) =>
      x.course === course &&
      x.distance === eventDistance(distance, course, stroke) &&
      x.stroke === stroke,
  );
  if (!row) return null;
  // Decimal roundoff must not turn a mathematically integral 1,000 into 999.
  const score = 1000 * (row[category] / time) ** 3;
  return Number.isSafeInteger(Math.floor(score))
    ? Math.floor(score + 1e-9)
    : null;
}
