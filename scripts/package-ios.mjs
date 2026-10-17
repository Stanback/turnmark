import { spawnSync } from "node:child_process";
import { mkdir, copyFile, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
if (process.platform !== "darwin")
  throw new Error("iOS packaging requires Xcode on macOS");
function run(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
run(process.execPath, ["scripts/build-shared.mjs", "native"]);
const profile = process.env.TURNMARK_NATIVE_PROFILE ?? "release";
if (!["release", "debug"].includes(profile))
  throw new Error("Use TURNMARK_NATIVE_PROFILE=release or debug");
for (const target of [
  "aarch64-apple-ios",
  "aarch64-apple-ios-sim",
  "x86_64-apple-ios",
]) {
  run("cargo", [
    "build",
    "--locked",
    "-p",
    "turnmark-core",
    "--features",
    "native",
    ...(profile === "release" ? ["--release"] : []),
    "--target",
    target,
  ]);
}
await mkdir("target/ios-headers", { recursive: true });
await mkdir("packages/swift/Sources/TurnmarkCore", { recursive: true });
await mkdir("packages/swift/Tests/TurnmarkCoreTests/Fixtures", {
  recursive: true,
});
await copyFile(
  "bindings/generated/turnmark_coreFFI.h",
  "target/ios-headers/turnmark_coreFFI.h",
);
await copyFile(
  "bindings/generated/turnmark_coreFFI.modulemap",
  "target/ios-headers/module.modulemap",
);
await copyFile(
  "bindings/generated/turnmark_core.swift",
  "packages/swift/Sources/TurnmarkCore/turnmark_core.swift",
);
await copyFile(
  "fixtures/sdk-conformance.json",
  "packages/swift/Tests/TurnmarkCoreTests/Fixtures/sdk-conformance.json",
);
const output = "packages/swift/Artifacts/TurnmarkCoreFFI.xcframework";
await rm(output, { recursive: true, force: true });
await mkdir("target/ios-simulator", { recursive: true });
run("lipo", [
  "-create",
  `target/aarch64-apple-ios-sim/${profile}/libturnmark_core.a`,
  `target/x86_64-apple-ios/${profile}/libturnmark_core.a`,
  "-output",
  "target/ios-simulator/libturnmark_core.a",
]);
run("xcodebuild", [
  "-create-xcframework",
  "-library",
  `target/aarch64-apple-ios/${profile}/libturnmark_core.a`,
  "-headers",
  "target/ios-headers",
  "-library",
  "target/ios-simulator/libturnmark_core.a",
  "-headers",
  "target/ios-headers",
  "-output",
  output,
]);
