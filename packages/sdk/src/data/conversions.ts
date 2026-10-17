/** Factual factors transcribed from NCAA 2025–26/2026–27 Rules, Appendix C, p.120.
 * The NCAA publishes metric → SCY only. Reverse and metric → metric are derived.
 * Deliberately no invented LCM factor for 50 back/breast/fly or 100 IM.
 */
export const conversionSource = {
  title: "NCAA 2025–26 & 2026–27 Rules",
  url: "https://ncaaorg.s3.amazonaws.com/championships/sports/swimdive/rules/PRXSW_RulesBook.pdf#page=125",
  revision: "2026-10-01",
  verified: "2026-10-16",
};
export const longCourseFactors: Record<
  "women" | "men",
  Record<string, number>
> = {
  women: {
    "50-FR": 0.871,
    "100-FR": 0.874,
    "200-FR": 0.874,
    "400-FR": 1.112,
    "800-FR": 1.12,
    "1500-FR": 0.975,
    "100-BK": 0.853,
    "200-BK": 0.857,
    "100-BR": 0.87,
    "200-BR": 0.878,
    "100-FL": 0.877,
    "200-FL": 0.881,
    "200-IM": 0.867,
    "400-IM": 0.876,
  },
  men: {
    "50-FR": 0.86,
    "100-FR": 0.863,
    "200-FR": 0.865,
    "400-FR": 1.105,
    "800-FR": 1.105,
    "1500-FR": 0.965,
    "100-BK": 0.835,
    "200-BK": 0.849,
    "100-BR": 0.856,
    "200-BR": 0.858,
    "100-FL": 0.868,
    "200-FL": 0.866,
    "200-IM": 0.857,
    "400-IM": 0.865,
  },
};
export const altitudeSource = {
  title: "USA Swimming Times & Recognition Policy Manual, §4.7",
  url: "https://www.usaswimming.org/docs/default-source/timesdocuments/general-docs/times-and-recognition-policy-manual.pdf#page=7",
  verified: "2026-10-16",
};
export const altitudeAdjustments: Record<
  number,
  readonly [number, number, number]
> = {
  200: [0.5, 1.2, 1.6],
  400: [2.5, 5, 7],
  800: [5, 10, 15],
  1500: [11, 23, 32.5],
};
