import { createEngine, type EngineOptions } from "./index.js";
export type { EngineOptions };
export type {
  BenchmarkRequest,
  BenchmarkValue,
  StandardProgram,
  StandardSystem,
} from "./benchmarks.js";
export { getNationalStandardPrograms } from "./benchmarks.js";

/** Published benchmarks/points. Uses the full payload because explicit preview
 * assessments also need conversion/altitude; never initializes converter.wasm. */
export async function createStandardsEngine(options: EngineOptions = {}) {
  const engine = await createEngine(options);
  return Object.freeze({
    version: engine.version,
    youth: engine.youth,
    masters: engine.masters,
    points: engine.points,
    benchmark: engine.benchmark,
  });
}
export type StandardsEngine = Awaited<ReturnType<typeof createStandardsEngine>>;
