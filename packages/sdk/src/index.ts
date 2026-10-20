export {
  assessSwimBenchmark,
  getNationalStandardPrograms,
  type StandardProgram,
  type BenchmarkRequest,
  type BenchmarkValue,
  type TimeTarget,
  type StandardSystem,
} from "./benchmarks.js";
import { assessSwimBenchmark } from "./benchmarks.js";
export {
  convertSwim,
  adjustAltitude,
  conversionMethod,
  coloradoMethod,
  conversionMethods,
  altitudePolicies,
  type AltitudePolicy,
  type Elevation,
  type ConversionMethod,
  type ConversionRequest,
  type ConversionValue,
  type AltitudeRequest,
  type AltitudeValue,
} from "./conversion.js";
export { parseTime, formatTime } from "./time.js";
export type {
  Course,
  Category,
  Stroke,
  Swim,
  SwimEvent,
  Result,
  Provenance,
  CoverageReason,
  ValidationReason,
} from "./contracts.js";
import { convertSwim, adjustAltitude } from "./conversion.js";
import { parseTime } from "./time.js";
import { getYouthStandards } from "./youth.js";
import { getMastersTarget } from "./masters.js";
import { getWorldPoints } from "./points.js";
import { initializeEngine, engineVersion, type EngineOptions } from "./core.js";
export type { EngineOptions } from "./core.js";

/** Load the shared Rust engine once; subsequent calculations are synchronous and offline. */
export async function createEngine(options: EngineOptions = {}) {
  await initializeEngine(options);
  return Object.freeze({
    version: engineVersion(),
    parseTime,
    convert: convertSwim,
    adjustAltitude,
    youth: getYouthStandards,
    masters: getMastersTarget,
    points: getWorldPoints,
    benchmark: assessSwimBenchmark,
  });
}
export type Engine = Awaited<ReturnType<typeof createEngine>>;
