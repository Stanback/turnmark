import data from "./data/standards.json" with { type: "json" };
import { getStandards } from "./internal/youth.js";
import { availableEvent } from "./internal/events.js";
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
import type { Age } from "./internal/events.js";

export const youthEdition = "usa-swimming-2024-28";
export const youthAges = ["10u", "11-12", "13-14", "15-16", "17-18"] as const;
export const standardsSource = Object.freeze({
  ...data.source,
  levels: Object.freeze([...data.source.levels]),
});
const provenance: Readonly<Provenance> = Object.freeze({
  id: youthEdition,
  title: data.source.title,
  url: data.source.url,
  revision: data.source.revision,
  sha256: data.source.sha256,
});
export interface YouthRequest {
  event: SwimEvent;
  table: Category;
  age: Age;
  edition?: typeof youthEdition;
}
export interface YouthValue {
  event: SwimEvent;
  age: Age;
  levels: string[];
  times: number[];
}
export function getYouthStandards(request: YouthRequest): Result<YouthValue>;
export function getYouthStandards(request: unknown): Result<YouthValue> {
  if (!record(request)) return invalid("request", "invalid-input");
  if (request.edition !== undefined && request.edition !== youthEdition)
    return invalid("edition", "unsupported-dataset");
  if (!isCategory(request.table)) return invalid("table", "invalid-category");
  if (
    typeof request.age !== "string" ||
    !youthAges.some((age) => age === request.age)
  )
    return invalid("age", "invalid-age-group");
  const event = validateEvent(request.event, "event");
  if ("status" in event) return event;
  const times = availableEvent(event.distance, event.event.course, event.stroke)
    ? getStandards(
        request.age as Age,
        request.table,
        event.event.course,
        event.distance,
        event.stroke,
      )
    : null;
  if (times === null)
    return {
      status: "unavailable",
      reason: "event-not-published",
      provenance: { ...provenance },
    };
  return {
    status: "available",
    provenance: { ...provenance },
    value: {
      event: event.event,
      age: request.age as Age,
      levels: [...standardsSource.levels],
      times: [...times],
    },
  };
}
