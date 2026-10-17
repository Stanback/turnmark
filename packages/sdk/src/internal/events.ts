export type Course = "SCY" | "SCM" | "LCM";
export type Stroke = "FR" | "BK" | "BR" | "FL" | "IM";
export type Category = "women" | "men";
export type Age = "10u" | "11-12" | "13-14" | "15-16" | "17-18";
export const courses: Course[] = ["SCY", "SCM", "LCM"];
export function eventDistances(stroke: Stroke): number[] {
  return stroke === "FR"
    ? [50, 100, 200, 400, 800, 1500]
    : stroke === "IM"
      ? [100, 200, 400]
      : [50, 100, 200];
}
export function eventDistance(
  distance: number,
  course: Course,
  stroke: Stroke,
): number {
  return course === "SCY" && stroke === "FR"
    ? ({ 400: 500, 800: 1000, 1500: 1650 }[distance] ?? distance)
    : distance;
}
export function availableEvent(
  distance: number,
  course: Course,
  stroke: Stroke,
) {
  return !(stroke === "IM" && distance === 100 && course === "LCM");
}
