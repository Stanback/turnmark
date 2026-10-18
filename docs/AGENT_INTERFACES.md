# MCP and WebMCP plan

Status: the local stdio server and stateless Cloudflare Worker adapter are now
implemented in `packages/mcp` and `packages/mcp-worker`. See [MCP setup, checks
and deployment](MCP.md). The dedicated Worker and protected credential
are configured, with deployment through passing main CI. npm publication
remains pending. WebMCP remains a separate planned adapter.

## One engine, two access paths

Expose Turnmark calculations to assistants through an MCP server and to browser
agents through WebMCP on the website. Both call `@turnmark/sdk`, which executes
the Rust core. Reuse one set of tool definitions, argument schemas and result
mappings across adapters; keep semantic validation, formulas, datasets and
provenance in Rust. Generate schemas from the core contract where practical,
and verify any protocol-specific mapping against the portable fixtures.

| MCP tool              | SDK responsibility                                                |
| --------------------- | ----------------------------------------------------------------- |
| `convert_swim`        | Convert an entered swim to an explicit target course.             |
| `adjust_altitude`     | Adjust an entered swim at an explicit elevation/unit.             |
| `get_youth_standards` | Published targets for the selected event, age group and category. |
| `get_masters_target`  | Published USMS target or a precise missing-data result.           |
| `get_world_points`    | Points and next milestone for the original metric swim.           |
| `get_sources`         | Method/data editions, coverage and attribution from SDK metadata. |

Inputs retain the SDK's actual distances, clock strings, explicit categories,
courses and editions. Results preserve `available` / `unavailable` / `invalid`,
reason codes, precision, published-versus-derived labels and provenance.
Missing times stay missing. A qualifying benchmark is not entry eligibility.
The adapters translate protocol envelopes and errors, without changing answers.

## MCP server

Start with a local Node server over stdio, loading the packaged Wasm bytes once
before serving requests. Calculations work offline without opening a browser.
Use the official MCP SDK; keep stdout for protocol messages and logs on stderr.
Expose input/output schemas and structured results with a short text rendering.
Calculation tools are read-only and idempotent; they receive explicit inputs
and do not read a person's browser history or saved swims.
[MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools),
[transports](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports).

Future personal-history access is a separate adapter and permission boundary,
using the versioned record schema proposed in the [offline history plan](MEET_HISTORY.md).
It must explicitly select a local store/import file and distinguish reads from
reviewable writes. The planned public calculation service does not expose a
person's device history.

`packages/mcp` owns the server and launch/configuration examples, without
another engine or dataset copy.

### Hosting sequence

1. The offline stdio server loads packaged Wasm; no hosted service is required.
2. `packages/mcp-worker` uses the same tools over stateless Streamable HTTP at
   `mcp.turnmark.app`. Deployment status is tracked in [MCP.md](MCP.md).
3. The SDK accepts a bundled precompiled Wasm module for Workers. Actual clients
   exercise both transports and protocol modes against the same portable
   fixtures. The public service has explicit request limits and no user storage;
   verify live discovery and calculations after deployment.

Cloudflare documents stateless MCP handlers and Streamable HTTP, Worker Custom
Domains, and precompiled Wasm modules.
[Remote MCP on Workers](https://developers.cloudflare.com/agents/model-context-protocol/guides/remote-mcp-server/),
[Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/),
[Workers Wasm](https://developers.cloudflare.com/workers/runtime-apis/webassembly/).

Static hosting serves HTML/JavaScript/Wasm, so it can serve the website and
its browser-executed WebMCP integration on supporting browsers. It cannot run
the remote MCP HTTP endpoint. Local MCP distribution can still use the GitHub
repository and release assets. Turnmark's website now uses its own static-assets
Worker; the MCP Worker is a separate service and deployment boundary.
[GitHub Pages hosting model](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

## WebMCP integration

Register the same calculation tools in the active web page after SDK startup.
Reuse the initialized Wasm instance and return results without changing form
values, navigating, saving history or sharing. Any future tool that changes
the user's application state should have a separate, explicit contract.

WebMCP is an evolving Community Group draft, not a W3C Standard. The October 16,
2026 draft exposes `document.modelContext`; do not freeze older examples using
`navigator.modelContext` into the architecture. Chrome's early-preview guidance
describes both declarative forms and imperative JavaScript tools. Turnmark's
existing SDK makes imperative registration the first candidate, subject to
verification against the browser build used for the prototype.
[Current draft](https://webmachinelearning.github.io/webmcp/),
[Chrome preview](https://developer.chrome.com/blog/webmcp-epp).

Keep the registration/lifecycle adapter in a provisional `packages/webmcp`.
Feature-detect the supported API in secure contexts, clean up registrations on
teardown, and handle duplicate registration and initialization failure. The
ordinary calculator must remain fully usable when WebMCP is absent or blocked.
Start on the first-party website; publisher iframe exposure needs separate
origin/permissions testing and explicit publisher configuration.

## Acceptance before release

- Run the portable cases through actual MCP tool discovery/calls and the browser
  registration path, comparing structured outputs and provenance with the SDK.
- Test invalid arguments, absent targets, unsupported events, unavailable Wasm,
  cancellation, duplicate registration and cleanup. Preserve the distinction
  between protocol failures and domain outcomes.
- Install the MCP package outside the monorepo; demonstrate a documented client
  connection and offline execution with bundled assets.
- Verify WebMCP discovery/invocation on a supported browser build and normal
  calculator behavior without the API, including offline reload. Record tested
  browser versions and preview requirements rather than promising broad support.
- Share reusable tool contracts in `packages/agent-tools` only when both adapters
  need them. Version tool schemas with the SDK and data editions; changes to
  protocol dependencies must not alter the underlying numerical results.
