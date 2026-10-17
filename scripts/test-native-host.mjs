import { spawnSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const mode = process.argv[2] ?? "swift";
function run(command, args) {
  const result = spawnSync(command, args, { stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
run(process.execPath, ["scripts/build-shared.mjs", "native"]);
await mkdir("target/conformance", { recursive: true });
if (mode === "swift") {
  run("swiftc", [
    "bindings/generated/turnmark_core.swift",
    "bindings/tests/main.swift",
    "-I",
    "bindings/generated",
    "-Xcc",
    "-fmodule-map-file=bindings/generated/turnmark_coreFFI.modulemap",
    "-L",
    "target/debug",
    "-lturnmark_core",
    "-Xlinker",
    "-rpath",
    "-Xlinker",
    "@executable_path/../debug",
    "-o",
    "target/conformance/swift-test",
  ]);
} else if (mode === "kotlin") {
  if (!process.env.JNA_JAR)
    throw new Error(
      "Set JNA_JAR to JNA 5.19.1's jar; kotlinc and Java 21 must be installed",
    );
  run("kotlinc", [
    "bindings/generated/uniffi/turnmark_core/turnmark_core.kt",
    "bindings/tests/Main.kt",
    "-cp",
    process.env.JNA_JAR,
    "-include-runtime",
    "-d",
    "target/conformance/kotlin-test.jar",
  ]);
} else throw new Error("Use swift or kotlin");
run(process.execPath, ["scripts/test-shared.mjs", mode]);
