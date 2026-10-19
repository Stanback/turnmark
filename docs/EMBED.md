# Embed the Turnmark converter

The hosted v1 widget uses
`https://turnmark.app/embed/v1/`; no npm install, API key or parent-page script is
required. The dedicated [widget setup page](https://turnmark.app/embed/) provides
appearance selection, a live preview, and copyable HTML. Find it under **Widget
setup** in the website footer.

```html
<iframe
  src="https://turnmark.app/embed/v1/"
  title="Swim time converter by Turnmark"
  width="100%"
  height="820"
  loading="lazy"
  referrerpolicy="strict-origin-when-cross-origin"
  style="max-width:640px;border:0;border-radius:16px;"
></iframe>
```

Paste into your CMS's custom HTML/embed block. A restrictive publisher Content
Security Policy must allow `https://turnmark.app` in `frame-src`. The default
appearance follows the reader's device; add `?theme=light` or `?theme=dark` to
choose explicitly. The frame is responsive down to 320 CSS pixels. Its height
can be increased to suit the page or larger text; content scrolls within the
frame when necessary. It does not resize or style the publisher's page.

The setup page fits its own preview to the content because both documents are
on Turnmark's origin. The copied public embed stays a plain iframe, with no
publisher script. It also emits an optional height-only layout signal described
below; publishers decide whether to use it. The setup page does not require or
configure a resizing integration.

## Behavior and attribution

The widget converts the entered event across SCY, SCM and LCM. It uses the
public `@turnmark/sdk` API and bundled Rust/Wasm core, with no duplicate formulas
or numerical tables. Each result shows its actual destination distance/course
and whether it is the entered swim, a published-factor conversion or a derived
estimate. Unsupported conversions remain unavailable. Times are estimates;
meet rules determine eligibility. The source link and Turnmark credit stay
visible. Standards, points, altitude and personal history remain in the full app.

The implementation is GPL-3.0-or-later, with source in this repository.
Preserve its license and source attribution when redistributing code. Numerical
sources remain credited to their respective owners.

`apps/embed/` contains the widget consumer; `embed/v1/index.html` is its HTML
entry. The web build emits the app, setup page and widget with shared versioned assets.
`apps/embed/Setup.svelte` is pre-rendered for the setup page; only the calculator
iframe loads the SDK/Wasm.
The hosted `/embed/v1/` path gets compatible updates; it is not an immutable
snapshot. Breaking configuration/embedding changes need a new versioned path
while existing paths remain supported. There are no parent commands, configurable callbacks, analytics keys or
executable URL parameters in v1.

## Optional height signal for integrations

After loading, an embedded widget sends its immediate parent a `postMessage`
when its content height changes, including responsive and text reflows:

```json
{ "type": "turnmark:resize", "version": 1, "height": 672 }
```

`height` is a positive integer in CSS pixels, rounded up to fit the widget's
content. The value above is illustrative. Messages are coalesced to an animation
frame and identical heights are suppressed. A plain iframe retains its configured
height and scrolling; this signal does not modify the publisher's page. The
widget listens for no parent commands. Because a publisher can suppress its
referrer, the child sends this non-sensitive layout metadata with target origin
`*`. It never includes the entered time, event, category or result.

Publishers opting in must check both the exact widget origin and the particular
iframe's `contentWindow`, then validate and bound the height. For example, with
`id="turnmark-widget"` on the iframe:

```js
const frame = document.getElementById("turnmark-widget");
window.addEventListener("message", (event) => {
  if (
    event.origin !== "https://turnmark.app" ||
    event.source !== frame.contentWindow
  )
    return;
  const message = event.data;
  if (
    !message ||
    message.type !== "turnmark:resize" ||
    message.version !== 1 ||
    !Number.isSafeInteger(message.height) ||
    message.height < 240 ||
    message.height > 4000
  )
    return;
  frame.style.height = `${message.height}px`;
});
```

The receiving site owns this optional code and its size bounds. Keep a usable
fallback iframe height; messages can be unavailable if the widget cannot load.

## Privacy and offline use

Calculations execute in the iframe after its static assets load. The widget
makes no calculation requests and does not access app preferences, saved comparisons,
local/session storage or IndexedDB. It does not set cookies, register a service
worker or load third-party scripts. Its parent-facing layout message contains
only a type, contract version and content height, never calculation inputs or
results. The hosting provider
still receives ordinary requests for HTML/assets and may process standard
request metadata. Publisher analytics and network policies are outside the
widget's control.

An initial network load is required on a publisher's site. Once loaded,
calculations continue without a connection. A previously installed Turnmark PWA
can cache the widget's route and assets too; the widget's own entry does not
register offline storage inside third-party frames. Reader inputs are not
encoded into the embed URL or shared with the publisher.

## Validation

`npm run check`, `npm test`, `npm run test:browser` and `npm run test:production`
cover the web consumer. Production widget tests use an actual second-origin
publisher fixture and the local Cloudflare static runtime. They verify source
examples and destination distances, unavailable/invalid outcomes, no storage
access, offline calculations after load, failed engine loading, copy success and
manual fallback, theme preview, narrow layouts, height-only cross-origin layout
signals and accessibility in both themes.
Web-only/embed changes do not rebuild native apps.
