<script lang="ts">
  import { elevationDisplay } from "./elevation-display";

  import {
    altitudePolicies,
    type Converter,
    type Swim,
    type Elevation,
    type AltitudePolicy,
  } from "@turnmark/sdk/converter";
  let {
    converter,
    swim,
    elevation = $bindable(),
    policy = $bindable("usa-swimming-altitude-2026"),
  }: {
    converter: Pick<Converter, "adjustAltitude">;
    swim: Swim;
    elevation?: Elevation;
    policy?: AltitudePolicy;
  } = $props();
  const id = $props.id();
  const preview = $derived(
    elevation ? converter.adjustAltitude({ swim, elevation, policy }) : null,
  );
</script>

<section class="altitude-controls" aria-label="Altitude adjustment">
  <h3>Altitude adjustment</h3>
  <div class="body">
    <label class="enable"
      ><input
        type="checkbox"
        checked={elevation !== undefined}
        onchange={(e) =>
          (elevation = e.currentTarget.checked
            ? { value: 0, unit: "feet" }
            : undefined)}
      />Adjust for altitude</label
    >
    {#if elevation}
      <label for={`${id}-elevation`}>Pool elevation</label>
      <input
        id={`${id}-elevation`}
        type="number"
        min="0"
        max={elevation.unit === "feet" ? 20000 : 6096}
        step={elevation.unit === "feet" ? 1 : "any"}
        value={elevation.value}
        oninput={(e) =>
          (elevation = { ...elevation!, value: e.currentTarget.valueAsNumber })}
      />
      <label for={`${id}-unit`}>Elevation unit</label>
      <select
        id={`${id}-unit`}
        value={elevation.unit}
        onchange={(e) => {
          const unit = e.currentTarget.value as Elevation["unit"];
          elevation = {
            value: elevationDisplay(elevation!.value, elevation!.unit, unit),
            unit,
          };
        }}
        ><option value="feet">Feet</option><option value="meters">Meters</option
        ></select
      >
      <label for={`${id}-policy`}>Altitude policy</label>
      <select id={`${id}-policy`} bind:value={policy}
        >{#each altitudePolicies as item}<option value={item.id}
            >{item.label}</option
          >{/each}</select
      >
      <p>
        {#if preview?.status === "available"}Altitude deduction: −{preview.value.adjustmentSeconds.toFixed(
            2,
          )}s. Sea-level estimate: {preview.value.adjustedTime}.{/if} Applied before
        course conversion. Meters are rounded to the nearest foot.
      </p>
    {/if}
  </div>
</section>

<style>
  section {
    border-top: 1px solid var(--tm-color-border-subtle);
    margin-top: 1rem;
    padding-top: 1rem;
    color: var(--tm-color-text);
  }
  h3 {
    margin: 0;
    font-size: 0.875rem;
  }
  .body {
    display: grid;
    gap: 0.75rem;
    padding-top: 0.75rem;
  }
  label {
    font-weight: 600;
  }
  input:not([type="checkbox"]),
  select {
    box-sizing: border-box;
    width: 100%;
    min-width: 0;
    min-height: 2.75rem;
    font: inherit;
    color: var(--tm-color-text);
    background: var(--tm-color-surface-input);
    border: 1px solid var(--tm-color-border-control);
    border-radius: var(--tm-radius-control);
    padding: 0.6rem 0.8rem;
  }
  input[type="checkbox"] {
    accent-color: var(--tm-color-accent);
    width: 1.125rem;
    height: 1.125rem;
  }
  .enable {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    min-height: 2.75rem;
  }
  p {
    font-size: 0.875rem;
    color: var(--tm-color-text-muted);
  }
  :focus-visible {
    outline: 2px solid var(--tm-color-accent);
    outline-offset: 3px;
  }
</style>
