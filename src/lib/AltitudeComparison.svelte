<script lang="ts">
  import {
    adjustAltitude,
    altitudePolicies,
    type Swim,
    type Elevation,
    type AltitudePolicy,
  } from "@turnmark/sdk/conversion";
  let {
    swim,
    elevation,
    selected,
  }: { swim: Swim; elevation: Elevation; selected: AltitudePolicy } = $props();
  const rows = $derived(
    altitudePolicies.map((policy) => ({
      ...policy,
      result: adjustAltitude({ swim, elevation, policy: policy.id }),
    })),
  );
</script>

<section
  class="altitude-policy-comparison"
  aria-label="Compare altitude policies"
>
  <h3>Sea-level estimates</h3>
  <p>Entered swim: <strong>{swim.time || "—"}</strong></p>
  <dl>
    {#each rows as row}<div>
        <dt>
          {row.label.replace(" (default)", "")}{#if row.id === selected}<small
              >Selected</small
            >{/if}
        </dt>
        <dd>
          {#if row.result.status === "available"}<strong
              >{row.result.value.adjustedTime}</strong
            ><small>−{row.result.value.adjustmentSeconds.toFixed(2)}s</small
            >{:else}Check time and elevation{/if}
        </dd>
      </div>{/each}
  </dl>
  <p>
    Deduct altitude first, then convert courses. Below 3,000 ft, or where the
    table has no deduction, the time stays unchanged. Use the policy required by
    your meet.
  </p>
  <div class="sources">
    {#each rows as row}<a href={row.source.url} target="_blank" rel="noreferrer"
        >{row.id === "usa-swimming-altitude-2026"
          ? "USA Swimming"
          : "NCAA altitude"} ↗</a
      >{/each}
  </div>
</section>

<style>
  section {
    font-size: 0.875rem;
    color: var(--tm-color-text-muted);
  }
  h3 {
    font-size: 0.875rem;
    color: var(--tm-color-text);
    margin: 0 0 0.5rem;
  }
  p {
    margin: 0.5rem 0;
    line-height: 1.6;
  }
  dl {
    margin: 0.5rem 0;
  }
  dl > div {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--tm-color-border-subtle);
  }
  dt,
  dd {
    margin: 0;
    min-width: 0;
  }
  dd {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  strong {
    color: var(--tm-color-text);
  }
  small {
    display: block;
    margin-top: 0.25rem;
  }
  dt small {
    color: var(--tm-color-accent);
  }
  .sources {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  a {
    color: var(--tm-color-accent);
  }
  @media (max-width: 340px) {
    dl > div {
      flex-direction: column;
      gap: 0.4rem;
    }
    dd {
      text-align: left;
    }
  }
</style>
