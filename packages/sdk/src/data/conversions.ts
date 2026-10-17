import data from "./conversions.json" with { type: "json" };

export const conversionSource = data.conversionSource;
export const altitudeSource = data.altitudeSource;
export const longCourseFactors: Record<
  "women" | "men",
  Record<string, number>
> = data.longCourseFactors;
export const altitudeAdjustments: Record<number, readonly number[]> =
  data.altitudeAdjustments;
export const shortCourseFactors = data.shortCourseFactors;
