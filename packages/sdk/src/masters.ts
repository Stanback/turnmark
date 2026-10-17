import { callCore } from "./core.js";
import metadata from "./generated/metadata.json" with { type: "json" };
import type { SwimEvent, Category, Result } from "./contracts.js";
export const mastersEdition = "usms-nationals-2026";
export const mastersSource = Object.freeze({ ...metadata.masters.source });
export const mastersAges: readonly string[] = Object.freeze([
  ...metadata.masters.ages,
  "85+",
]);
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
  return callCore("masters", request);
}
