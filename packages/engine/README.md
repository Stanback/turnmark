# @turnmark/engine

Experimental, unpublished JavaScript library derived from `turnmark-core` Rust.
All calculations and semantic validation execute in WebAssembly. No network is
used after explicit initialization. GPL-3.0-or-later, as in the existing SDK.

Browser:

```ts
import { createEngine } from "@turnmark/engine";
const engine = await createEngine();
const result = engine.convert({
  swim: {
    time: "1:00",
    event: { distance: 100, stroke: "freestyle", course: "LCM" },
  },
  to: "SCY",
  table: "women",
});
```

The build must serve the packaged `.wasm` asset; supply `wasm: assetUrl` if your
bundler rewrites URLs. Node consumers supply bytes explicitly:

```ts
import { readFile } from "node:fs/promises";
import { createEngine } from "@turnmark/engine";
const wasm = await readFile(
  new URL(import.meta.resolve("@turnmark/engine/engine.wasm")),
);
const engine = await createEngine({ wasm });
```

The engine exposes `parseTime`, `convert`, `adjustAltitude`, `youth`, `masters`,
and `points`, using the existing SDK request/result contracts. Requests must be
plain JSON-compatible data. Typed Swift/Kotlin bindings are generated separately
from the same Rust crate; they do not use JSON as their application API.

This package temporarily imports TypeScript declarations from `@turnmark/sdk`;
those type imports are erased and execute no legacy calculation code. The web
app still uses the existing SDK while the shared-engine experiment is reviewed.
The migration must remove the TypeScript domain implementation before declaring
Rust the sole production authority. Neither package is published yet.
