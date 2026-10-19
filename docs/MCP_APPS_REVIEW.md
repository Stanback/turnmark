# MCP Apps implementation review

Implemented October 18, 2026 using the official MCP Apps extension and pinned
`@modelcontextprotocol/ext-apps@2.0.3`. This is an inline conversion card, not a
replacement transport or the older MCP-UI action/resource convention.
The [research](MCP_APPS.md) records the protocol/host decisions and primary sources.

## User experience

The card displays the destination event/course/category and returned time, its
original performance, published/derived kind, and source edition. Time and target
course are editable; an explicit Update comparison calls `convert_swim` through
the host. Original event/course/category stay fixed to the request. No factors,
numerical tables or Wasm execute in the view. A 500 yd→400 m conversion uses the
returned event. Other tools retain text/structured results.

| Light, 680 px | Dark, 320 px |
| --- | --- |
| <img src="screenshots/mcp-card-light.png" width="460" alt="Light MCP conversion card with original swim and editable comparison"> | <img src="screenshots/mcp-card-dark-narrow.png" width="260" alt="Dark narrow MCP conversion card"> |

The shared generated colors and canonical wave give it Turnmark's identity.
All palette roles come from `design/turnmark.tokens.json` through the generated
CSS bundled into the resource. Keep future UI states on that contract; the host
can change layout, typography and accessibility behavior without introducing an
independent color palette. The deeper navy controls match web/widget/native.
Controls use the host/browser's native behavior and system typography. Host
appearance changes apply live; automatic sizing reports content height. At 200%
text, the clock fits one line and surrounding copy wraps normally:

<img src="screenshots/mcp-card-large-text.png" width="280" alt="MCP card at 200 percent text with readable single-line clock and expanded source">

## Boundaries

- Six existing read-only tools and schemas stay intact. Only `convert_swim`
  advertises `_meta.ui.resourceUri`; the one static resource is registered
  independently of initialization capabilities for stateless HTTP compatibility.
- URI `ui://turnmark/conversion/0.2.0.html`, MIME
  `text/html;profile=mcp-app`. Change the resource version for later view releases.
  Both list/read carry CSP with empty connect/resource/frame domain lists.
- One self-contained HTML asset, including the official bridge SDK: approximately
  656 KB raw / 139 KB gzip, under an enforced 750,000-byte build budget. No CDN,
  font request, direct fetch, local storage, history access or nested iframe.
  Installed third-party license notices are derived from the bundle graph and
  included in both the HTML resource and npm archive.
- Worker dry run: approximately 2,283 KiB total / 468 KiB gzip. This fits the
  [Workers Free compressed-script allowance](https://developers.cloudflare.com/workers/platform/limits/).
  Local workerd startup profiling measured a 42.2 ms window / 22.5 ms active
  sample time; that is module startup, not an edge request CPU measurement.
  Existing body limits, approximate per-IP/aggregate rate limits, Free plan,
  Origin policy and protected deployment credentials remain unchanged.
- Updates are explicit, single-flight, abortable and time-bounded. Generation
  checks discard late responses. Failed requests preserve the committed result.
  Model context updates follow a successful edit; denied context updates explain
  how to continue. No automatic new conversation message or retry loop.
- Text uses DOM textContent, source links go through host approval, and the test
  host forwards only the intended conversion tool. The real host owns capability,
  tool approval, sandbox and link policies; this card cannot grant itself access.

## Verification evidence

`npm run test:mcp` builds and types the card, then runs:

- Packed stdio and local workerd Streamable HTTP, in both supported protocol
  modes, with and without Apps capabilities: eight combinations. Each checks
  42 exact SDK-equal outcomes, eight malformed requests, all tools, cancellation,
  resource discovery/read/unknown URI, MIME, immutable URI, CSP and text fallback.
- Packed stdio runs outside the workspace with network disabled. A second fresh
  installation against **registry SDK 0.1.0** also runs both protocol modes,
  full result fixtures and resource reads with runtime fetch disabled.
- Actual local Worker bindings enforce request/body/Origin/rate/aggregate limits.
- Official AppBridge in Chromium with both a real stdio MCP server and a local
  Workers Streamable HTTP server, an opaque-origin
  `allow-scripts` sandbox and strict CSP: rendering, resize, keyboard update,
  theme changes, 320 px width, 200% text, explicit cancellation/late response,
  denied tool/context/link calls, malformed/invalid/unavailable outcomes, hostile strings,
  mapped destination event and independent card instances. Axe reports no
  violations or untested-frame finding. No external requests or page errors.
- Svelte/TypeScript checks, web unit tests, 18 production-runtime tests and
  affected-check selection tests pass. UI/build/harness edits select MCP/core;
  shared tokens also select web; ordinary card edits do not rebuild native apps.

## Acceptance and release status

The browser screenshots are from the official bridge test host, **not** ChatGPT,
Claude or VS Code. Specific desktop/mobile host versions still need a real-host
visual/approval/context acceptance pass. Protocol compatibility does not establish rendering in
every host or directory approval. Local profiling does not establish edge CPU
usage; verify production responses after deployment and monitor actual Free
limits without enabling a paid plan.

The source/server/UI version is MCP **0.2.0**. Public npm MCP **0.1.0** remains the
published text-only version until a separately authenticated release. A tested
0.2.0 tarball can be retained with `npm run pack:mcp` under ignored `release/`,
with a SHA-256 checksum. The main-only manual release workflow accepts a package
choice and keeps SDK/MCP versions independent. The SDK stays at
published 0.1.0 for this adapter release. Follow [SDK releases](SDK_RELEASES.md)
for the protected trusted-publisher setup; do not add an npm token to CI or
replace an existing registry version.
