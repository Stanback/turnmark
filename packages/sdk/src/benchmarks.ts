import { callCore } from "./core.js";
import type { Swim, SwimEvent, Category, Result } from "./contracts.js";
export type StandardSystem =
  "youth" | "masters" | "futures" | "juniors" | "nisca";
export interface StandardProgram {
  system: StandardSystem;
  label: string;
  title: string;
  scope: string;
  ages: string[];
  note: string;
}
/** Source-backed program labels and coverage. Initialize the SDK first. */
export function getNationalStandardPrograms(): StandardProgram[] {
  return callCore("national-programs", {});
}
export interface BenchmarkRequest {
  swim: Swim;
  table: Category;
  age: string;
  system: StandardSystem;
  edition?: string;
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
