<script lang="ts">
  import Icon from "../../src/lib/Icon.svelte";
  import {
    convertSwim,
    type Course,
    type Category,
    type Stroke,
  } from "@turnmark/sdk";
  import { conversionSource } from "@turnmark/sdk/conversion";
  const courses: Course[] = ["SCY", "SCM", "LCM"];
  const strokes: { value: Stroke; label: string }[] = [
    { value: "freestyle", label: "Freestyle" },
    { value: "backstroke", label: "Backstroke" },
    { value: "breaststroke", label: "Breaststroke" },
    { value: "butterfly", label: "Butterfly" },
    { value: "individual-medley", label: "Individual medley" },
  ];
  let time = $state("1:00.00");
  let course = $state<Course>("LCM");
  let stroke = $state<Stroke>("freestyle");
  let distance = $state(100);
  let table = $state<Category>("women");
  // These are selectable UI options; the engine decides support and mappings.
  const distances = $derived(
    stroke === "freestyle"
      ? course === "SCY"
        ? [50, 100, 200, 500, 1000, 1650]
        : [50, 100, 200, 400, 800, 1500]
      : stroke === "individual-medley"
        ? [100, 200, 400]
        : [50, 100, 200],
  );
  function reconcileDistance() {
    if (!distances.includes(distance)) distance = 100;
  }
  const results = $derived(
    courses.map((to) => ({
      to,
      result: convertSwim({
        swim: { time, event: { distance, stroke, course } },
        to,
        table,
      }),
    })),
  );
  const invalid = $derived(
    results.find((x) => x.result.status === "invalid")?.result,
  );
  const strokeLabel = $derived(strokes.find((x) => x.value === stroke)!.label);
  const kind = {
    swum: "Entered swim",
    published: "Published factor",
    derived: "Derived estimate",
  };
</script>

