import { compatibility } from "../core.js";
export type Course = "SCY" | "SCM" | "LCM";
export type Stroke = "FR" | "BK" | "BR" | "FL" | "IM";
export type Category = "women" | "men";
export type Age = "10u" | "11-12" | "13-14" | "15-16" | "17-18";
export const courses: Course[] = ["SCY", "SCM", "LCM"];
export function eventDistances(stroke: Stroke): number[] {
  return compatibility("eventDistances", [stroke]);
}
export function eventDistance(
  distance: number,
  course: Course,
  stroke: Stroke,
): number {
  return compatibility("eventDistance", [distance, course, stroke]);
}
export function availableEvent(
  distance: number,
  course: Course,
  stroke: Stroke,
): boolean {
  return compatibility("availableEvent", [distance, course, stroke]);
}
