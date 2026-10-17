import data from "./data/masters.json" with { type: "json" };
import { getMastersEntry } from "./internal/masters.js";
import {
  record,
  invalid,
  isCategory,
  validateEvent,
  type SwimEvent,
  type Category,
  type Provenance,
  type Result,
} from "./contracts.js";
import { formatTime } from "./time.js";

export const mastersEdition = "usms-nationals-2026";
export const mastersSource = Object.freeze({ ...data.source });
export const mastersAges: readonly string[] = Object.freeze([
  ...data.ages,
  "85+",
]);
const provenance: Readonly<Provenance> = Object.freeze({
  id: mastersEdition,
  title: data.source.name,
  url: data.source.url,
  revision: data.source.checked,
  sha256: data.source.sha256,
});
export interface MastersRequest {
  event: SwimEvent;
  table: Category;
  age: string;
  edition?: typeof mastersEdition;
}
export interface MastersValue {
  event: SwimEvent;
  age: string;
  time: string;
  seconds: number;
  hundredths: number;
}
export function getMastersTarget(request: MastersRequest): Result<MastersValue>;
export function getMastersTarget(request: unknown): Result<MastersValue> {
  if (!record(request)) return invalid("request", "invalid-input");
  if (request.edition !== undefined && request.edition !== mastersEdition)
    return invalid("edition", "unsupported-dataset");
  if (!isCategory(request.table)) return invalid("table", "invalid-category");
  if (typeof request.age !== "string" || !mastersAges.includes(request.age))
    return invalid("age", "invalid-age-group");
  const event = validateEvent(request.event, "event");
  if ("status" in event) return event;
  const source = { ...provenance };
  if (event.event.course === "SCM")
    return {
      status: "unavailable",
      reason: "course-not-supported",
      provenance: source,
    };
  if (request.age === "85+")
    return {
      status: "unavailable",
      reason: "age-group-not-published",
      provenance: source,
    };
  const seconds = getMastersEntry(
    request.age,
    request.table,
    event.event.course,
    event.distance,
    event.stroke,
  );
  if (seconds === null)
    return {
      status: "unavailable",
      reason: "no-time-published",
      provenance: source,
    };
  if (seconds === undefined)
    return {
      status: "unavailable",
      reason: "event-not-published",
      provenance: source,
    };
  return {
    status: "available",
    provenance: source,
    value: {
      event: event.event,
      age: request.age,
      time: formatTime(seconds),
      seconds,
      hundredths: Math.round(seconds * 100),
    },
  };
}