<div class="converter">
  <header>
    <h1>Swim time converter</h1>
    <p>SCY · SCM · LCM</p>
  </header>
  <div class="fields">
    <label class="time"
      >Entered time<input
        bind:value={time}
        aria-invalid={invalid?.status === "invalid"}
        aria-describedby="time-help"
        inputmode="decimal"
        autocomplete="off"
        maxlength="12"
        placeholder="1:02.45"
      /></label
    >
    <p id="time-help" class:invalid={invalid?.status === "invalid"}>
      {invalid?.status === "invalid"
        ? "Enter a positive time, such as 58.32 or 1:02.45 (up to 60:00)."
        : "Minutes : seconds . hundredths"}
    </p>
    <label class="wide-field"
      ><span class="field-caption"><Icon name={stroke} size={18} />Stroke</span
      ><span class="select-wrap"
        ><select bind:value={stroke} onchange={reconcileDistance}
          >{#each strokes as s}<option value={s.value}>{s.label}</option
            >{/each}</select
        ><Icon name="chevron" size={16} /></span
      ></label
    >
    <label
      ><span class="field-caption"
        ><Icon name="distance" size={18} />Distance</span
      ><span class="select-wrap"
        ><select bind:value={distance}
          >{#each distances as d}<option value={d}
              >{d} {course === "SCY" ? "yards" : "meters"}</option
            >{/each}</select
        ><Icon name="chevron" size={16} /></span
      ></label
    >
    <label
      >Entered course<span class="select-wrap"
        ><select bind:value={course} onchange={reconcileDistance}
          >{#each courses as c}<option>{c}</option>{/each}</select
        ><Icon name="chevron" size={16} /></span
      ></label
    >
    <label class="wide-field"
      >Published table<span class="select-wrap"
        ><select bind:value={table}
          ><option value="women">Women / girls</option><option value="men"
            >Men / boys</option
          ></select
        ><Icon name="chevron" size={16} /></span
      ></label
    >
  </div>
  <section
    class="results"
    aria-label="Course comparison"
    aria-live="polite"
    aria-atomic="true"
  >
    {#each results as { to, result }}
      <article class:entered={to === course}>
        {#if result.status === "available"}
          <div>
            <h2>
              {result.value.event.distance}
              {strokeLabel} · {result.value.event.course}
            </h2>
            <p>{kind[result.value.kind]}</p>
          </div>
          <strong>{result.value.time}</strong>
        {:else}
          <div>
            <h2>{to}</h2>
            <p>
              {result.status === "invalid"
                ? "Check the entered time"
                : "No published factor for this event"}
            </p>
          </div>
          <span aria-label="No result">—</span>
        {/if}
      </article>
    {/each}
  </section>
  <footer>
    <p>Converted times are estimates. Meet rules decide entry eligibility.</p>
    <div>
      <a href={conversionSource.url} target="_blank" rel="noopener noreferrer"
        >NCAA factors ↗</a
      ><a
        class="brand"
        href="https://turnmark.app/"
        target="_blank"
        rel="noopener noreferrer">Turnmark ↗</a
      >
    </div>
  </footer>
</div>

<style>
  :global(:root) {
    font-family: "DM Sans Variable", system-ui, sans-serif;
    color-scheme: light dark;
    --bg: var(--tm-color-canvas);
    --card: var(--tm-color-surface);
    --ink: var(--tm-color-text);
    --muted: var(--tm-color-text-muted);
    --line: var(--tm-color-border-subtle);
    --accent: var(--tm-color-accent);
    --entered: var(--tm-color-selected-surface);
  }
  :global(:root[data-theme="light"]) {
    color-scheme: light;
  }
  :global(:root[data-theme="dark"]) {
    color-scheme: dark;
  }
  :global(*) {
    box-sizing: border-box;
  }
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
  }
  .converter {
    max-width: 640px;
    margin: auto;
    padding: 22px;
  }
  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 20px;
  }
  h1 {
    font-size: 20px;
    line-height: 1.3;
    margin: 0;
    letter-spacing: -0.025em;
  }
  header p {
    margin: 0;
    font-size: 12px;
    white-space: nowrap;
    color: var(--muted);
  }
  .fields {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 15px 12px;
  }
  label {
    display: grid;
    gap: 7px;
    font-size: 13px;
    font-weight: 650;
    min-width: 0;
  }
  .field-caption {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  input,
  select {
    width: 100%;
    min-height: 44px;
    padding: 10px;
    border: 1px solid var(--tm-color-border-control);
    border-radius: var(--tm-radius-control);
    background: var(--tm-color-surface-input);
    color: var(--ink);
    font: inherit;
    font-size: 15px;
  }
  .select-wrap {
    position: relative;
  }
  select {
    appearance: none;
    padding-inline-end: 48px;
  }
  .select-wrap :global(svg) {
    position: absolute;
    right: 18px;
    top: 50%;
    transform: translateY(-50%) rotate(90deg);
    color: var(--muted);
    pointer-events: none;
  }
  @media (forced-colors: active) {
    select {
      appearance: auto;
    }
    .select-wrap :global(svg) {
      display: none;
    }
  }
  input {
    font-family: "DM Mono", monospace;
    font-size: 25px;
  }
  :is(input, select, a):focus-visible {
    outline: 3px solid var(--accent);
    outline-offset: 3px;
  }
  .time {
    grid-column: 1/-1;
  }
  #time-help {
    grid-column: 1/-1;
    margin: -7px 0 0;
    font-size: 12px;
    color: var(--muted);
    min-height: 16px;
  }
  #time-help.invalid {
    color: var(--tm-color-error);
    font-weight: 600;
  }
  input[aria-invalid="true"] {
    border-width: 2px;
    border-color: var(--tm-color-error);
  }
  .results {
    margin-top: 22px;
    display: grid;
    gap: 8px;
  }
  article {
    display: flex;
    gap: 12px;
    justify-content: space-between;
    align-items: center;
    padding: 13px;
    border: 1px solid var(--line);
    border-radius: var(--tm-radius-control);
    background: var(--card);
    min-height: 70px;
  }
  article.entered {
    background: var(--entered);
  }
  article.entered strong {
    color: var(--tm-color-result-highlight);
  }
  h2 {
    margin: 0;
    font-size: 14px;
    line-height: 1.4;
    font-weight: 650;
  }
  article p {
    margin: 4px 0 0;
    color: var(--muted);
    font-size: 12px;
  }
  article strong {
    font:
      500 clamp(18px, 5vw, 25px)/1.3 "DM Mono",
      monospace;
    white-space: nowrap;
  }
  footer {
    margin-top: 17px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.5;
  }
  footer p {
    margin: 0 0 12px;
  }
  footer div {
    display: flex;
    gap: 16px;
    justify-content: space-between;
  }
  a {
    color: var(--accent);
    text-underline-offset: 3px;
  }
  .brand {
    font-weight: 750;
  }
  @media (max-width: 440px) {
    .wide-field {
      grid-column: 1 / -1;
    }
  }
  @media (max-width: 360px) {
    .fields {
      grid-template-columns: minmax(0, 1fr);
    }
    .converter {
      padding: 16px;
    }
    header {
      display: block;
    }
    header p {
      margin-top: 5px;
    }
  }
</style>
