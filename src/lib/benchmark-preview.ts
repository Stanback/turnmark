import { convertSwim, getNationalStandardPrograms } from "@turnmark/sdk";
import {
  swimRequest,
  eventDistances,
  eventDistance,
  type SwimState,
  type Course,
} from "./swim";

/**
 * Presentation order for the "Time standards" group in the "Compare against"
 * selector across web and native surfaces: USA Swimming choices together,
 * followed by interscholastic (NISCA) and adult (USMS Masters) alternatives.
 */
export function benchmarkTimeStandardChoices(): ReadonlyArray<{
  id: SwimState["standardSystem"];
  label: string;
}> {
  return [
    { id: "youth", label: "USA Swimming · Youth" },
    ...getNationalStandardPrograms().map((program) => ({
      id: program.system,
      label: program.system === "juniors" ? "Junior Nationals" : program.label,
    })),
    { id: "masters", label: "USMS · Masters" },
  ];
}

/** Compose shared engine results; never relabel an unsupported preview as entered. */
export function benchmarkPreview(
  form: SwimState,
  to: Course,
): SwimState | null {
  const result = convertSwim({
    swim: swimRequest(form),
    to,
    table: form.category,
    method: form.method,
    ...(form.altitude !== 0
      ? {
          elevation: { value: form.altitude, unit: "feet" as const },
          altitudePolicy: form.altitudePolicy,
        }
      : {}),
  });
  if (result.status !== "available") return null;
  const event = result.value.event;
  const distance = eventDistances(form.stroke).find(
    (distance) =>
      eventDistance(distance, event.course, form.stroke) === event.distance,
  );
  if (distance === undefined) return null;
  return {
    ...form,
    time: result.value.time,
    course: event.course,
    distance,
    altitude: 0,
  };
}
