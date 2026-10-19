<script lang="ts">
  import {
    convertSwim,
    conversionMethods,
    type ConversionRequest,
    type ConversionMethod,
  } from "@turnmark/sdk/conversion";

  let {
    request,
    selected,
  }: {
    request: ConversionRequest;
    selected: ConversionMethod;
  } = $props();
  const comparisons = $derived(
    conversionMethods.map((method) => ({
      ...method,
      result: convertSwim({ ...request, method: method.id }),
    })),
  );
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
          {item.label}{#if item.id === selected}<span>Selected</span>{/if}
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
  {#if difference !== null}<p class="method-gap">
      Method difference: <strong>{difference}s</strong>
    </p>{/if}
  <p>
    These are different conversion rules, not a prediction range or confidence
    interval. Follow the method required by your meet.
  </p>
  <h3>What goes into the calculation</h3>
  <p>
    NCAA uses event- and category-specific metric-to-yards factors. Reverse
    conversions and SCM/LCM comparisons are derived from those factors. Colorado
    Timing uses event- and course-specific multipliers and fixed time offsets;
    it does not vary by age or category.
  </p>
  <p>
    Pool length changes distance and the number of turns and push-offs. Neither
    method measures your turn technique, endurance or individual development.
    Turns are not personalized inputs. Distance events map between 500/1000/1650
    yards and 400/800/1500 meters.
  </p>
  <p>
    Standards and points use your entered swim separately from these course
    estimates.
  </p>
  <ul>
    {#each comparisons as item}
      <li>
        <a href={item.source.url} target="_blank" rel="noopener noreferrer"
          >{item.label} source ↗</a
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
  ul {
    padding-inline-start: 20px;
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
