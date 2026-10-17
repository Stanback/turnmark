import { readdir, copyFile, mkdir } from "node:fs/promises";

// Generated copies keep the npm package self-contained. Edit only root data/.
const source = new URL("../data/", import.meta.url);
const destination = new URL("../packages/sdk/src/data/", import.meta.url);
await mkdir(destination, { recursive: true });
for (const name of await readdir(source)) {
  if (name.endsWith(".json")) {
    await copyFile(new URL(name, source), new URL(name, destination));
  }
}
