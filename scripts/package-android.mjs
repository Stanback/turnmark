import { spawnSync } from "node:child_process";
import { mkdir, copyFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";

process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const ndk = process.env.ANDROID_NDK_HOME;
if (!ndk)
  throw new Error(
    "Set ANDROID_NDK_HOME to the installed NDK (tested: 30.0.16248370)",
  );
const host = process.platform === "darwin" ? "darwin-x86_64" : "linux-x86_64";
const bin = resolve(ndk, "toolchains", "llvm", "prebuilt", host, "bin");
const profile = process.env.TURNMARK_NATIVE_PROFILE ?? "release";
if (!["release", "debug"].includes(profile))
  throw new Error("Use TURNMARK_NATIVE_PROFILE=release or debug");
function run(cmd, args, env = process.env) {
  const result = spawnSync(cmd, args, { stdio: "inherit", env });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
run(process.execPath, ["scripts/build-shared.mjs", "native"]);
for (const [target, abi, compiler] of [
  ["aarch64-linux-android", "arm64-v8a", "aarch64-linux-android26-clang"],
  ["x86_64-linux-android", "x86_64", "x86_64-linux-android26-clang"],
]) {
  const key = target.toUpperCase().replaceAll("-", "_");
  const env = {
    ...process.env,
    [`CARGO_TARGET_${key}_LINKER`]: join(bin, compiler),
    [`CC_${target.replaceAll("-", "_")}`]: join(bin, compiler),
    [`AR_${target.replaceAll("-", "_")}`]: join(bin, "llvm-ar"),
  };
  run(
    "cargo",
    [
      "build",
      "--locked",
      "-p",
      "turnmark-core",
      "--features",
      "native",
      ...(profile === "release" ? ["--release"] : []),
      "--target",
      target,
    ],
    env,
  );
  const destination = `bindings/generated/android/jniLibs/${abi}`;
  await mkdir(destination, { recursive: true });
  await copyFile(
    `target/${target}/${profile}/libturnmark_core.so`,
    `${destination}/libturnmark_core.so`,
  );
}
