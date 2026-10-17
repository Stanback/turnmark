import initialize, {
  evaluate,
  engine_version,
  type InitInput,
} from "./generated/turnmark_wasm.js";
// Reuse the established public contract during migration. These imports are
// erased: this adapter executes no TypeScript domain calculation or validation.
import type {
  ConversionRequest,
  ConversionValue,
  AltitudeRequest,
  AltitudeValue,
  Result,
} from "@turnmark/sdk";
import type { YouthRequest, YouthValue } from "@turnmark/sdk/youth";
import type { MastersRequest, MastersValue } from "@turnmark/sdk/masters";
import type { PointsRequest, PointsValue } from "@turnmark/sdk/points";

export interface EngineOptions {
  /** Browser default: the packaged asset URL. Node: supply its bytes via fs. */
  wasm?: string | URL | ArrayBuffer | Uint8Array;
}
export interface Engine {
  readonly version: string;
  parseTime(input: unknown): number | null;
  convert(request: ConversionRequest): Result<ConversionValue>;
  adjustAltitude(request: AltitudeRequest): Result<AltitudeValue>;
  youth(request: YouthRequest): Result<YouthValue>;
  masters(request: MastersRequest): Result<MastersValue>;
  points(request: PointsRequest): Result<PointsValue>;
}

/** Initialize once explicitly; after this, every calculation is synchronous and offline. */
export async function createEngine(
  options: EngineOptions = {},
): Promise<Readonly<Engine>> {
  await initialize(
    options.wasm === undefined
      ? undefined
      : { module_or_path: options.wasm as InitInput },
  );
  function run<T>(operation: string, input: unknown): T {
    // JSON's treatment of undefined and non-finite values must preserve the
    // existing runtime validation boundary. Non-finite scalars become null.
    return JSON.parse(
      evaluate(operation, JSON.stringify(input) ?? "null"),
    ) as T;
  }
  return Object.freeze({
    version: engine_version(),
    parseTime: (input: unknown) =>
      typeof input === "string" ? run<number | null>("parse", input) : null,
    convert: (input: ConversionRequest) =>
      run<Result<ConversionValue>>("convert", input),
    adjustAltitude: (input: AltitudeRequest) =>
      run<Result<AltitudeValue>>("altitude", input),
    youth: (input: YouthRequest) => run<Result<YouthValue>>("youth", input),
    masters: (input: MastersRequest) =>
      run<Result<MastersValue>>("masters", input),
    points: (input: PointsRequest) => run<Result<PointsValue>>("points", input),
  });
}
