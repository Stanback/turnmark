<script lang="ts">
  import Icon from "./Icon.svelte";
  import { getMastersEntry, mastersSource } from "./masters";
  import {
    mastersAges,
    eventLabel,
    formatTime,
    type Course,
    type Category,
    type Stroke,
  } from "./swim";
  let {
    age = $bindable("18-24"),
    course,
    category,
    distance,
    stroke,
    time,
  }: {
    age?: string;
    course: Course;
    category: Category;
    distance: number;
    stroke: Stroke;
    time: number | null;
  } = $props();
  const entry = $derived(
    getMastersEntry(age, category, course, distance, stroke),
  );
  const target = $derived(entry ?? null);
  const gap = $derived(time !== null && target !== null ? time - target : null);
</script>

<div class="masters-panel">
  <h2 id="standards-title">USMS National Qualifying Times</h2>
  <p class="masters-description">
    Adult targets from the published 2026 Spring (SCY) and Summer (LCM)
    Nationals tables.
  </p>
  <div class="standards-controls">
    <label for="masters-age"
      >Age group<span class="select-wrap standards-select"
        ><select id="masters-age" bind:value={age}
          >{#each mastersAges as group}<option value={group}
              >{group.replaceAll("-", "–")}</option
            >{/each}</select
        ><Icon name="chevron" size={16} /></span
      ></label
    ><span class="standards-edition"
      >2026<span>
        · {course === "SCY"
          ? "Spring · SCY"
          : course === "LCM"
            ? "Summer · LCM"
            : "SCY / LCM"}</span
      ></span
    >
  </div>
  <div class="masters-context">
    {eventLabel(distance, course, stroke)} · {course} · {category === "women"
      ? "Women"
      : "Men"} · {age.replaceAll("-", "–")}
  </div>
  {#if target !== null && time !== null}
    <div class="masters-comparison">
      <div>
        <span>Your entered swim</span><strong>{formatTime(time)}</strong>
      </div>
      <Icon name="arrow" size={18} />
      <div>
        <span>2026 NQT target</span><strong data-testid="masters-target"
          >{formatTime(target)}</strong
        >
      </div>
    </div>
    <div class="masters-status" class:met={gap !== null && gap <= 0}>
      <Icon name={gap !== null && gap <= 0 ? "check" : "clock"} size={19} />
      <div>
        <strong
          >{gap !== null && gap <= 0
            ? "At or faster than the NQT"
            : "Time to the NQT target"}</strong
        >
        <p>
          {gap === 0
            ? "Your entered time matches the published target."
            : `${Math.abs(gap!).toFixed(2)}s ${gap! < 0 ? "faster than the published target." : "to reach the published target."}`}
        </p>
      </div>
    </div>
  {:else}<div class="masters-empty">
      <Icon name="info" size={22} />
      <h3>
        {course === "SCM"
          ? "No SCM Nationals target"
          : age === "85+"
            ? "No NQT for ages 85+"
            : time === null
              ? "Enter a valid swim time"
              : entry === null
                ? "USMS lists ‘NO TIME’ for this selection"
                : "No published target for this selection"}
      </h3>
      <p>
        {course === "SCM"
          ? "These USMS tables cover SCY and LCM. Select the course you actually swam; converted estimates aren’t used for this comparison."
          : age === "85+"
            ? "USMS does not set National Qualifying Times for age groups 85 and older."
            : entry === null
              ? "The published table has no qualifying time for this event and age group. There’s no target to compare against."
              : "Missing targets remain blank. Try another event or age group."}
      </p>
    </div>{/if}
  <p class="masters-note">
    Compared with your entered time. Course and altitude estimates are not used.
    This is a 2026 benchmark, not confirmation of entry eligibility;
    meet-specific rules and exceptions apply.
  </p>
  <a
    class="points-source"
    href={mastersSource.url}
    target="_blank"
    rel="noreferrer"
    >USMS tables & entry guidance <Icon name="external" size={13} /></a
  >
</div>
