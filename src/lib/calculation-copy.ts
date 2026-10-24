export const coloradoDistanceCaveat =
  "Distance caveat: this documented Colorado rule uses a general SCM/SCY multiplier for unequal-distance freestyle events. Check the meet’s required conversion.";

export const empiricalLowEvidenceCaveat =
  "Limited data: few swimmers in Turnmark’s data swam this event in both of these courses at this level, so this equivalent time is less certain and leans on related events and pool geometry.";

export const empiricalOutOfRangeCaveat =
  "Outside the model’s fitted range: this estimate extrapolates beyond the available fit.";

/** The note to show with a conversion caveat, or an empty string when there is none. */
export function caveatText(caveat: string | undefined): string {
  if (caveat === "empirical-low-evidence") return empiricalLowEvidenceCaveat;
  if (caveat === "empirical-out-of-range") return empiricalOutOfRangeCaveat;
  if (caveat === "colorado-short-course-distance")
    return coloradoDistanceCaveat;
  return "";
}

/** Short description of the engine-reported formula, or an empty string for the swum time. */
export function formulaText(formula: string | undefined): string {
  if (formula === "multiplier") return "flat multiplier";
  if (formula === "multiplier-offset") return "fixed turn offset";
  if (formula === "equivalent") return "equivalent time";
  return "";
}

/** Selected-calculation note for Turnmark Equivalence, whose factor varies with the entered time. */
export const empiricalCalculationNote =
  "Turnmark Equivalence: the model’s equivalent time in this course. The multiplier shown applies to this entered time.";

export const ncaaMethodExplanation =
  "Factors vary by event and course, not age. Long-course factors use separate men’s and women’s tables; short-course meters-to-yards factors are shared. NCAA publishes metric-to-yards factors; reverse and SCM/LCM conversions are derived.";

export const empiricalMethodExplanation =
  "Estimates the equivalent time in the other course from 95K pairs of the same swimmer racing both courses within a month (8.51M US swims, 2010–2026), allowing for the randomness in any single swim. Converting back returns the entered time to within 0.02 s.";

export const poolLengthExplanation =
  "Shorter pools mean more turns and push-offs. These rules do not adjust for your starts, underwater skill, technique, endurance or individual development.";

export const methodComparisonCaveat =
  "Published rules and an equivalence model, not a prediction range or guarantee of entry eligibility. Use the method required by your meet.";
