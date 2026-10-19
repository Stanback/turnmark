# Turnmark MCP

Read-only swimming calculations over local stdio, using `@turnmark/sdk` and its
bundled Rust/Wasm engine. Version `0.2.0` includes an interactive MCP Apps
conversion card for compatible hosts, alongside the existing text and structured
results. Node 22.12+ is required; calculations run offline after installation,
without Rust or a browser.

## Hosted connection

Add a remote MCP server in your assistant or editor with these settings:

- URL: `https://mcp.turnmark.app/mcp`
- Transport: Streamable HTTP
- Authentication: none; no API key, account or npm installation is required.

For a portable `.mcp.json` in current VS Code/Copilot:

```json
{
  "mcpServers": {
    "turnmark": {
      "type": "http",
      "url": "https://mcp.turnmark.app/mcp"
    }
  }
}
```

Client configuration formats differ. VS Code's editor-specific `.vscode/mcp.json`
uses `servers` instead of `mcpServers`; see its
[configuration guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers).
After connecting, list the tools and try: “Convert a men's 200 m LCM breaststroke
time of 2:16.71 to SCY, and show the source and result kind.”

The endpoint is MCP, not a REST calculator or browser page. Opening it in a
browser sends GET and returns `405`; use an MCP client. The hostname's root
GET returns health/version information. The service is public and rate limited:
on `429`, honor `Retry-After` rather than retrying in a tight loop. A `503` can
mean temporary unavailability; the local stdio option remains available.

Remote inputs are processed by Cloudflare. Send only explicit calculation
inputs; the server has no accounts, saved-swim access or write tools. For local
calculation inputs, use the offline stdio connection below.

## Local connection

Install in a project with `npm install @turnmark/mcp@0.2.0`. Use an absolute
Node executable and installed package path in your MCP client's config:

```json
{
  "mcpServers": {
    "turnmark": {
      "command": "/absolute/path/to/node",
      "args": [
        "/absolute/path/to/project/node_modules/@turnmark/mcp/dist/cli.js"
      ]
    }
  }
}
```

The server loads its bundled engine before accepting requests. Stdout contains
MCP messages only; diagnostics go to stderr. No runtime downloads are needed.
The package also provides the `turnmark-mcp` executable. A source checkout can
build it with `npm ci && npm run build --workspace @turnmark/mcp`; use that
checkout's `packages/mcp/dist/cli.js` path instead. See the repository's
[development setup](https://github.com/Stanback/turnmark/blob/main/CONTRIBUTING.md)
for the Rust/Wasm build toolchain. Installed npm packages need no Rust toolchain.

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

The paired Worker uses `https://mcp.turnmark.app/mcp` with stateless
Streamable HTTP. A remote client supplies explicit
calculation inputs to Cloudflare; the local stdio option keeps them on-device.
Neither server reads saved swims, profiles, arbitrary files, URLs or browser
state. There are no history writes or accounts. WebMCP is separate future work.

See [deployment and checks](https://github.com/Stanback/turnmark/blob/main/docs/MCP.md).
The website publishes this reference at <https://turnmark.app/mcp/index.md>,
with a [quick start](https://turnmark.app/mcp/) and
[documentation index for agents](https://turnmark.app/llms.txt).
GPL-3.0-or-later applies; preserve the SDK's source attribution.

## Interactive conversion card (MCP Apps)

The hosted server advertises an official MCP Apps conversion card on
`convert_swim`. In a compatible host, the result shows its destination event,
original swim, published/derived kind and source edition. Edit the time or
comparison course, then choose **Update comparison**. Each update calls the
same read-only server tool; no conversion math runs in the card. This makes one
explicit request per update rather than sending a request for every keystroke.

The card uses the host's light/dark appearance, reports its size, and needs no
outbound network, nested frame, local storage or special device permissions.
Source links go through the host's link permission. User edits update the
conversation context when the host permits it; otherwise the card explains
that the change needs to be mentioned in your next message. It never sends a
new chat message automatically or accesses personal swim history.

Clients without MCP Apps continue to receive the same text and structured
results. There is no separate UI endpoint to configure: use the same stdio
server or Streamable HTTP URL. The immutable resource is
`ui://turnmark/conversion/0.2.0.html`, served as
`text/html;profile=mcp-app`. Local Apps require package `0.2.0` or later;
package `0.1.0` provides text and structured tools.

Verified with the official AppBridge in an opaque browser sandbox and real
tool calls over both stdio and local Workers Streamable HTTP.
Specific versions of ChatGPT, Claude and VS Code have **not** been visually
verified in this release; rendering depends on the client and surface. See the
[implementation review](https://github.com/Stanback/turnmark/blob/main/docs/MCP_APPS_REVIEW.md).
