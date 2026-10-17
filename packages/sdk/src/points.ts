import data from "./data/points.json" with { type: "json" };
import { worldPointsContext, worldPoints } from "./internal/points.js";
import {
  record,
  invalid,
  isCategory,
  validateSwim,
  type Swim,
  type Category,
  type Provenance,
  type Result,
} from "./contracts.js";
import { formatTime } from "./time.js";

export const pointsEdition = "world-aquatics-2026";
export const pointsSource = Object.freeze({ ...data.source });
export const pointsValidity = Object.freeze({ ...data.validity });
const provenance: Readonly<Provenance> = Object.freeze({
  id: pointsEdition,
  title: data.source.name,
  url: data.source.url,
  revision: data.source.checked,
  sha256: data.source.sha256,
});
export interface PointsRequest {
  swim: Swim;
  table: Category;
  edition?: typeof pointsEdition;
}
export interface PointsValue {
  points: number;
  baseTime: string;
  baseSeconds: number;
  validity: string;
  nextMilestone: {
    points: number;
    time: string;
    seconds: number;
    gapSeconds: number;
  };
}
export function getWorldPoints(request: PointsRequest): Result<PointsValue>;
export function getWorldPoints(request: unknown): Result<PointsValue> {
  if (!record(request)) return invalid("request", "invalid-input");
  if (request.edition !== undefined && request.edition !== pointsEdition)
    return invalid("edition", "unsupported-dataset");
  if (!isCategory(request.table)) return invalid("table", "invalid-category");
  const swim = validateSwim(request.swim);
  if ("status" in swim) return swim;
  const source = { ...provenance };
  if (swim.event.course === "SCY")
    return {
      status: "unavailable",
      reason: "course-not-supported",
      provenance: source,
    };
  const exists = data.events.some(
    (row) =>
      row.course === swim.event.course &&
      row.distance === swim.event.distance &&
      row.stroke === swim.stroke,
  );
  if (!exists)
    return {
      status: "unavailable",
      reason: "event-not-published",
      provenance: source,
    };
  const points = worldPoints(
    swim.seconds,
    swim.event.course,
    swim.distance,
    swim.stroke,
    request.table,
  );
  const context = worldPointsContext(
    swim.seconds,
    swim.event.course,
    swim.distance,
    swim.stroke,
    request.table,
  );
  if (points === null || context === null)
    return invalid("swim.time", "unsafe-result");
  return {
    status: "available",
    provenance: source,
    value: {
      points,
      baseTime: formatTime(context.base),
      baseSeconds: context.base,
      validity: data.validity[swim.event.course],
      nextMilestone: {
        points: context.nextMark,
        time: formatTime(context.target),
        seconds: context.target,
        gapSeconds: context.gap,
      },
    },
  };
}
