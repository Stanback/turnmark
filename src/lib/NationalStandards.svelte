<script lang="ts">
  import {
    assessSwimBenchmark,
    getNationalStandardPrograms,
    type StandardSystem,
  } from "@turnmark/sdk";
  import { swimRequest, type SwimState, eventLabel } from "./swim";
  import Icon from "./Icon.svelte";
  let {
    system,
    age = $bindable("18 & under"),
    form,
  }: { system: StandardSystem; age?: string; form: SwimState } = $props();
  const program = $derived(
    getNationalStandardPrograms().find((p) => p.system === system)!,
  );
  const outcome = $derived(
    assessSwimBenchmark({
      swim: swimRequest(form),
      table: form.category,
      age: program.ages.length ? age : "",
      system,
    }),
  );
</script>

<div class="national-panel">
  <div class="standards-title-row">
    <div>
      <h2 id="standards-title">{program.title}</h2>
      <p>{program.scope}</p>
    </div>
    {#if program.ages.length}<label for="national-age"
        >Age table<span class="select-wrap standards-select"
          ><select id="national-age" bind:value={age}
            >{#each program.ages as group}<option value={group}>{group}</option
              >{/each}</select
          ><Icon name="chevron" size={16} /></span
        ></label
      >{/if}
  </div>
  <p class="context">
    {eventLabel(form.distance, form.course, form.stroke)} · {form.course} · {form.category ===
    "women"
      ? "Women / girls"
      : "Men / boys"} · Your entered swim
  </p>
  {#if outcome.status === "available"}
    <div class="targets" aria-label="Published time thresholds">
      {#each outcome.value.targets as target}<div
          class="target"
          class:met={target.met}
          data-testid={`national-target-${target.label}`}
        >
          <span
            ><strong>{target.label}</strong><small
              >{target.met
                ? "Time threshold met"
                : `${target.gapSeconds.toFixed(2)}s to this threshold`}</small
            ></span
          >
          <span class="clock"
            >{#if target.met}<Icon
                name="check"
                size={18}
              />{/if}{target.time}</span
          >
        </div>{/each}
    </div>
  {:else if outcome.status === "unavailable"}
    <p class="empty" role="status">
      No published target for this {outcome.reason === "course-not-supported"
        ? "course"
        : "event"}. Select the course you actually swam; converted estimates
      aren’t used.
    </p>
  {:else}<p class="empty">
      Enter a valid swim time to compare with these thresholds.
    </p>{/if}
  <p class="note">{program.note}</p>
  {#if outcome.status !== "invalid"}<a
      class="points-source"
      href={outcome.provenance.url}
      target="_blank"
      rel="noreferrer"
      >Published {outcome.provenance.revision} source<Icon
        name="external"
        size={13}
      /></a
    >{/if}
</div>

<style>
  .national-panel {
    display: grid;
    gap: var(--tm-space-16);
  }
  h2,
  p {
    margin: 0;
  }
  .standards-title-row p,
  .context,
  .note,
  .empty {
    color: var(--muted);
    font-size: 0.875rem;
    line-height: 1.65;
  }
  .standards-title-row p {
    margin-top: var(--tm-space-8);
  }
  label {
    display: grid;
    gap: var(--tm-space-8);
    font-size: 0.875rem;
    font-weight: 650;
  }
  .targets {
    border-block: 1px solid var(--line);
  }
  .target {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--tm-space-16);
    padding-block: var(--tm-space-16);
  }
  .target + .target {
    border-top: 1px solid var(--line);
  }
  .target > span:first-child {
    display: grid;
    gap: var(--tm-space-8);
  }
  small {
    font-size: 0.8125rem;
    color: var(--muted);
  }
  .clock {
    display: flex;
    align-items: center;
    gap: var(--tm-space-8);
    font-family: var(--heading);
    font-size: clamp(1.25rem, 5vw, 2rem);
    font-weight: 750;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .met .clock {
    color: var(--highlight);
  }
  .note {
    max-width: 75ch;
  }
</style>
