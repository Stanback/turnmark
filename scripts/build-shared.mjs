import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const mode = process.argv[2] ?? "all";
if (!["all", "native", "wasm"].includes(mode))
  throw new Error("Use all, native or wasm");
function run(command, args) {
  const result = spawnSync(command, args, { stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
mkdirSync("bindings/generated", { recursive: true });
if (mode !== "wasm") {
  run("cargo", [
    "build",
    "--locked",
    "-p",
    "turnmark-core",
    "--features",
    "bindgen",
  ]);
  const library =
    process.platform === "darwin"
      ? "libturnmark_core.dylib"
      : "libturnmark_core.so";
  run("target/debug/uniffi-bindgen", [
    "generate",
    "--library",
    `target/debug/${library}`,
    "--language",
    "swift",
    "--language",
    "kotlin",
    "--out-dir",
    "bindings/generated",
    "--no-format",
  ]);
}
if (mode !== "native") {
  run("cargo", [
    "build",
    "--locked",
    "-p",
    "turnmark-wasm",
    "--release",
    "--target",
    "wasm32-unknown-unknown",
  ]);
  // Keep this CLI exactly aligned with the wasm-bindgen crate in Cargo.lock.
  const version = spawnSync("wasm-bindgen", ["--version"], {
    encoding: "utf8",
  });
  if (
    version.status !== 0 ||
    version.stdout.trim() !== "wasm-bindgen 0.2.129"
  ) {
    throw new Error(
      "Install cargo install wasm-bindgen-cli --version 0.2.129 --locked",
    );
  }
  run("wasm-bindgen", [
    "--target",
    "web",
    "--out-dir",
    "bindings/generated/wasm",
    "target/wasm32-unknown-unknown/release/turnmark_wasm.wasm",
  ]);
}
