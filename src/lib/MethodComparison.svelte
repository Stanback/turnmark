<script lang="ts">
  import { coloradoDistanceCaveat } from "./calculation-copy";
  import AltitudeComparison from "./AltitudeComparison.svelte";
  import {
    convertSwim,
    conversionMethods,
    type ConversionRequest,
    type ConversionMethod,
  } from "@turnmark/sdk/conversion";

  let {
    request,
    selected,
    adjusted = false,
  }: {
    request: ConversionRequest;
    selected: ConversionMethod;
    adjusted?: boolean;
  } = $props();
  const comparisons = $derived(
    conversionMethods.map((method) => ({
      ...method,
      result: convertSwim({ ...request, method: method.id }),
    })),
  );
  const chosen = $derived(comparisons.find((item) => item.id === selected)!);
  const difference = $derived.by(() => {
    const [a, b] = comparisons.map((item) => item.result);
    return a.status === "available" && b.status === "available"
      ? (Math.abs(a.value.hundredths - b.value.hundredths) / 100).toFixed(2)
      : null;
  });
</script>

<section
  class="method-comparison"
  aria-label={`Compare methods in ${request.to}`}
>
  <h3>Compare methods · {request.to}</h3>
  <dl>
    {#each comparisons as item}
      <div data-method={item.id}>
        <dt>
          {item.label.replace(" (default)", "")}{#if item.id === selected}<span
              >Selected</span
            >{/if}
        </dt>
        <dd>
          {#if item.result.status === "available"}
            <strong>{item.result.value.time}</strong>
            <small
              >{item.result.value.event.distance}
              {item.result.value.event.course === "SCY" ? "yd" : "m"} · {item
                .result.value.event.course}</small
            >
          {:else}
            <span
              >{item.result.status === "invalid"
                ? "Check the entered swim"
                : "Unavailable for this event"}</span
            >
          {/if}
        </dd>
      </div>
    {/each}
  </dl>
  {#if comparisons.some((item) => item.result.status === "available" && item.result.value.caveat)}<p
      class="distance-caveat"
    >
      {coloradoDistanceCaveat}
    </p>{/if}
  {#if difference !== null}<p class="method-gap">
      Method difference: <strong>{difference}s</strong>
    </p>{/if}
  <p>
    Two conversion rules, not a prediction range or confidence interval. Use the
    method required by your meet.
  </p>
  {#if request.elevation}<AltitudeComparison
      swim={request.swim}
      elevation={request.elevation}
      selected={request.altitudePolicy ?? "usa-swimming-altitude-2026"}
    />{/if}
  <h3>Why the times differ</h3>
  <div class="explanations">
    <div>
      <h4>NCAA</h4>
      <p>
        Published factors vary by event and category. Metric-to-yards values are
        direct; reverse and SCM/LCM comparisons use ratios.
      </p>
    </div>
    <div>
      <h4>Colorado Timing</h4>
      <p>
        Documented multipliers plus fixed time offsets. The formulas vary by
        event and course, not age or category.
      </p>
    </div>
    <div>
      <h4>Pool length</h4>
      <p>
        Shorter pools add turns and push-offs. These rules do not measure your
        technique, endurance or individual development.
      </p>
    </div>
    <div>
      <h4>Distance events</h4>
      <p>500, 1000 and 1650 yards map to 400, 800 and 1500 meters.</p>
    </div>
  </div>
  <p>
    Standards and points use the entered swim, before altitude or course
    conversion.
  </p>
  <h3>Selected calculation · {chosen.label.replace(" (default)", "")}</h3>
  <div class="result-explanation">
    {#if chosen.result.status === "available"}
      {#if chosen.result.value.kind === "swum"}
        <p>
          {adjusted ||
          (chosen.result.value.altitude?.value.adjustmentSeconds ?? 0) > 0
            ? `Your sea-level estimate in ${request.to}.`
            : "Your entered swim, exactly as timed."}
        </p>
      {:else}
        <p>
          {request.swim.event.course} → {request.to}:
          <strong
            >× {chosen.result.value.factor.toFixed(5)}{chosen.result.value
              .offsetSeconds
              ? ` ${chosen.result.value.offsetSeconds > 0 ? "+" : "−"} ${Math.abs(chosen.result.value.offsetSeconds).toFixed(2)}s`
              : ""}</strong
          >. {chosen.id === "ncaa-2025-27"
            ? chosen.result.value.kind === "published"
              ? "Published NCAA factor."
              : "Derived from NCAA metric-to-yards factors."
            : "Colorado Timing formula."} Truncated to hundredths.
        </p>
        <p class="formula-note">
          The factor is rounded here for display. Calculations use the full
          rule.
        </p>
      {/if}
    {:else}<p>Unavailable for this event and destination.</p>{/if}
  </div>
  <ul class="sources">
    {#each comparisons as item}
      <li>
        <a href={item.source.url} target="_blank" rel="noopener noreferrer"
          >{item.id === "ncaa-2025-27"
            ? "NCAA rules"
            : "Colorado Timing formulas"} ↗</a
        >
      </li>
    {/each}
  </ul>
</section>

<style>
  .method-comparison {
    margin-top: 18px;
    color: var(--tm-color-text-muted);
    font-size: 0.875rem;
    line-height: 1.6;
  }
  h3 {
    color: var(--tm-color-text);
    font: inherit;
    font-weight: 650;
    margin: 20px 0 10px;
  }
  dl {
    margin: 0;
  }
  dl > div {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 8px 20px;
    padding: 10px 0;
    border-bottom: 1px solid var(--tm-color-border-subtle);
  }
  dt {
    color: var(--tm-color-text);
  }
  dt span {
    display: inline-block;
    margin-inline-start: 8px;
    font-size: 0.75rem;
    color: var(--tm-color-accent);
  }
  dd {
    display: grid;
    justify-items: end;
    margin: 0;
  }
  dd strong {
    color: var(--tm-color-text);
    font-variant-numeric: tabular-nums;
    font-size: 1.125rem;
  }
  dd small {
    font-size: 0.75rem;
  }
  p {
    margin: 12px 0;
  }
  .method-gap strong {
    color: var(--tm-color-text);
  }
  .formula-note {
    font-size: 0.75rem;
  }
  .explanations {
    display: grid;
    gap: 16px;
  }
  h4 {
    margin: 0 0 4px;
    color: var(--tm-color-text);
    font: inherit;
    font-weight: 650;
  }
  .explanations p {
    margin: 0;
  }
  .sources {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 20px;
    list-style: none;
    padding: 0;
    margin-top: 20px;
  }
  a {
    color: var(--tm-color-accent);
    text-underline-offset: 3px;
  }
  a:focus-visible {
    outline: 2px solid var(--tm-color-accent);
    outline-offset: 3px;
  }
</style>
