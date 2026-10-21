import initialize, {
  evaluate,
  engine_version,
  type InitInput,
} from "./generated/converter/turnmark_wasm.js";
import type { EngineOptions } from "./core.js";
import type { Result } from "./contracts.js";
import type {
  ConversionRequest,
  ConversionValue,
  AltitudeRequest,
  AltitudeValue,
} from "./conversion.js";
export type { ConversionMethod, AltitudePolicy } from "./conversion-methods.js";
export type { Elevation } from "./conversion.js";
export type {
  EngineOptions,
  ConversionRequest,
  ConversionValue,
  AltitudeRequest,
  AltitudeValue,
};
export type {
  Course,
  Category,
  Stroke,
  Swim,
  SwimEvent,
  Result,
} from "./contracts.js";
export {
  conversionMethod,
  coloradoMethod,
  conversionMethods,
  altitudePolicies,
} from "./conversion-methods.js";

let ready: Promise<void> | undefined;
let initialized = false;
function call<T>(operation: string, input: unknown): T {
  if (!initialized)
    throw new Error("Initialize the converter with await createConverter().");
  let request: string;
  try {
    request =
      JSON.stringify(input, (_key, value: unknown) =>
        ["bigint", "symbol", "function"].includes(typeof value) ? null : value,
      ) ?? "null";
  } catch {
    request = "null";
  }
  return JSON.parse(evaluate(operation, request)) as T;
}

/** Conversion/altitude-only payload; independent from the full SDK runtime. */
export async function createConverter(options: EngineOptions = {}) {
  await (ready ??= initialize(
    options.wasm === undefined
      ? undefined
      : { module_or_path: options.wasm as InitInput },
  )
    .then(() => {
      initialized = true;
    })
    .catch((error: unknown) => {
      ready = undefined;
      throw error;
    }));
  return Object.freeze({
    version: engine_version(),
    parseTime: (input: unknown): number | null =>
      typeof input === "string" ? call("parse", input) : null,
    convert: (request: ConversionRequest): Result<ConversionValue> =>
      call("convert", request),
    adjustAltitude: (request: AltitudeRequest): Result<AltitudeValue> =>
      call("altitude", request),
  });
}
export type Converter = Awaited<ReturnType<typeof createConverter>>;
