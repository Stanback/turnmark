import { readFile } from "node:fs/promises";
import { createEngine as initialize, type EngineOptions } from "./index.js";

export * from "./index.js";

/** Node entry point: load the bundled Wasm from disk, without a network request. */
export async function createEngine(options: EngineOptions = {}) {
  return initialize({
    ...options,
    wasm:
      options.wasm ??
      (await readFile(
        new URL("./generated/turnmark_wasm_bg.wasm", import.meta.url),
      )),
  });
}
