import { cp, mkdir, copyFile } from "node:fs/promises";
// Generated declarations are needed while compiling the tiny typed adapter.
await mkdir("src/generated", { recursive: true });
await mkdir("dist/generated", { recursive: true });
await cp("../../bindings/generated/wasm/", "src/generated/", {
  recursive: true,
});
await cp("../../bindings/generated/wasm/", "dist/generated/", {
  recursive: true,
});
await copyFile("../../LICENSE", "LICENSE");
