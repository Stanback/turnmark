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

<nav class="page-width" aria-label="Documentation navigation">
  <a href="/">← Turnmark calculator</a>
  <a href="/mcp/">MCP setup</a>
  <a href="/docs/embed.md">Markdown reference</a>
</nav>
<main class="embed-section page-width" aria-labelledby="embed-title">
  <div>
    <h1 id="embed-title">Embed the swim time converter</h1>
    <p>
      A compact calculator for articles, club sites, and meet pages. Paste this
      HTML into an embed or custom HTML block.
    </p>
  </div>
  <div class="embed-controls">
    <label for="embed-theme">Appearance</label><select
      id="embed-theme"
      bind:value={theme}
      onchange={() => {
        copied = false;
        failed = false;
      }}
      ><option value="auto">Match the reader’s device</option><option
        value="light">Light</option
      ><option value="dark">Dark</option></select
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
    <ol>
      <li>
        Choose whether the widget follows the reader’s device or stays light or
        dark.
      </li>
      <li>
        Copy the HTML into a custom HTML or embed block in your editor. In
        WordPress, use a Custom HTML block.
      </li>
      <li>
        Preview and publish the page. Some editors require permission to use
        iframes.
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
      Convert between SCY, SCM and LCM with the same Rust-backed SDK as
      Turnmark. Results retain their destination distance, source and
      published-factor or derived-estimate label. Missing factors stay
      unavailable.
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
<footer class="page-width">
  <a href="/llms.txt">Agent documentation index</a> ·
  <a href="https://github.com/Stanback/turnmark">Source code</a>
</footer>

<style>
  :global(html) {
    color-scheme: light dark;
    background: #f5f8fa;
    color: #163348;
    --line: #cad7df;
    --muted: #4e687a;
    --embed-surface: #fff;
  }
  :global(body) {
    margin: 0;
    font:
      16px/1.65 "DM Sans Variable",
      system-ui,
      sans-serif;
  }
  :global(*),
  :global(*::before),
  :global(*::after) {
    box-sizing: border-box;
  }
  .page-width {
    width: min(100% - 48px, 760px);
    margin-inline: auto;
  }
  nav {
    display: flex;
    flex-wrap: wrap;
    gap: 12px 22px;
    padding-top: 32px;
  }
  a {
    color: #00687c;
    text-underline-offset: 3px;
  }
  a:focus-visible,
  button:focus-visible,
  select:focus-visible,
  summary:focus-visible {
    outline: 3px solid #1388ae;
    outline-offset: 4px;
  }
  .embed-section {
    padding-block: 36px;
  }
  h1 {
    font-size: clamp(2rem, 6vw, 3rem);
    line-height: 1.15;
    letter-spacing: -0.035em;
    margin: 0 0 22px;
  }
  h2 {
    margin: 0 0 12px;
  }
  p {
    line-height: 1.7;
    max-width: 740px;
  }
  .embed-controls {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    margin: 22px 0;
  }
  select {
    max-width: 100%;
    padding: 10px 12px;
    background: var(--embed-surface);
    color: inherit;
    border: 1px solid var(--line);
    border-radius: 8px;
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
    background: var(--embed-surface);
    color: inherit;
    border: 1px solid var(--line);
    border-radius: 10px;
    font:
      13px/1.7 "DM Mono",
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
    border: 1px solid var(--line);
    border-radius: 16px;
    margin-top: 12px;
  }
  textarea:focus-visible {
    outline: 3px solid #1388ae;
    outline-offset: 4px;
  }
  .primary-button {
    border: 0;
    border-radius: 8px;
    padding: 12px 18px;
    background: #00687c;
    color: #fff;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .setup-notes {
    margin-top: 36px;
    border-top: 1px solid var(--line);
    padding-top: 28px;
  }
  .setup-notes h2:not(:first-child) {
    margin-top: 28px;
  }
  ol {
    padding-left: 24px;
  }
  li + li {
    margin-top: 8px;
  }
  code {
    font-size: 0.9em;
    overflow-wrap: anywhere;
  }
  footer {
    padding-block: 0 40px;
    font-size: 14px;
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
  @media (prefers-color-scheme: dark) {
    :global(html) {
      background: #0b202b;
      color: #dce9f1;
      --line: #344e60;
      --muted: #b3c9d7;
      --embed-surface: #172f43;
    }
    a {
      color: #9cdaea;
    }
    .primary-button {
      background: #9cdaea;
      color: #0b202b;
    }
  }
  .embed-note {
    font-size: 14px;
    color: var(--muted);
    margin-top: 22px;
  }
</style>
