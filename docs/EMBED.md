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
publisher script or cross-origin resize messages. If a real publisher needs
automatic sizing later, an optional loader can be added without changing the
existing iframe contract.

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
while existing paths remain supported. There are no configurable messages,
parent callbacks, analytics keys or executable URL parameters in v1.

## Privacy and offline use

Calculations execute in the iframe after its static assets load. The widget
makes no calculation requests and does not access app preferences, saved swims,
local/session storage or IndexedDB. It does not set cookies, register a service
worker, message its parent or load third-party scripts. The hosting provider
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
manual fallback, theme preview, narrow layouts and accessibility in both themes.
Web-only/embed changes do not rebuild native apps.
