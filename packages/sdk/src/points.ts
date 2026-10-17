import { callCore } from "./core.js";
import metadata from "./generated/metadata.json" with { type: "json" };
import type { Swim, Category, Result } from "./contracts.js";
export const pointsEdition = "world-aquatics-2026";
export const pointsSource = Object.freeze({ ...metadata.points.source });
export const pointsValidity = Object.freeze({ ...metadata.points.validity });
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
  return callCore("points", request);
}
