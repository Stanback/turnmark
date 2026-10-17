<script lang="ts">
  import { onMount } from "svelte";
  import Icon from "./lib/Icon.svelte";
  import Pool from "./lib/Pool.svelte";
  import Masters from "./lib/Masters.svelte";
  import Install from "./lib/Install.svelte";
  import Theme from "./lib/Theme.svelte";
  import { site, faqs } from "./data/site";
  import { readPreferences, type SwimPreferences } from "./lib/preferences";
  import {
    worldPoints,
    worldPointsContext,
    pointsSource,
    pointsValidity,
  } from "./lib/points";
  import { altitudeSource, conversionSource } from "./data/conversions";
  import { standardsSource } from "@turnmark/sdk/youth";
  import {
    courses,
    courseInfo,
    strokes,
    ages,
    levels,
    defaultState,
    parseTime,
    formatTime,
    convert,
    eventDistances,
    eventDistance,
    eventLabel,
    availableEvent,
    altitudeAdjustment,
    getStandards,
    standardStatus,
    ladderPosition,
    stateHash,
    readState,
    csvCell,
    type Course,
    type Stroke,
    type SwimState,
  } from "./lib/swim";

  let form = $state<SwimState>({ ...defaultState });
  let focus = $state<Course>("LCM");
  let toast = $state("");
  let saved = $state<{ id: string; form: SwimState }[]>([]);
  let toastTimer: ReturnType<typeof setTimeout>;
  let mounted = $state(false);
  let elevationUnit = $state<"ft" | "m">("ft");
  let elevationOpen = $state(false);
  type HistoryEntry = {
    id: string;
    form: SwimState;
    target: Course;
    createdAt: number;
  };
  let conversions = $state<HistoryEntry[]>([]);
  let historyFilter = $state<Stroke | "all">("all");
  let activeSection = $state("converter");
  let standardMode = $state<"targets" | "points">("targets");
  $effect(() => {
    if (form.altitude > 0) elevationOpen = true;
  });
  $effect(() => {
    if (!mounted || !altitudeValid) return;
    const preferences: SwimPreferences = {
      age: form.age,
      mastersAge: form.mastersAge,
      standardSystem: form.standardSystem,
      category: form.category,
      course: form.course,
      altitude: form.altitude,
      elevationUnit,
      standardMode,
    };
    try {
      localStorage.setItem("turnmark-preferences", JSON.stringify(preferences));
    } catch {
      /* Preferences still work in this tab when storage is unavailable. */
    }
  });
  let lastRecorded = "";
  const filteredHistory = $derived(
    conversions.filter(
      (x) => historyFilter === "all" || x.form.stroke === historyFilter,
    ),
  );
  $effect(() => {
    const target = focus;
    const hash = `${stateHash(form)}|${target}`;
    if (!mounted || error || hash === lastRecorded) return;
    const snapshot = { ...form };
    const timer = setTimeout(() => recordConversion(snapshot, target), 1400);
    return () => clearTimeout(timer);
  });
  const time = $derived(parseTime(form.time));
  const points = $derived(
    worldPoints(time, form.course, form.distance, form.stroke, form.category),
  );

  const pointContext = $derived(
    worldPointsContext(
      time,
      form.course,
      form.distance,
      form.stroke,
      form.category,
    ),
  );

  const altitudeValid = $derived(
    Number.isInteger(form.altitude) &&
      form.altitude >= 0 &&
      form.altitude <= 20000,
  );
  const elevationInput = $derived(
    Number.isFinite(form.altitude)
      ? elevationUnit === "ft"
        ? form.altitude
        : Number((form.altitude * 0.3048).toFixed(1))
      : undefined,
  );
  const elevationLabel = $derived(
    altitudeValid
      ? `${Number(elevationInput).toLocaleString(undefined, { maximumFractionDigits: 1 })} ${elevationUnit}`
      : "",
  );
  function setElevation(value: number | undefined) {
    if (value === undefined || !Number.isFinite(value)) form.altitude = NaN;
    else if (elevationUnit === "ft") form.altitude = value;
    else if (value < 0) form.altitude = -1;
    else if (value > 6096) form.altitude = 20001;
    else form.altitude = Math.round(value / 0.3048);
  }
  const adjustment = $derived(
    altitudeValid ? altitudeAdjustment(form.distance, form.altitude) : 0,
  );
  const correctedTime = $derived(
    time !== null && time > adjustment && altitudeValid
      ? time - adjustment
      : null,
  );
  const results = $derived(
    courses.map((course) => ({
      course,
      ...convert(
        correctedTime ?? 0,
        form.stroke,
        form.distance,
        form.course,
        course,
        form.category,
      ),
    })),
  );
  const focused = $derived(results.find((x) => x.course === focus)!);
  const thresholds = $derived(
    getStandards(
      form.age,
      form.category,
      form.course,
      form.distance,
      form.stroke,
    ),
  );
  const standing = $derived(
    thresholds && correctedTime !== null
      ? standardStatus(correctedTime, thresholds)
      : null,
  );
  const nextTime = $derived(
    thresholds && standing?.next !== null && standing?.next !== undefined
      ? thresholds[standing.next]
      : null,
  );
  const nextGap = $derived(
    nextTime !== null && correctedTime !== null
      ? Math.max(0, correctedTime - nextTime)
      : null,
  );
  const marker = $derived(
    thresholds && correctedTime !== null
      ? Math.max(2, Math.min(98, ladderPosition(correctedTime, thresholds)))
      : 0,
  );
  const sourceDistance = $derived(
    eventDistance(form.distance, form.course, form.stroke),
  );
  const focusDistance = $derived(
    eventDistance(form.distance, focus, form.stroke),
  );
  const lengths = $derived(focusDistance / (focus === "LCM" ? 50 : 25));
  const pace = $derived(
    focused.time !== null ? (focused.time / focusDistance) * 100 : null,
  );
  const error = $derived(
    time === null
      ? "Enter a time like 58.32 or 1:02.45 (up to 60 minutes)."
      : !altitudeValid
        ? elevationUnit === "ft"
          ? "Enter an elevation in whole feet, between 0 and 20,000."
          : "Enter an elevation between 0 and 6,096 meters."
        : time <= adjustment
          ? "The time must be longer than the altitude adjustment."
          : "",
  );
  const currentLabel = $derived(
    eventLabel(form.distance, form.course, form.stroke),
  );

  onMount(() => {
    let preferences = readPreferences(null);
    try {
      preferences = readPreferences(
        JSON.parse(localStorage.getItem("turnmark-preferences") ?? "null"),
      );
    } catch {
      /* Malformed or blocked storage falls back to the normal defaults. */
    }
    const {
      elevationUnit: unit,
      standardMode: mode,
      ...defaults
    } = preferences;
    elevationUnit = unit;
    standardMode = window.location.hash.startsWith("#t=") ? "targets" : mode;
    // A shared conversion is complete: never mix in a remembered altitude/category.
    form = window.location.hash.startsWith("#t=")
      ? readState(window.location.hash)
      : { ...defaultState, ...defaults };
    try {
      const raw: unknown = JSON.parse(
        localStorage.getItem("turnmark-swimboard") ?? "[]",
      );
      if (Array.isArray(raw))
        saved = raw
          .filter(
            (x) => typeof x?.id === "string" && typeof x?.hash === "string",
          )
          .slice(0, 8)
          .map((x) => ({ id: x.id, form: readState(x.hash) }));
    } catch {
      /* Corrupt or blocked storage starts with an empty board. */
    }
    try {
      const raw: unknown = JSON.parse(
        localStorage.getItem("turnmark-history") ?? "[]",
      );
      if (Array.isArray(raw))
        conversions = raw
          .filter(
            (x) =>
              typeof x?.id === "string" &&
              typeof x?.hash === "string" &&
              Number.isFinite(x?.createdAt) &&
              courses.includes(x?.target),
          )
          .slice(0, 50)
          .map((x) => ({
            id: x.id,
            form: readState(x.hash),
            target: x.target,
            createdAt: x.createdAt,
          }));
    } catch {
      /* History is optional when storage is unavailable. */
    }
    lastRecorded = `${stateHash(form)}|${focus}`;
    mounted = true;
    let sectionFrame = 0;
    const updateSection = () => {
      sectionFrame = 0;
      let next = "converter",
        nearest = -Infinity;
      for (const id of ["converter", "history", "standards", "method"]) {
        const top = document.getElementById(id)?.getBoundingClientRect().top;
        if (
          top !== undefined &&
          top <= innerHeight * 0.3 &&
          (top > nearest + 1 ||
            (Math.abs(top - nearest) <= 1 && activeSection === id))
        ) {
          next = id;
          nearest = top;
        }
      }
      activeSection = next;
    };
    const scheduleSection = () => {
      if (!sectionFrame) sectionFrame = requestAnimationFrame(updateSection);
    };
    window.addEventListener("scroll", scheduleSection, { passive: true });
    window.addEventListener("resize", scheduleSection);
    scheduleSection();
    const hashChange = () => {
      if (window.location.hash.startsWith("#t=")) {
        form = readState(window.location.hash);
        standardMode = "targets";
      }
    };
    window.addEventListener("hashchange", hashChange);
    return () => {
      clearTimeout(toastTimer);
      cancelAnimationFrame(sectionFrame);
      window.removeEventListener("scroll", scheduleSection);
      window.removeEventListener("resize", scheduleSection);
      window.removeEventListener("hashchange", hashChange);
    };
  });
  function recordConversion(
    snapshot: SwimState,
    target: Course,
    explicit = false,
  ) {
    const hash = `${stateHash(snapshot)}|${target}`;
    if (!explicit && hash === lastRecorded) return;
    if (
      explicit &&
      conversions[0] &&
      `${stateHash(conversions[0].form)}|${conversions[0].target}` === hash &&
      conversions[0].target === target
    )
      return;
    lastRecorded = hash;
    const next = [
      {
        id: crypto.randomUUID(),
        form: snapshot,
        target,
        createdAt: Date.now(),
      },
      ...conversions,
    ].slice(0, 50);
    writeHistory(next);
  }
  function writeHistory(next: HistoryEntry[]) {
    try {
      localStorage.setItem(
        "turnmark-history",
        JSON.stringify(
          next.map((x) => ({
            id: x.id,
            hash: stateHash(x.form),
            target: x.target,
            createdAt: x.createdAt,
          })),
        ),
      );
      conversions = next;
    } catch {
      notify(
        "History couldn’t be saved in this browser. Copy a link to keep this swim.",
      );
    }
  }
  function restoreConversion(entry: HistoryEntry) {
    lastRecorded = `${stateHash(entry.form)}|${entry.target}`;
    form = { ...entry.form };
    focus = entry.target;
    go("converter");
    notify("Previous conversion restored.");
  }
  function historyResult(entry: HistoryEntry) {
    const seconds = parseTime(entry.form.time);
    const adjusted =
      seconds === null
        ? 0
        : seconds -
          altitudeAdjustment(entry.form.distance, entry.form.altitude);
    return convert(
      adjusted,
      entry.form.stroke,
      entry.form.distance,
      entry.form.course,
      entry.target,
      entry.form.category,
    ).time;
  }
  function dateLabel(timestamp: number) {
    const date = new Date(timestamp);
    return (
      date.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
      " · " +
      date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    );
  }
  function notify(message: string) {
    toast = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ""), 3500);
  }
  function go(id: string) {
    activeSection = id === "conversion-results" ? "converter" : id;
    document.getElementById(id)?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
  }
  function setStroke(stroke: Stroke) {
    form.stroke = stroke;
    if (!eventDistances(stroke).includes(form.distance))
      form.distance = stroke === "IM" ? 200 : 100;
    ensureCourse();
  }
  function ensureCourse() {
    if (!availableEvent(form.distance, form.course, form.stroke))
      form.course = "SCY";
  }
  function reset() {
    form = { ...defaultState };
    focus = "LCM";
    elevationOpen = false;
    elevationUnit = "ft";
    standardMode = "targets";
    history.replaceState(null, "", location.pathname + location.search);
    notify("Inputs reset.");
  }
  async function share() {
    if (error) return;
    const url = `${location.origin}${location.pathname}#${stateHash(form)}`;
    try {
      await navigator.clipboard.writeText(url);
      history.replaceState(null, "", url);
      notify("Conversion link copied.");
    } catch {
      history.replaceState(null, "", url);
      notify("Share link is ready in your address bar.");
    }
  }
  function persist(next: typeof saved) {
    try {
      localStorage.setItem(
        "turnmark-swimboard",
        JSON.stringify(
          next.map((x) => ({ id: x.id, hash: stateHash(x.form) })),
        ),
      );
      saved = next;
      return true;
    } catch {
      notify(
        "Your browser couldn’t save this swim. You can copy a link instead.",
      );
      return false;
    }
  }
  function save() {
    if (error || !mounted) return;
    const snapshot = { ...form };
    recordConversion(snapshot, focus, true);
    const next = [
      { id: crypto.randomUUID(), form: snapshot },
      ...saved.filter((x) => stateHash(x.form) !== stateHash(snapshot)),
    ].slice(0, 8);
    if (persist(next)) notify("Saved to your swimboard on this device.");
  }
  function download() {
    if (error) return;
    const rows: (string | number)[][] = [
      ["Turnmark course comparison"],
      ["Event", currentLabel],
      ["Entered time", form.time],
      ["Source course", form.course],
      ["Factor table", form.category],
      ["Standards system", form.standardSystem],
      [
        "Standards age group",
        form.standardSystem === "masters" ? form.mastersAge : form.age,
      ],
      ["Altitude ft", form.altitude],
      ["Altitude correction seconds", adjustment],
      [],
      ["Course", "Event", "Time", "Method"],
      ...results.map((x) => [
        x.course,
        eventLabel(form.distance, x.course, form.stroke),
        formatTime(x.time),
        x.kind === "swum"
          ? adjustment
            ? "Altitude adjusted"
            : "Entered swim"
          : x.kind === "published"
            ? "Published NCAA metric-to-yards factor"
            : x.kind === "derived"
              ? "Derived from NCAA factors"
              : (x.reason ?? "Unavailable"),
      ]),
      [],
      ["Conversion source", conversionSource.url],
      ["Standards source", standardsSource.url],
      [
        "Note",
        "Course-converted times are estimates. Check the meet rules for entry eligibility.",
      ],
    ];
    const url = URL.createObjectURL(
      new Blob(
        ["\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n")],
        { type: "text/csv;charset=utf-8" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `turnmark-${form.distance}-${form.stroke.toLowerCase()}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>

<svelte:head><title>{site.title}</title></svelte:head>
<a class="skip-link" href="#main">Skip to converter</a>
<header class="site-header">
  <div class="header-inner">
    <a class="wordmark" href="./" aria-label="Turnmark home"
      ><span class="brand-icon"><Icon name="turn" size={25} /></span
      >turnmark<span class="brand-period">.</span></a
    >
    <nav aria-label="Main navigation">
      <button
        class:nav-current={activeSection === "converter"}
        onclick={() => go("converter")}>Converter</button
      ><button
        class:nav-current={activeSection === "history"}
        onclick={() => go("history")}>History</button
      ><button
        class:nav-current={activeSection === "standards"}
        onclick={() => go("standards")}>Time standards</button
      ><button onclick={() => go("method")}>The method</button>
    </nav>
    <div class="header-actions">
      <Install />
      <a
        class="github-link"
        aria-label="Turnmark source code on GitHub"
        href="https://github.com/Stanback/turnmark"
        target="_blank"
        rel="noreferrer"
        ><Icon name="github" size={18} /><span>Open source</span><Icon
          name="external"
          size={13}
        /></a
      >
    </div>
  </div>
</header>
<main id="main">
  <section class="intro" aria-labelledby="page-title">
    <img
      class="hero-photo"
      src={`${import.meta.env.BASE_URL}images/swimmer-hero.webp`}
      alt=""
      fetchpriority="high"
    />
    <div class="hero-inner page-width">
      <div class="intro-copy">
        <h1 id="page-title">
          Your swim.<br />Any
          <span class="course-word"
            >course<svg viewBox="0 0 320 15" aria-hidden="true"
              ><path d="M3 9q140-14 312-2" /></svg
            ></span
          >.
        </h1>
        <p>
          Swim time converter for yards and meters.<br class="desktop-break" /> Compare
          SCY, SCM, and LCM times and published standards.
        </p>
        <button
          class="hero-cta"
          onclick={() => {
            go("converter");
            document
              .getElementById("swim-time")
              ?.focus({ preventScroll: true });
          }}>Start converting <Icon name="arrow" size={17} /></button
        >
      </div>
    </div>
  </section>

  <section
    id="converter"
    class="workspace page-width"
    aria-label="Swim time converter"
  >
    <div class="input-panel">
      <button class="text-button reset" onclick={reset}>Reset</button>
      <div class="panel-title">
        <h2>Convert your swim</h2>
        <p>Compare times across pool courses.</p>
      </div>
      <div class="field-label" id="stroke-label">Stroke</div>
      <div class="stroke-picker" role="group" aria-labelledby="stroke-label">
        {#each strokes as stroke}<button
            class:active={form.stroke === stroke.id}
            aria-pressed={form.stroke === stroke.id}
            onclick={() => setStroke(stroke.id)}>{stroke.short}</button
          >{/each}
      </div>
      <label class="field-label distance-label" for="distance"
        >Distance <span>{form.course === "SCY" ? "yards" : "meters"}</span
        ></label
      >
      <div class="select-wrap">
        <select id="distance" bind:value={form.distance} onchange={ensureCourse}
          >{#each eventDistances(form.stroke) as distance}<option
              value={distance}
              >{eventDistance(distance, form.course, form.stroke)}
              {form.course === "SCY" ? "yards" : "meters"}</option
            >{/each}</select
        ><Icon name="chevron" size={16} />
      </div>
      <label class="field-label time-label" for="swim-time"
        >Your time <span>minutes : seconds . hundredths</span></label
      >
      <div class:invalid={!!error} class="time-entry">
        <input
          id="swim-time"
          aria-invalid={!!error}
          aria-describedby={error ? "time-error" : "time-help"}
          inputmode="decimal"
          autocomplete="off"
          spellcheck="false"
          maxlength="9"
          bind:value={form.time}
        /><Icon name="clock" size={23} />
      </div>
      {#if error}<p class="field-error" id="time-error" role="alert">
          {error}
        </p>{:else}<div class="time-help" id="time-help">
          <span class="status-dot"></span>Results update as you type
        </div>{/if}
      <div class="field-label course-label" id="course-label">Swum in</div>
      <div class="course-picker" role="group" aria-labelledby="course-label">
        {#each courses as course}<button
            class:active={form.course === course}
            disabled={!availableEvent(form.distance, course, form.stroke)}
            aria-pressed={form.course === course}
            onclick={() => (form.course = course)}
            ><strong>{course}</strong><span>{courseInfo[course].pool}</span
            ></button
          >{/each}
      </div>
      <div class="factor-row">
        <label for="category">Category <span>for published tables</span></label>
        <div class="select-wrap">
          <select id="category" bind:value={form.category}
            ><option value="women">Women / girls</option><option value="men"
              >Men / boys</option
            ></select
          ><Icon name="chevron" size={13} />
        </div>
      </div>
      <details class="altitude-options" bind:open={elevationOpen}>
        <summary
          ><span><Icon name="mountain" size={17} />Swam at altitude?</span><span
            class="summary-elevation"
            >{altitudeValid && form.altitude > 0 ? elevationLabel : "+"}</span
          ></summary
        >
        <div class="altitude-body">
          <div class="elevation-heading">
            <label for="altitude">Pool elevation</label>
            <div
              class="elevation-units"
              role="group"
              aria-label="Elevation units"
            >
              <button
                class:active={elevationUnit === "ft"}
                aria-pressed={elevationUnit === "ft"}
                onclick={() => (elevationUnit = "ft")}>ft</button
              >
              <button
                class:active={elevationUnit === "m"}
                aria-pressed={elevationUnit === "m"}
                onclick={() => (elevationUnit = "m")}>m</button
              >
            </div>
          </div>
          <div class="elevation-entry">
            <input
              type="number"
              id="altitude"
              min="0"
              max={elevationUnit === "ft" ? 20000 : 6096}
              step={elevationUnit === "ft" ? 1 : "any"}
              bind:value={() => elevationInput, setElevation}
              aria-invalid={!altitudeValid}
              aria-describedby="elevation-help"
            /><span>{elevationUnit} above sea level</span>
          </div>
          <p id="elevation-help">
            {#if altitudeValid}{elevationUnit === "ft"
                ? `${(form.altitude * 0.3048).toLocaleString(undefined, { maximumFractionDigits: 1 })} meters`
                : `${form.altitude.toLocaleString()} feet (rounded to the nearest foot)`}.{/if}
            {#if adjustment}Altitude adjustment: −{adjustment.toFixed(2)}s
              before course conversion.
            {:else if altitudeValid && form.altitude > 0}{form.altitude < 3000
                ? "Below the 3,000 ft threshold; no adjustment applies."
                : "No altitude adjustment is published for this sprint event."}
            {:else}Adjustments start at 3,000 ft (914.4 m) for events of 200 or
              longer.{/if}
          </p>
        </div>
      </details>
      <div class="input-footnote">
        <Icon name="info" size={14} /><span
          >Estimates for perspective. Meet rules decide entry eligibility.</span
        >
      </div>
      <button
        class="primary-button mobile-results-jump"
        disabled={!!error}
        onclick={() => {
          go("conversion-results");
          document
            .getElementById("results-title")
            ?.focus({ preventScroll: true });
        }}>See your results <Icon name="down" size={19} /></button
      >
    </div>

    <div
      class="results-panel"
      id="conversion-results"
      role="region"
      aria-labelledby="results-title"
    >
      <div class="results-heading">
        <div>
          <h2 id="results-title" tabindex="-1">Your conversion results</h2>
        </div>
        <a
          class="method-chip"
          href={conversionSource.url}
          target="_blank"
          rel="noreferrer"
          aria-label="NCAA factors — open published conversion source"
          >NCAA factors <Icon name="external" size={12} /></a
        >
      </div>
      <div class="pool-scene">
        <div class="pool-scene-top">
          <div>
            <span class="tiny-label"
              >{form.course} <span aria-hidden="true">→</span> {focus}</span
            >
            <h3>
              {eventLabel(form.distance, focus, form.stroke)}
              <span>· {focus}</span>
            </h3>
          </div>
          <div class="pool-scene-caption">
            {courseInfo[focus].name}<span
              >{focused.kind === "swum"
                ? "Your entered course"
                : "Converted estimate"}</span
            >
          </div>
        </div>
        <Pool
          course={focus}
          distance={focusDistance}
          time={formatTime(focused.time)}
        />
        <div class="pool-scene-bottom">
          <span
            ><strong>{lengths}</strong> lengths
            <span class="dot-separator">·</span>
            <strong>{Math.max(0, lengths - 1)}</strong>
            {lengths === 2 ? "turn" : "turns"}</span
          ><span
            >{focused.time !== null
              ? `${formatTime(pace)} / 100 ${focus === "SCY" ? "yd" : "m"}`
              : "Conversion unavailable"}</span
          >
        </div>
      </div>
      {#if adjustment > 0 && correctedTime !== null}
        <section
          class="altitude-conversion"
          aria-labelledby="altitude-title"
          aria-live="polite"
        >
          <div class="altitude-conversion-heading">
            <Icon name="mountain" size={17} />
            <h3 id="altitude-title">Altitude adjustment</h3>
            <span>{form.course}</span>
          </div>
          <div class="altitude-comparison">
            <div class="altitude-before">
              <span>Swum at {elevationLabel}</span><strong
                data-testid="altitude-original">{formatTime(time)}</strong
              >
            </div>
            <div class="altitude-difference">
              <span>−{adjustment.toFixed(2)}s</span><Icon
                name="arrow"
                size={22}
              />
            </div>
            <div class="altitude-after">
              <span>Sea-level estimate</span><strong
                data-testid="altitude-corrected"
                >{formatTime(correctedTime)}</strong
              >
            </div>
          </div>
          <p>
            Adjusted in {form.course} before course conversion.
            <a href={altitudeSource.url} target="_blank" rel="noreferrer"
              >USA Swimming §4.7<Icon name="external" size={10} /></a
            >
          </p>
        </section>
      {/if}
      <div
        class="result-cards"
        aria-label="Course comparison results"
        aria-live="polite"
        aria-atomic="true"
      >
        {#each results as result}<button
            class="result-card"
            class:selected={focus === result.course}
            class:unavailable={result.time === null}
            aria-pressed={focus === result.course}
            onclick={() => (focus = result.course)}
            ><div class="result-card-top">
              <strong>{result.course}</strong><span
                >{result.course === form.course
                  ? adjustment
                    ? "ADJUSTED"
                    : "YOUR INPUT"
                  : "ESTIMATE"}</span
              >
            </div>
            <div class="result-time" data-testid={`result-${result.course}`}>
              {formatTime(result.time)}
            </div>
            <div class="result-card-bottom">
              <span
                >{eventDistance(form.distance, result.course, form.stroke)}
                {result.course === "SCY" ? "yards" : "meters"}</span
              >{#if focus === result.course}<span class="selected-check"
                  ><Icon name="check" size={12} /></span
                >{:else}<Icon name="arrow" size={15} />{/if}
            </div></button
          >{/each}
      </div>
      <div class="result-explanation">
        <Icon name="info" size={15} />
        <p>
          {#if focused.kind === "unavailable"}{focused.reason}{:else if focused.kind === "swum"}{adjustment
              ? `Your sea-level estimate in ${form.course}.`
              : "Your entered swim, exactly as timed."}{:else}{form.course} → {focus}:
            <strong>× {focused.factor?.toFixed(5)}</strong>. {focused.kind ===
            "published"
              ? "Published NCAA factor."
              : "Derived from NCAA metric-to-yards factors."} Truncated to hundredths.{/if}
        </p>
      </div>
      <div class="result-actions">
        <button class="primary-button" onclick={save} disabled={!!error}
          ><Icon name="bookmark" size={16} />Save swim</button
        ><button class="secondary-button" onclick={share} disabled={!!error}
          ><Icon name="link" size={16} />Copy link</button
        ><button
          class="icon-button export-button"
          onclick={download}
          disabled={!!error}
          aria-label="Download course comparison as CSV"
          title="Download CSV"><Icon name="download" size={18} /></button
        ><span class="local-note">No account. No uploads.</span>
      </div>
    </div>
  </section>

  <div class="insights-grid page-width">
    <section class="history-panel" id="history" aria-labelledby="history-title">
      <div class="history-heading">
        <div>
          <h2 id="history-title">
            Recent conversions <span>{conversions.length}</span>
          </h2>
        </div>
        {#if conversions.length}<button
            class="text-button"
            onclick={() => {
              writeHistory([]);
              notify("Conversion history cleared.");
            }}>Clear history</button
          >{/if}
      </div>
      <p class="history-subtitle">
        Your last 50 conversions. Only on this device.
      </p>
      <div
        class="history-filters"
        role="group"
        aria-label="Filter conversion history"
      >
        <button
          class:active={historyFilter === "all"}
          aria-pressed={historyFilter === "all"}
          onclick={() => (historyFilter = "all")}>All</button
        >
        {#each strokes as stroke}<button
            class:active={historyFilter === stroke.id}
            aria-pressed={historyFilter === stroke.id}
            aria-label={`Filter history: ${stroke.short}`}
            onclick={() => (historyFilter = stroke.id)}>{stroke.short}</button
          >{/each}
      </div>
      <div class="history-list">
        {#each filteredHistory as entry (entry.id)}
          <div class="history-row">
            <button
              class="history-restore"
              onclick={() => restoreConversion(entry)}
              aria-label={`Restore ${eventLabel(entry.form.distance, entry.form.course, entry.form.stroke)} ${entry.form.time}`}
            >
              <span
                class="history-wave"
                class:medley={entry.form.stroke === "IM"}
                ><Icon name="wave" size={20} /></span
              >
              <span class="history-event"
                ><strong
                  >{eventLabel(
                    entry.form.distance,
                    entry.form.course,
                    entry.form.stroke,
                  )}</strong
                ><small
                  >{entry.form.course} <span aria-hidden="true">→</span>
                  {entry.target} · {entry.form.category === "women"
                    ? "Women"
                    : "Men"}</small
                ></span
              >
              <span class="history-times"
                ><strong
                  >{formatTime(parseTime(entry.form.time))} <span>→</span>
                  {formatTime(historyResult(entry))}</strong
                ><small>{dateLabel(entry.createdAt)}</small></span
              >
              <Icon name="chevron" size={14} />
            </button>
            <button
              class="history-remove"
              aria-label={`Remove conversion ${entry.form.time}`}
              onclick={() =>
                writeHistory(conversions.filter((x) => x.id !== entry.id))}
              ><Icon name="close" size={14} /></button
            >
          </div>
        {:else}
          <div class="history-empty">
            <span class="empty-icon"
              ><Icon
                name={conversions.length ? "wave" : "history"}
                size={26}
              /></span
            >
            <h3>
              {conversions.length
                ? "No conversions for this stroke."
                : "No conversions yet."}
            </h3>
            <p>
              {conversions.length
                ? "Try another filter to find a previous conversion."
                : "Change a time or event above. Your conversion will appear here automatically."}
            </p>
            <span
              ><Icon name="lock" size={13} />Private to this browser. No account
              needed.</span
            >
          </div>
        {/each}
      </div>
    </section>
    <section
      class="standards-section"
      id="standards"
      aria-labelledby="standards-title"
    >
      <div
        class="standards-tabs"
        role="group"
        aria-label="Performance comparison"
      >
        <button
          class:active={standardMode === "targets"}
          aria-pressed={standardMode === "targets"}
          onclick={() => (standardMode = "targets")}>Time standards</button
        >
        <button
          class:active={standardMode === "points"}
          aria-pressed={standardMode === "points"}
          onclick={() => (standardMode = "points")}
          >World Aquatics points</button
        >
      </div>
      {#if standardMode === "targets"}
        <label class="standards-system" for="standards-system"
          >Standards<select
            id="standards-system"
            bind:value={form.standardSystem}
            ><option value="youth">USA Swimming · Youth</option><option
              value="masters">U.S. Masters Swimming · Adults</option
            ></select
          ></label
        >
        {#if form.standardSystem === "masters"}
          <Masters
            bind:age={form.mastersAge}
            course={form.course}
            category={form.category}
            distance={form.distance}
            stroke={form.stroke}
            {time}
          />
        {:else}
          <div class="standards-title-row">
            <div>
              <h2 id="standards-title">USA Swimming time standards</h2>
              <p>Find your place on the USA Swimming motivational ladder.</p>
            </div>
            <div class="standards-controls">
              <label for="age-group"
                >Age group<select id="age-group" bind:value={form.age}
                  >{#each ages as age}<option value={age.id}>{age.label}</option
                    >{/each}</select
                ></label
              ><span class="standards-edition"
                >2024–2028<br /><span>National age group standards</span></span
              >
            </div>
          </div>
          <div class="standards-card">
            <div class="standards-context">
              <span class="context-pill">{currentLabel} · {form.course}</span
              ><span
                >{form.category === "women" ? "Girls" : "Boys"} · {ages.find(
                  (a) => a.id === form.age,
                )?.label} <span class="context-divider">/</span>
                {adjustment
                  ? "Altitude-adjusted input"
                  : "Your entered course"}</span
              ><a href={standardsSource.url} target="_blank" rel="noreferrer"
                >Official table<Icon name="external" size={12} /></a
              >
            </div>
            {#if thresholds && standing && correctedTime !== null}<div
                class="standard-summary"
              >
                <div class="standard-achievement">
                  <span
                    class="achievement-badge"
                    class:long-label={standing.achieved >= 0 &&
                      levels[standing.achieved].length > 2}
                    >{standing.achieved >= 0
                      ? levels[standing.achieved]
                      : "→"}</span
                  >
                  <div>
                    <h3>
                      {standing.achieved >= 0
                        ? `${levels[standing.achieved]} time, nicely done.`
                        : "Your next chapter starts here."}
                    </h3>
                    <p>
                      {#if standing.next !== null}<strong
                          >{nextGap?.toFixed(2)}s</strong
                        >
                        to the next time standard:
                        <strong>{levels[standing.next]}</strong>
                        in {formatTime(nextTime)}.{:else}You’ve reached the top
                        motivational standard for this event.{/if}
                    </p>
                  </div>
                </div>
                <div class="goal-time">
                  <span class="tiny-label"
                    >{standing.next !== null
                      ? `NEXT UP · ${levels[standing.next]}`
                      : "TOP STANDARD · AAAA"}</span
                  ><strong>{formatTime(nextTime ?? thresholds[5])}</strong>
                </div>
              </div>
              <div class="ladder" style={`--marker:${marker}%`}>
                <div class="ladder-track">
                  <div class="ladder-progress" style={`width:${marker}%`}></div>
                  <span class="swim-marker"
                    ><span>{formatTime(correctedTime)}</span></span
                  >
                </div>
                <div class="ladder-levels">
                  {#each thresholds as threshold, i}<div
                      class:achieved={i <= standing.achieved}
                    >
                      <span class="ladder-node"
                        >{#if i <= standing.achieved}<Icon
                            name="check"
                            size={10}
                          />{/if}</span
                      ><strong>{levels[i]}</strong><span
                        >{formatTime(threshold)}</span
                      >
                    </div>{/each}
                </div>
              </div>
              <p class="standards-note">
                {#if adjustment}Altitude-adjusted comparison; confirm
                  eligibility with your meet.{:else}Compared using your entered {form.course}
                  time. Course estimates above don’t count as official swims.{/if}
              </p>
            {:else}<div class="standards-empty">
                <Icon name="info" size={22} />
                <h3>
                  {error
                    ? "Your next goal is one time away."
                    : "No published standard for this selection."}
                </h3>
                <p>
                  {error
                    ? "Enter a valid swim above to explore the ladder."
                    : "Try another age group or event. We leave missing data empty."}
                </p>
              </div>{/if}
          </div>
        {/if}
      {:else}
        <div class="points-panel">
          <h2 id="standards-title">World Aquatics points</h2>
          <p>
            Compare performances across events and metric pool courses. Higher
            points mean a faster performance relative to the event’s
            world-record reference time.
          </p>
          <div class="points-score">
            <strong data-testid="points-score"
              >{points === null ? "—" : points.toLocaleString()}</strong
            ><span>WORLD AQUATICS POINTS</span>
          </div>
          {#if pointContext && points !== null}
            <div class="points-context">
              <p class="points-event">
                {currentLabel} · {form.course} · {form.category === "women"
                  ? "Women"
                  : "Men"}
              </p>
              <p class="points-tldr">
                <strong
                  >1,000 points matches the world-record reference time</strong
                >. World Aquatics fixes this reference for each event, course,
                and category using the approved record at the table’s cutoff
                date. It can lag a newer record. Scores are not adjusted for
                age.
              </p>
              <div class="points-benchmarks">
                <div>
                  <span>World-record reference · 1,000 points</span><strong
                    >{formatTime(pointContext.base)}</strong
                  ><small>2026 · {form.course}</small>
                </div>
                <div class="points-next">
                  <span
                    >Next points target · {pointContext.nextMark.toLocaleString()}
                    points</span
                  ><strong data-testid="points-next-time"
                    >{formatTime(pointContext.target)}</strong
                  ><small
                    ><b>{pointContext.gap.toFixed(2)}s</b> to drop from your entered
                    time</small
                  >
                  <small
                    >Next 100-point step: a suggested goal, not an official
                    qualifying time.</small
                  >
                </div>
              </div>
              <button
                class="points-standards-link"
                onclick={() => (standardMode = "targets")}
                >Compare with age-group time standards <Icon
                  name="arrow"
                  size={15}
                /></button
              >
            </div>
          {/if}
          {#if form.course === "SCY"}<p class="points-note">
              <Icon name="info" size={17} />World Aquatics publishes points for
              25m and 50m pools. Select SCM or LCM for an entered metric swim;
              we don’t score a yards conversion as an official swim.
            </p>
          {:else}<p class="points-note">
              <Icon name="info" size={17} />Based on your entered {form.course} time,
              without altitude adjustment. {pointsValidity[form.course]}.
            </p>{/if}
          <div class="points-formula">
            <span>Formula</span><code>1,000 × (base time / your time)³</code>
          </div>
          <a
            class="points-source"
            href={pointsSource.url}
            target="_blank"
            rel="noreferrer"
            >2026 base times <Icon name="external" size={13} /></a
          >
          <a
            class="points-source"
            href={pointsSource.method}
            target="_blank"
            rel="noreferrer"
            >How World Aquatics points work <Icon
              name="external"
              size={13}
            /></a
          >
        </div>
      {/if}
    </section>
  </div>

  {#if saved.length}<section
      class="swimboard page-width"
      aria-labelledby="swimboard-title"
    >
      <div class="board-heading">
        <h2 id="swimboard-title">Your swimboard<span>{saved.length}</span></h2>
        <p>Saved on this device.</p>
      </div>
      <div class="saved-grid">
        {#each saved as swim}<div class="saved-card">
            <button
              class="restore-swim"
              onclick={() => {
                form = { ...swim.form };
                go("converter");
              }}
              ><span
                >{eventLabel(
                  swim.form.distance,
                  swim.form.course,
                  swim.form.stroke,
                )} · {swim.form.course}</span
              ><strong>{formatTime(parseTime(swim.form.time))}</strong><span
                >{swim.form.category === "women"
                  ? "Women / girls"
                  : "Men / boys"}<Icon name="arrow" size={15} /></span
              ></button
            ><button
              class="remove-swim"
              aria-label={`Remove saved ${eventLabel(swim.form.distance, swim.form.course, swim.form.stroke)} ${swim.form.time}`}
              onclick={() => persist(saved.filter((x) => x.id !== swim.id))}
              ><Icon name="close" size={16} /></button
            >
          </div>{/each}
      </div>
    </section>{/if}

  <section
    class="method-section page-width"
    id="method"
    aria-labelledby="method-title"
  >
    <div class="method-intro">
      <h2 id="method-title">Sources and methodology</h2>
      <p>
        Turns, technique, and race-day conditions make every swim different.
        Here’s what goes into your estimate.
      </p>
      <a
        href="https://github.com/Stanback/turnmark/blob/main/docs/METHODOLOGY.md"
        target="_blank"
        rel="noreferrer"
        >Read the full methodology<Icon name="arrow" size={17} /></a
      >
    </div>
    <div class="method-items">
      <article>
        <div>
          <h3>Course conversion</h3>
          <p>
            NCAA metric-to-yards tables power course conversions. Reverse
            conversions and meter-to-meter comparisons use ratios of those
            factors and are labeled as derived estimates. Unsupported events
            stay unavailable.
          </p>
          <a href={conversionSource.url} target="_blank" rel="noreferrer"
            >2025–27 NCAA rules · updated Oct 2026<Icon
              name="external"
              size={12}
            /></a
          >
        </div>
      </article>
      <article>
        <div>
          <h3>USA Swimming standards</h3>
          <p>
            2,892 published times from USA Swimming’s 2024–2028 age group
            standards, revised October 2025. The ladder compares your input in
            its original course, age group, and published category.
          </p>
          <a href={standardsSource.url} target="_blank" rel="noreferrer"
            >USA Swimming motivational standards<Icon
              name="external"
              size={12}
            /></a
          >
        </div>
      </article>
      <article>
        <div>
          <h3>Altitude adjustments</h3>
          <p>
            Optional altitude adjustments follow USA Swimming’s published table.
            They’re applied to eligible individual events before course
            conversion. Your meet’s rules still govern accepted entries.
          </p>
          <a href={altitudeSource.url} target="_blank" rel="noreferrer"
            >USA Swimming times policy · §4.7<Icon
              name="external"
              size={12}
            /></a
          >
        </div>
      </article>
      <article>
        <div>
          <h3>World Aquatics points</h3>
          <p>
            World Aquatics points compare entered metric swims against published
            2026 base times. This is a separate scoring system from course
            conversion and age-group targets.
          </p>
          <a href={pointsSource.method} target="_blank" rel="noreferrer"
            >World Aquatics scoring method<Icon name="external" size={12} /></a
          >
        </div>
      </article>
    </div>
  </section>
  <section class="faq-section page-width" aria-labelledby="faq-title">
    <div class="faq-intro">
      <h2 id="faq-title">About the swim time converter</h2>
      <p>
        Convert between short course yards, short course meters, and long course
        meters. Explore published time standards, altitude adjustments, and
        performance points.
      </p>
    </div>
    <div class="faq-list">
      {#each faqs as faq}<details>
          <summary>{faq.question}<Icon name="chevron" size={16} /></summary>
          <div class="faq-answer">
            <p>{faq.answer}</p>
            {#if faq.url}<a href={faq.url} target="_blank" rel="noreferrer"
                >{faq.source}<Icon name="external" size={12} /></a
              >{/if}
          </div>
        </details>{/each}
    </div>
  </section>
</main>
<div class="appearance-row page-width"><Theme /></div>
<footer class="page-width">
  <a class="footer-brand" href="./">turnmark.</a><span
    >Built by <a href="https://bristanback.com" target="_blank" rel="noreferrer"
      >Bri Stanback</a
    > · Open source, always.</span
  ><span>Sources checked October 16, 2026</span>
</footer>
<nav class="mobile-nav" aria-label="Mobile navigation">
  {#each [{ id: "converter", icon: "wave", label: "Converter" }, { id: "history", icon: "history", label: "History" }, { id: "standards", icon: "standards", label: "Standards" }, { id: "method", icon: "info", label: "The method" }] as item}
    <button
      class:active={activeSection === item.id}
      aria-current={activeSection === item.id ? "location" : undefined}
      onclick={() => go(item.id)}
      ><Icon name={item.icon} size={21} /><span>{item.label}</span></button
    >
  {/each}
</nav>
<div class="toast" class:visible={!!toast} role="status" aria-live="polite">
  {#if toast}<Icon name="check" size={17} />{toast}{/if}
</div>
