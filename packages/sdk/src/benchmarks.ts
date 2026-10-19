import { callCore } from "./core.js";
import type { Swim, SwimEvent, Category, Result } from "./contracts.js";
export type StandardSystem = "youth" | "masters";
export interface BenchmarkRequest {
  swim: Swim;
  table: Category;
  age: string;
  system: StandardSystem;
}
export interface TimeTarget {
  label: string;
  time: string;
  seconds: number;
  met: boolean;
  gapSeconds: number;
}
export interface BenchmarkValue {
  event: SwimEvent;
  age: string;
  system: StandardSystem;
  enteredTime: string;
  enteredSeconds: number;
  targets: TimeTarget[];
  achievedLevel: string | null;
  nextTarget: TimeTarget | null;
}
/** Compare the original swim with published targets. Never confirms entry eligibility. */
export function assessSwimBenchmark(
  request: BenchmarkRequest,
): Result<BenchmarkValue>;
export function assessSwimBenchmark(request: unknown): Result<BenchmarkValue> {
  return callCore("benchmark", request);
}
