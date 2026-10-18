# Turnmark MCP

Read-only swimming calculations over local stdio, using `@turnmark/sdk` and its
bundled Rust/Wasm engine. Version 0.1.0 is not published yet. Node 22.12+ is
required; calculations run offline after installation, without Rust or a browser.

## Local connection

Build from the repository root with `npm ci && npm run build --workspace @turnmark/mcp`.
Use an absolute Node executable and checkout path in your MCP client's config:

```json
{
  "mcpServers": {
    "turnmark": {
      "command": "/absolute/path/to/node",
      "args": ["/absolute/path/to/turnmark/packages/mcp/dist/cli.js"]
    }
  }
}
```

The server loads its bundled engine before accepting requests. Stdout contains
MCP messages only; diagnostics go to stderr. No runtime downloads are needed.
Once both npm packages are released, install `@turnmark/mcp@0.1.0` and use its
`turnmark-mcp` executable. Until then, test/install the SDK and MCP tarballs
together; the package test exercises exactly that outside the monorepo.

## Tools

| Tool                  | Inputs                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| `convert_swim`        | Entered `swim`, destination `to`, category `table`, optional `method`. |
| `adjust_altitude`     | Entered `swim`, `elevation` with value and feet/meters unit.           |
| `get_youth_standards` | `event`, `table`, age-group key, optional `edition`.                   |
| `get_masters_target`  | `event`, `table`, age-group key, optional `edition`.                   |
| `get_world_points`    | Raw entered `swim`, `table`, optional `edition`.                       |
| `get_sources`         | Empty object; returns engine version, editions and attribution.        |

A swim has a clock string `time` and an `event` with actual `distance`, full
`stroke` name and `course` (`SCY`, `SCM`, `LCM`). `table` is `women` or `men`,
following published source categories. Example `convert_swim` arguments:

```json
{
  "swim": {
    "time": "2:16.71",
    "event": { "distance": 200, "stroke": "breaststroke", "course": "LCM" }
  },
  "to": "SCY",
  "table": "men"
}
```

This returns `1:57.29` with published-factor provenance. Results contain both
`structuredContent` and the same JSON in text content. Domain outcomes retain
`available`, `unavailable` or `invalid`, event/course context, reason codes,
published/derived kinds and provenance. Missing published targets stay missing;
benchmarks do not certify meet-entry eligibility. Malformed tool arguments and
unknown tools are protocol/tool errors; valid-shaped requests with unsupported
editions, invalid clock strings or uncovered events reach Rust unchanged.
The adapter contains no calculation formulas or copied numerical tables.

## Remote endpoint

The paired Worker is prepared for `https://mcp.turnmark.app/mcp` using stateless
Streamable HTTP. It is not deployed yet. A remote client supplies explicit
calculation inputs to Cloudflare; the local stdio option keeps them on-device.
Neither server reads saved swims, profiles, arbitrary files, URLs or browser
state. There are no history writes or accounts. WebMCP is separate future work.

See [deployment and checks](https://github.com/Stanback/turnmark/blob/main/docs/MCP.md).
GPL-3.0-or-later applies; preserve the SDK's source attribution.
