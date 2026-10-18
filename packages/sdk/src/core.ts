import initialize, {
  evaluate,
  engine_version,
  type InitInput,
} from "./generated/turnmark_wasm.js";

export interface EngineOptions {
  /** Default: packaged asset URL in browsers. The /node entry loads local bytes. */
  wasm?: string | URL | ArrayBuffer | Uint8Array;
}
let ready: Promise<void> | undefined;
let initialized = false;
export function initializeEngine(options: EngineOptions): Promise<void> {
  return (ready ??= initialize(
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
}
export function engineVersion(): string {
  return engine_version();
}

/** Serialization only. Calculation validation and all formulas live in Rust. */
export function callCore<T>(operation: string, input: unknown): T {
  if (!initialized)
    throw new Error(
      "Initialize the Turnmark SDK with await createEngine() before calling calculations.",
    );
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
export function compatibility<T>(operation: string, args: unknown[]): T {
  return callCore("compat", { operation, args });
}
