import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const sdk = process.env.ANDROID_HOME;
const ndk =
  process.env.ANDROID_NDK_HOME ?? (sdk && join(sdk, "ndk/30.0.16248370"));
if (!sdk || !ndk)
  throw new Error("Set ANDROID_HOME and, if needed, ANDROID_NDK_HOME");
const apk = resolve(
  "packages/android/build/outputs/apk/androidTest/debug/sdk-android-debug-androidTest.apk",
);
const host = process.platform === "darwin" ? "darwin-x86_64" : "linux-x86_64";
function run(command, args) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  assert.equal(
    result.status,
    0,
    `${command}: ${result.error ?? ""}\n${result.stderr}\n${result.stdout}`,
  );
  return result.stdout;
}
run(join(sdk, "build-tools/36.0.0/zipalign"), ["-c", "-P", "16", "4", apk]);
const temporary = await mkdtemp(join(tmpdir(), "turnmark-elf-"));
try {
  run("unzip", ["-q", apk, "lib/*/*.so", "-d", temporary]);
  const abis = await readdir(join(temporary, "lib"));
  assert.deepEqual(abis.sort(), ["arm64-v8a", "x86_64"]);
  for (const abi of abis) {
    const files = await readdir(join(temporary, "lib", abi));
    assert.ok(files.includes("libturnmark_core.so"), `Missing engine: ${abi}`);
    assert.ok(files.includes("libjnidispatch.so"), `Missing JNA: ${abi}`);
    for (const file of files) {
      const output = run(
        join(ndk, "toolchains/llvm/prebuilt", host, "bin/llvm-readelf"),
        ["-lW", join(temporary, "lib", abi, file)],
      );
      const loads = output
        .split("\n")
        .filter((line) => line.trim().startsWith("LOAD "));
      assert.ok(loads.length > 0);
      for (const line of loads)
        assert.ok(
          parseInt(line.trim().split(/\s+/).at(-1), 16) >= 16384,
          `${abi}/${file}: ${line}`,
        );
    }
  }
  console.log(
    "Android test APK: both 64-bit ABIs, Rust/JNA ELF alignment and 16 KB ZIP alignment passed",
  );
} finally {
  await rm(temporary, { recursive: true, force: true });
}
