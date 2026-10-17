import { callCore } from "./core.js";
import metadata from "./generated/metadata.json" with { type: "json" };
import type { SwimEvent, Category, Result } from "./contracts.js";
import type { Age } from "./internal/events.js";
export const youthEdition = "usa-swimming-2024-28";
export const youthAges = ["10u", "11-12", "13-14", "15-16", "17-18"] as const;
export const standardsSource = Object.freeze({
  ...metadata.youth.source,
  levels: Object.freeze([...metadata.youth.source.levels]),
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
  return callCore("youth", request);
}
