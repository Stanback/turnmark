import { readFile } from "node:fs/promises";
import { createEngine } from "../dist/index.js";
await createEngine({
  wasm: await readFile(
    new URL("../dist/generated/turnmark_wasm_bg.wasm", import.meta.url),
  ),
});
