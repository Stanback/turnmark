<script lang="ts">
  import { site } from "../data/site";
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

<section class="embed-section page-width" aria-labelledby="embed-title">
  <div>
    <h2 id="embed-title">Add the converter to your site</h2>
    <p>
      A compact calculator for articles, club sites, and meet pages. Paste this
      HTML into an embed or custom HTML block.
    </p>
  </div>
  <div class="embed-controls">
    <label for="embed-theme">Appearance</label><select
      id="embed-theme"
      bind:value={theme}
      onchange={() => (copied = false)}
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
  <details>
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
    key or publisher JavaScript required. <a
      href="https://github.com/Stanback/turnmark/blob/main/docs/EMBED.md"
      target="_blank"
      rel="noreferrer">Setup details ↗</a
    >
  </p>
</section>

<style>
  .embed-section {
    padding-block: 50px;
    border-top: 1px solid var(--line);
    --embed-surface: #fff;
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
  :global([data-theme="dark"]) .embed-section {
    --embed-surface: #172f43;
  }
  .embed-note {
    font-size: 14px;
    color: var(--muted);
    margin-top: 22px;
  }
</style>
