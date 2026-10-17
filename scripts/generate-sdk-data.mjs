import { readFile, writeFile, mkdir } from "node:fs/promises";

// Only source metadata is needed in JS; all numerical tables are embedded in Rust.
const source = new URL("../data/", import.meta.url);
const destination = new URL("../packages/sdk/src/generated/", import.meta.url);
await mkdir(destination, { recursive: true });
const read = async (name) =>
  JSON.parse(await readFile(new URL(`${name}.json`, source), "utf8"));
const youth = await read("standards"),
  masters = await read("masters"),
  points = await read("points"),
  conversions = await read("conversions");
await writeFile(
  new URL("metadata.json", destination),
  JSON.stringify({
    youth: { source: youth.source },
    masters: { source: masters.source, ages: masters.ages },
    points: { source: points.source, validity: points.validity },
    conversions: {
      conversionSource: conversions.conversionSource,
      altitudeSource: conversions.altitudeSource,
    },
    sources: await read("sources"),
  }) + "\n",
);
