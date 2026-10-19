<script lang="ts">
  import { site } from "../../src/data/site";
  let theme = $state("auto");
  let copied = $state(false);
  let failed = $state(false);
  const url = $derived(
    `${site.url}embed/v1/${theme === "auto" ? "" : `?theme=${theme}`}`,
  );
  const code = $derived(
    `<iframe src="${url}" title="Swim time converter by Turnmark" width="100%" height="740" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" style="max-width:640px;border:0;border-radius:16px;"></iframe>`,
  );
  async function copy() {
    copied = false;
    failed = false;
    try {
      await navigator.clipboard.writeText(code);
      copied = true;
    } catch {
      failed = true;
    }
  }
</script>

<header class="docs-header docs-width">
  <a class="docs-brand" href="/" aria-label="Turnmark home"
    ><span class="docs-brand-icon"
      ><svg
        viewBox="0 0 24 24"
        width="23"
        height="23"
        fill="none"
        stroke="currentColor"
        stroke-width="1.65"
        stroke-linecap="round"
        aria-hidden="true"><path d="M3 8q4-6 9 0t9 0M3 16q4-6 9 0t9 0" /></svg
      ></span
    >turnmark<span>.</span></a
  >
  <nav aria-label="Documentation navigation">
    <a href="/">Calculator</a>
    <a href="/mcp/">MCP setup</a>
    <a href="/docs/embed.md">Markdown reference</a>
  </nav>
</header>
<main class="embed-section docs-width" aria-labelledby="embed-title">
  <div>
    <h1 id="embed-title">Embed the swim time converter</h1>
    <p>
      A compact calculator for articles, club sites, and meet pages. Paste this
      HTML into an embed or custom HTML block.
    </p>
  </div>
  <div class="embed-controls">
    <label for="embed-theme">Appearance</label><span class="docs-select"
      ><select
        id="embed-theme"
        bind:value={theme}
        onchange={() => {
          copied = false;
          failed = false;
        }}
        ><option value="auto">Match the reader’s device</option><option
          value="light">Light</option
        ><option value="dark">Dark</option></select
      ><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"
        ><path
          d="m4 6 4 4 4-4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        /></svg
      ></span
    >
  </div>
  <label class="code-label" for="embed-code">Embed code</label>
  <textarea
    id="embed-code"
    readonly
    value={code}
    rows="4"
    spellcheck="false"
    onclick={(event) => event.currentTarget.select()}></textarea>
  <div class="embed-actions">
    <button class="primary-button" onclick={copy}
      >{copied ? "Copied" : "Copy embed code"}</button
    ><span role="status"
      >{copied
        ? "Embed code copied."
        : failed
          ? "Select the code above and copy it manually."
          : ""}</span
    >
  </div>
  <details open>
    <summary>Preview the converter</summary><iframe
      src={`/embed/v1/${theme === "auto" ? "" : `?theme=${theme}`}`}
      title="Swim time converter preview"
      width="100%"
      height="740"
      loading="lazy"
    ></iframe>
  </details>
  <p class="embed-note">
    Free to embed, with a Turnmark credit and source link. Calculations run in
    the reader’s browser; the widget doesn’t access your swim history. No API
    key or publisher JavaScript required. <a href="/docs/embed.md"
      >Full widget reference</a
    >
  </p>
  <section class="setup-notes" aria-labelledby="setup-notes-title">
    <h2 id="setup-notes-title">Add it to a page</h2>
    <ol class="setup-steps">
      <li>
        <strong>Choose an appearance</strong>
        Follow the reader’s device, or keep the widget light or dark.
      </li>
      <li>
        <strong>Paste the embed code</strong>
        Copy the HTML into a custom HTML or embed block in your editor. In WordPress,
        use a Custom HTML block.
      </li>
      <li>
        <strong>Preview and publish</strong>
        Check the converter in your page. Some editors require permission to use iframes.
      </li>
    </ol>
    <p>
      The widget adapts to the space available, down to 320 pixels wide.
      Increase the iframe’s <code>height</code> if your layout or larger text needs
      more room.
    </p>
    <p>
      If your site uses a Content Security Policy, allow <code
        >https://turnmark.app</code
      >
      in <code>frame-src</code>. No API key, npm install or parent-page script
      is needed.
    </p>
    <h2>What readers get</h2>
    <p>
      Convert between SCY, SCM and LCM. Results retain their destination
      distance, source and published-factor or derived-estimate label. Missing
      factors stay unavailable.
    </p>
    <p>
      Calculations continue offline after the widget loads. It does not read
      saved swims, browser storage or the publisher’s page. Hosting still
      involves ordinary network requests for the initial assets.
    </p>
    <p>
      Keep the Turnmark credit and source link visible. Standards, points,
      altitude and personal history are available in the <a href="/"
        >full calculator</a
      >.
    </p>
  </section>
</main>
<footer class="docs-width">
  <a href="https://github.com/Stanback/turnmark">Source code</a>
</footer>

<style>
  .embed-controls {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    margin: 28px 0;
  }
  .docs-select {
    position: relative;
    max-width: 100%;
  }
  .docs-select svg {
    position: absolute;
    inset-inline-end: 20px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
  }
  select {
    appearance: none;
    max-width: 100%;
    padding: 12px 52px 12px 16px;
    background: var(--docs-surface);
    color: inherit;
    border: 1px solid var(--docs-control);
    border-radius: 10px;
    font: inherit;
  }
  .code-label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
  }
  textarea {
    display: block;
    width: 100%;
    min-height: 130px;
    padding: 16px;
    resize: vertical;
    background: var(--docs-surface);
    color: inherit;
    border: 1px solid var(--docs-control);
    border-radius: 10px;
    font:
      13px/1.7 ui-monospace,
      monospace;
  }
  .embed-actions {
    display: flex;
    gap: 16px;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 16px;
  }
  .embed-actions span {
    font-size: 14px;
  }
  details {
    margin-top: 26px;
  }
  summary {
    cursor: pointer;
    padding: 12px 0;
    font-weight: 600;
  }
  iframe {
    display: block;
    max-width: 640px;
    border: 1px solid var(--docs-line);
    border-radius: 16px;
    margin-top: 12px;
  }
  .primary-button {
    border: 0;
    border-radius: 10px;
    padding: 12px 18px;
    background: var(--docs-action);
    color: #062b38;
    font: inherit;
    font-weight: 650;
    cursor: pointer;
  }
  .setup-notes {
    margin-top: 36px;
    border-top: 1px solid var(--docs-line);
    padding-top: 28px;
  }
  .setup-notes h2:first-child {
    margin-top: 0;
  }
  .embed-note {
    font-size: 14px;
    color: var(--docs-muted);
    margin-top: 22px;
  }
  @media (max-width: 367px) {
    iframe {
      width: calc(100% + 48px);
      max-width: none;
      margin-inline: -24px;
      border-inline: 0;
      border-radius: 0;
    }
  }
  @media (forced-colors: active) {
    select {
      appearance: auto;
      padding-inline-end: 16px;
    }
    .docs-select svg {
      display: none;
    }
  }
</style>
