import { spawnSync } from "node:child_process";
import { cp, mkdir, rm, copyFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
function run(command, args, cwd) {
  const result = spawnSync(command, args, { stdio: "inherit", cwd });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
run(process.execPath, ["scripts/build-shared.mjs", "wasm"]);
run(process.execPath, ["scripts/generate-sdk-data.mjs"]);
await mkdir("packages/sdk/src/generated", { recursive: true });
await cp("bindings/generated/wasm", "packages/sdk/src/generated", {
  recursive: true,
});
await rm("packages/sdk/dist", { recursive: true, force: true });
run(process.execPath, [
  "node_modules/typescript/bin/tsc",
  "-p",
  "packages/sdk/tsconfig.json",
]);
await cp("bindings/generated/wasm", "packages/sdk/dist/generated", {
  recursive: true,
});
await copyFile("LICENSE", "packages/sdk/LICENSE");
