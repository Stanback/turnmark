# Web cleanup review

Actual production-build captures, using sample local conversion history. The
main README showcase follows native Standards & points work.

- Recent conversions fills the desktop standards row. Its entries scroll within
  the card; the last entry remains reachable by keyboard. Youth, masters and
  points views are checked. At 900 pixels and below, history uses page scrolling.
- Sources/methodology and FAQ share a desktop column boundary and aligned starts.
- Widget and MCP setup use one stylesheet, generated Turnmark palette and fonts,
  760-pixel content width, responsive brand header and keyboard focus treatment.
  Both remain readable without JavaScript. MCP is still static HTML; processing
  its CSS with Vite does not add a client application or change the MCP service.
- Widget setup has an inset dropdown chevron and a spaced three-step list.

Validation: 119 unit tests; 51 CI-selection tests; 33 browser tests (one existing
mobile-only skip); 17 production tests, including no-script rendering, offline
navigation and light/dark accessibility audits. Svelte/TypeScript checks pass
without warnings. The paired native result-gradient follow-up has its own
[visual review](NATIVE_VISUAL_REVIEW.md#result-gradient-follow-up) and passes all
16 iOS and 17 Android tests. The numerical engine is unchanged.

![Desktop history and standards row](screenshots/web-cleanup-grid-dark.png)

![Aligned methodology and FAQ](screenshots/web-cleanup-columns-dark.png)

| Widget setup, light                                             | MCP setup, dark                                          |
| --------------------------------------------------------------- | -------------------------------------------------------- |
| ![Widget setup](screenshots/web-cleanup-widget-setup-light.png) | ![MCP setup](screenshots/web-cleanup-mcp-setup-dark.png) |

![Narrow widget setup, dark](screenshots/web-cleanup-widget-setup-dark.png)
