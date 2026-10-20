<script lang="ts">
  import { coloradoDistanceCaveat } from "./lib/calculation-copy";
  import MethodComparison from "./lib/MethodComparison.svelte";
  import { onMount, tick } from "svelte";
  import Icon from "./lib/Icon.svelte";
  import HeroCurrent from "./lib/HeroCurrent.svelte";
  import Masters from "./lib/Masters.svelte";
  import Install from "./lib/Install.svelte";
  import Theme from "./lib/Theme.svelte";
  import { site, faqs } from "./data/site";
  import { resources } from "./data/resources";
  import {
    conversionMethods,
    coloradoMethod,
    altitudePolicies,
  } from "@turnmark/sdk/conversion";
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
    convertState,
    stateAltitude,
    swimRequest,
    eventDistances,
    eventDistance,
    eventLabel,
    availableEvent,
    altitudeAdjustment,
    adjustedTime,
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

  // The web workspace starts with the user's time, not an implicit sample race.
  let form = $state<SwimState>({ ...defaultState, time: "" });
  let focus = $state<Course>("LCM");
  let toast = $state("");
  let saved = $state<{ id: string; form: SwimState }[]>([]);
  let toastTimer: ReturnType<typeof setTimeout>;
  let mounted = $state(false);
  let elevationUnit = $state<"ft" | "m">("ft");
  let calculationOpen = $state(false);
  let altitudeEnabled = $state(false);
  let resourcesOpen = $state(false);
  let methodologyOpen = $state(false);
  let historyOpen = $state(false);
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
    if (form.altitude > 0) {
      calculationOpen = true;
      altitudeEnabled = true;
    }
    if (form.method === coloradoMethod) calculationOpen = true;
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
      altitudePolicy: form.altitudePolicy,
      method: form.method,
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
  const emptyTime = $derived(form.time.trim() === "");
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
  const altitudeResult = $derived(stateAltitude(form));
  const adjustment = $derived(
    altitudeResult.status === "available"
      ? altitudeResult.value.adjustmentSeconds
      : 0,
  );
  const correctedTime = $derived(
    altitudeResult.status === "available"
      ? altitudeResult.value.adjustedSeconds
      : null,
  );
  const results = $derived(
    courses.map((course) => ({ course, ...convertState(form, course) })),
  );
  const focused = $derived(results.find((x) => x.course === focus)!);
  const selectedMethod = $derived(
    conversionMethods.find((method) => method.id === form.method)!,
  );
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
    thresholds && time !== null ? standardStatus(time, thresholds) : null,
  );
  const nextTime = $derived(
    thresholds && standing?.next !== null && standing?.next !== undefined
      ? thresholds[standing.next]
      : null,
  );
  const nextGap = $derived(
    nextTime !== null && time !== null ? Math.max(0, time - nextTime) : null,
  );
  const marker = $derived(
    thresholds && time !== null
      ? Math.max(2, Math.min(98, ladderPosition(time, thresholds)))
      : 0,
  );
  const sourceDistance = $derived(
    eventDistance(form.distance, form.course, form.stroke),
  );
  const error = $derived(
    time === null
      ? "Enter a time like 58.32 or 1:02.45 (up to 60 minutes)."
      : !altitudeValid
        ? elevationUnit === "ft"
          ? "Enter an elevation in whole feet, between 0 and 20,000."
          : "Enter an elevation between 0 and 6,096 meters."
        : altitudeResult.status === "invalid" && altitudeValid && time !== null
          ? "The time must be longer than the altitude adjustment."
          : "",
  );
  const focusedTime = $derived(formatTime(error ? null : focused.time));
  const focusedClock = $derived(focusedTime.split("."));
  const selectedEvent = $derived(`${form.stroke}:${form.distance}`);
  const currentLabel = $derived(
    eventLabel(form.distance, form.course, form.stroke),
  );

  onMount(() => {
    resourcesOpen = window.location.hash === "#resources";
    methodologyOpen = window.location.hash === "#method";
    historyOpen = window.location.hash === "#history";
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
      : { ...defaultState, ...defaults, time: "" };
    restoreCalculationOptions();
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
      for (const id of ["converter", "standards", "history", "method"]) {
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
        restoreCalculationOptions();
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
    restoreCalculationOptions();
    focus = entry.target;
    go("converter");
    notify("Previous conversion restored.");
  }
  function historyResult(entry: HistoryEntry) {
    return convertState(entry.form, entry.target).time;
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
  async function go(id: string) {
    if (id === "history") historyOpen = true;
    if (id === "method") methodologyOpen = true;
    if (id === "resources") resourcesOpen = true;
    await tick();
    activeSection = id === "conversion-results" ? "converter" : id;
    document.getElementById(id)?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
  }
  function poolLabel(course: Course) {
    return courseInfo[course].pool
      .replace("yards", "yd")
      .replace("meters", "m");
  }
  function selectEvent(value: string) {
    const [stroke, distance] = value.split(":");
    const option = strokes.find((item) => item.id === stroke);
    if (!option || !eventDistances(option.id).includes(Number(distance)))
      return;
    form.stroke = option.id;
    form.distance = Number(distance);
    ensureCourse();
  }
  function ensureCourse() {
    if (!availableEvent(form.distance, form.course, form.stroke))
      form.course = "SCY";
  }
  function restoreCalculationOptions() {
    altitudeEnabled = form.altitude > 0;
    calculationOpen = altitudeEnabled || form.method === coloradoMethod;
  }
  function reset() {
    form = { ...defaultState, time: "" };
    focus = "LCM";
    calculationOpen = false;
    altitudeEnabled = false;
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
        "Your browser couldn’t save this comparison. You can copy a link instead.",
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
      ["Course conversion", selectedMethod.label],
      ["Standards system", form.standardSystem],
      [
        "Standards age group",
        form.standardSystem === "masters" ? form.mastersAge : form.age,
      ],
      ["Altitude ft", form.altitude],
      ["Altitude correction seconds", adjustment],
      [
        "Altitude policy",
        altitudePolicies.find((p) => p.id === form.altitudePolicy)!.label,
      ],
      [
        "Altitude source",
        altitudePolicies.find((p) => p.id === form.altitudePolicy)!.source.url,
      ],
      [],
      ["Course", "Event", "Time", "Method", "Caveat"],
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
              ? `Derived estimate · ${selectedMethod.label}`
              : (x.reason ?? "Unavailable"),
        x.caveat ? coloradoDistanceCaveat : "",
      ]),
      [],
      ["Conversion source", selectedMethod.source.url],
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
<div class="hero-atmosphere" aria-hidden="true"></div>
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
        class:nav-current={activeSection === "standards"}
        onclick={() => go("standards")}>Time standards</button
      ><button
        class:nav-current={activeSection === "history"}
        onclick={() => go("history")}>History</button
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
  <section class="intro page-width" aria-labelledby="page-title">
    <div class="intro-copy">
      <p class="converter-eyebrow">The swim time converter</p>
      <h1 id="page-title">Your swim.<br /><span>Any course.</span></h1>
      <p>
        Convert swim times and check published standards.<br />Your offline
        companion for 25-yard, 25-meter, and 50-meter pools.
      </p>
    </div>
    <HeroCurrent />
  </section>

  <section
    id="converter"
    class="workspace page-width"
    aria-label="Swim time converter"
  >
    <div class="converter-frame">
      <div class="input-panel">
        <button class="text-button reset" onclick={reset}
          >Reset <Icon name="reset" size={14} /></button
        >
        <div class="panel-title">
          <h2>Your swim</h2>
          <p>Enter a swim. Compare every course.</p>
        </div>
        <label class="field-label" for="event"
          >Event <span>distance &amp; stroke</span></label
        >
        <div class="select-wrap event-select">
          <Icon
            name={{
              FR: "freestyle",
              BK: "backstroke",
              BR: "breaststroke",
              FL: "butterfly",
              IM: "individual-medley",
            }[form.stroke]}
            size={22}
            class="select-leading-icon"
          />
          <select
            id="event"
            value={selectedEvent}
            onchange={(event) => selectEvent(event.currentTarget.value)}
          >
            {#each strokes as stroke}
              <optgroup label={stroke.name}>
                {#each eventDistances(stroke.id) as distance}
                  <option value={`${stroke.id}:${distance}`}
                    >{eventDistance(distance, form.course, stroke.id)}
                    {stroke.name}</option
                  >
                {/each}
              </optgroup>
            {/each}
          </select><Icon name="chevron" size={16} />
        </div>
        <label class="field-label time-label" for="swim-time"
          >Your time <span>mm:ss.hh</span></label
        >
        <div class:invalid={!!error && !emptyTime} class="time-entry">
          <input
            id="swim-time"
            aria-invalid={!!error && !emptyTime}
            aria-describedby={error && !emptyTime ? "time-error" : "time-help"}
            placeholder="0:00.00"
            inputmode="decimal"
            autocomplete="off"
            spellcheck="false"
            maxlength="9"
            bind:value={form.time}
          /><Icon name="clock" size={23} />
        </div>
        {#if error && !emptyTime}<p
            class="field-error"
            id="time-error"
            role="alert"
          >
            {error}
          </p>{:else}<div class="time-help" id="time-help">
            {emptyTime ? "Seconds or mm:ss.hh" : "Results update as you type"}
          </div>{/if}
        <div class="field-label course-label" id="course-label">
          Swum in <span>course length</span>
        </div>
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
          <label for="category"
            >Category <span>for published tables</span></label
          >
          <div class="select-wrap">
            <select id="category" bind:value={form.category}
              ><option value="women">Women / girls</option><option value="men"
                >Men / boys</option
              ></select
            ><Icon name="chevron" size={13} />
          </div>
        </div>
        <details class="calculation-options" bind:open={calculationOpen}>
          <summary
            ><span><Icon name="settings" size={17} />Calculation options</span
            ><span class="summary-elevation"
              >{form.method === coloradoMethod
                ? "Colorado"
                : "NCAA"}{#if altitudeValid && form.altitude > 0}
                · {elevationLabel}{/if}</span
            ></summary
          >
          <div class="calculation-body">
            <div class="course-method-field">
              <label class="field-label" for="conversion-method"
                >Course conversion</label
              >
              <div class="select-wrap">
                <select id="conversion-method" bind:value={form.method}
                  >{#each conversionMethods as method}<option value={method.id}
                      >{method.label}</option
                    >{/each}</select
                ><Icon name="chevron" size={16} />
              </div>
              <p>Standards and points use your original swim.</p>
            </div>
            <section class="altitude-controls" aria-label="Altitude adjustment">
              <h3>Altitude adjustment</h3>
              <label class="altitude-toggle"
                ><input
                  type="checkbox"
                  bind:checked={altitudeEnabled}
                  onchange={(e) => {
                    if (!e.currentTarget.checked) form.altitude = 0;
                  }}
                />Adjust for altitude</label
              >
              {#if altitudeEnabled}<div class="altitude-body">
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
                  <div class="altitude-policy-field">
                    <label class="field-label" for="altitude-policy"
                      >Altitude policy</label
                    >
                    <span class="select-wrap"
                      ><select
                        id="altitude-policy"
                        bind:value={form.altitudePolicy}
                        >{#each altitudePolicies as policy}<option
                            value={policy.id}>{policy.label}</option
                          >{/each}</select
                      ><Icon name="chevron" size={16} /></span
                    >
                  </div>
                  <p id="elevation-help">
                    {#if altitudeValid}{elevationUnit === "ft"
                        ? `${(form.altitude * 0.3048).toLocaleString(undefined, { maximumFractionDigits: 1 })} meters`
                        : `${form.altitude.toLocaleString()} feet (rounded to the nearest foot)`}.{/if}
                    {#if adjustment}Altitude adjustment: −{adjustment.toFixed(
                        2,
                      )}s before course conversion.
                    {:else if altitudeValid && form.altitude > 0}{form.altitude <
                      3000
                        ? "Below the 3,000 ft threshold; no adjustment applies."
                        : "No altitude adjustment is published for this sprint event."}
                    {:else}Adjustments start at 3,000 ft (914.4 m) for published
                      event distances.{/if}
                  </p>
                </div>{/if}
            </section>
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
            <h2 id="results-title" tabindex="-1">Equivalent times</h2>
          </div>
          <div class="course-position" aria-hidden="true">
            {#each courses as course}<span class:active={course === focus}
              ></span>{/each}
          </div>
        </div>
        <div class="focused-result" aria-live="polite" aria-atomic="true">
          <p class="focused-context">
            {eventDistance(form.distance, focus, form.stroke)}
            {strokes.find((stroke) => stroke.id === form.stroke)!.name} · {focus}
            ({poolLabel(focus)} pool)
          </p>
          <div class="focused-time" data-testid="focused-time">
            <span>{focusedClock[0]}</span>{#if focusedClock[1]}<span
                class="hundredths">.{focusedClock[1]}</span
              >{/if}
          </div>
          <p class="focused-provenance">
            {#if emptyTime}Enter your time to compare all three courses.
            {:else if error}Check your input to see a conversion.
            {:else if focused.kind === "unavailable"}No conversion published for
              this event.
            {:else if focused.kind === "swum"}{adjustment
                ? "Sea-level estimate"
                : "Your original time"} · {form.course}
            {:else}From {formatTime(time)} in {form.course} · {form.category ===
              "women"
                ? "Women / girls"
                : "Men / boys"}{/if}
          </p>
        </div>
        {#if !error && focused.caveat}<p
            class="altitude-method-note"
            data-testid="distance-caveat"
          >
            {coloradoDistanceCaveat}
          </p>{/if}
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
              <a
                href={altitudePolicies.find(
                  (p) => p.id === form.altitudePolicy,
                )!.source.url}
                target="_blank"
                rel="noreferrer"
                >Published altitude policy<Icon name="external" size={10} /></a
              >
            </p>
          </section>
        {/if}
        <h3 class="equivalents-title">
          <span class="equivalents-heading"
            ><Icon name="equivalents" size={20} />All course equivalents</span
          > <span>Select a course to focus</span>
        </h3>
        <div
          class="result-cards"
          role="group"
          aria-label="Course comparison results"
        >
          {#each results as result}
            <button
              class="result-card"
              class:selected={focus === result.course}
              class:unavailable={result.time === null}
              aria-pressed={focus === result.course}
              onclick={() => (focus = result.course)}
            >
              <span class="result-description">
                <span class="result-card-top"
                  ><strong>{result.course}</strong
                  >{#if focus === result.course}<Icon
                      name="check"
                      size={13}
                    />{/if}<span
                    >{emptyTime
                      ? result.course === form.course
                        ? "ENTERED COURSE"
                        : ""
                      : result.course === form.course
                        ? adjustment
                          ? "ADJUSTED"
                          : "ORIGINAL"
                        : result.kind === "published"
                          ? "PUBLISHED FACTOR"
                          : result.kind === "derived"
                            ? "DERIVED ESTIMATE"
                            : "UNAVAILABLE"}</span
                  ></span
                >
                <span class="result-card-bottom"
                  >{eventDistance(form.distance, result.course, form.stroke)}
                  {form.stroke === "IM"
                    ? "IM"
                    : strokes.find((stroke) => stroke.id === form.stroke)!
                        .short} ·
                  {poolLabel(result.course)} pool</span
                >
              </span>
              <span class="result-time" data-testid={`result-${result.course}`}
                >{formatTime(error ? null : result.time)}</span
              >
            </button>
          {/each}
        </div>
        <details class="result-method">
          <summary>
            <span><Icon name="info" size={15} />How this is calculated</span>
            <Icon name="chevron" size={15} />
          </summary>
          {#if error}<div class="result-explanation">
              <p>Results will appear when your input is valid.</p>
            </div>{/if}
          {#if !error}
            <MethodComparison
              adjusted={adjustment > 0}
              selected={form.method}
              request={{
                swim: swimRequest(form),
                to: focus,
                table: form.category,
                ...(form.altitude > 0
                  ? {
                      elevation: {
                        value: form.altitude,
                        unit: "feet" as const,
                      },
                      altitudePolicy: form.altitudePolicy,
                    }
                  : {}),
              }}
            />
            {#if adjustment}<p class="altitude-method-note">
                Both methods use the same sea-level estimate of {formatTime(
                  correctedTime,
                )} after the {adjustment.toFixed(2)}s altitude deduction. Your
                original swim remains {form.time}.
              </p>{/if}
          {/if}
          <button class="text-button method-link" onclick={() => go("method")}
            >View methodology &amp; sources <Icon
              name="arrow"
              size={14}
            /></button
          >
        </details>
        <div class="result-actions">
          <button class="primary-button" onclick={save} disabled={!!error}
            ><Icon name="bookmark" size={16} />Save comparison</button
          ><button class="secondary-button" onclick={share} disabled={!!error}
            ><Icon name="link" size={16} />Copy link</button
          ><button
            class="icon-button export-button"
            onclick={download}
            disabled={!!error}
            aria-label="Download course comparison as CSV"
            title="Download CSV"><Icon name="download" size={18} /></button
          >
        </div>
      </div>
    </div>
  </section>

  <div class="insights-grid page-width">
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
          aria-label="Time standards"
          onclick={() => (standardMode = "targets")}>Standards</button
        >
        <button
          class:active={standardMode === "points"}
          aria-pressed={standardMode === "points"}
          aria-label="World Aquatics points"
          onclick={() => (standardMode = "points")}>Points</button
        >
      </div>
      {#if standardMode === "targets"}
        <label class="standards-system" for="standards-system"
          >Standards<span class="select-wrap standards-select"
            ><select id="standards-system" bind:value={form.standardSystem}
              ><option value="youth">USA Swimming · Youth</option><option
                value="masters">U.S. Masters Swimming · Adults</option
              ></select
            ><Icon name="chevron" size={16} /></span
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
                >Age group<span class="select-wrap standards-select"
                  ><select id="age-group" bind:value={form.age}
                    >{#each ages as age}<option value={age.id}
                        >{age.label}</option
                      >{/each}</select
                  ><Icon name="chevron" size={16} /></span
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
                Your entered course</span
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
                    ><span>{formatTime(time)}</span></span
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
                Compared using your entered {form.course} time, before altitude or
                course conversion. Estimates above don’t count as official swims.
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
            Compare your entered metric swim with the published 2026 reference
            times. Higher points mean a faster relative performance.
          </p>
          {#if pointContext && points !== null}
            <div class="points-score">
              <strong data-testid="points-score"
                >{points.toLocaleString()}</strong
              >
              <span>POINTS</span>
            </div>
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
            {#if form.course !== "SCY"}<p class="points-note">
                <Icon name="info" size={17} />Based on your entered {form.course}
                time, without altitude adjustment. {pointsValidity[
                  form.course
                ]}.
              </p>{/if}
          {:else}
            <div class="points-unavailable points-note" role="status">
              <Icon name="info" size={22} />
              <div>
                <h3>
                  {error
                    ? "Enter a valid swim"
                    : form.course === "SCY"
                      ? "SCY isn’t scored"
                      : "No published points for this event"}
                </h3>
                <p>
                  {error
                    ? "Check your entered time and event in the converter."
                    : form.course === "SCY"
                      ? "Points are published for 25m and 50m pools. Enter an SCM or LCM swim to see a score. Converted estimates aren’t scored as actual swims."
                      : "The published table has no base time for this selection. Try another event or metric course."}
                </p>
                <button class="text-button" onclick={() => go("converter")}
                  >Back to converter <Icon name="arrow" size={15} /></button
                >
              </div>
            </div>
          {/if}
          <div class="points-formula">
            <span>Formula</span><code
              title="Base time divided by your entered time"
              >1,000 × (base / time)³</code
            >
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
    <section class="history-panel" id="history" aria-labelledby="history-title">
      <details class="history-disclosure" bind:open={historyOpen}>
        <summary class="history-heading">
          <h2 id="history-title">
            Recent conversions <span>{conversions.length}</span>
          </h2>
          <Icon name="chevron" size={17} />
        </summary>
        <div class="history-body">
          <div class="history-tools">
            <p class="history-subtitle">
              Your last 50 conversions. Only on this device.
            </p>
            {#if conversions.length}<button
                class="text-button clear-history"
                onclick={() => {
                  if (
                    !window.confirm(
                      "Clear all conversion history on this device? This cannot be undone.",
                    )
                  )
                    return;
                  writeHistory([]);
                  notify("Conversion history cleared.");
                }}>Clear history <Icon name="trash" size={14} /></button
              >{/if}
          </div>
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
                onclick={() => (historyFilter = stroke.id)}
                >{stroke.short}</button
              >{/each}
          </div>
          <div
            class="history-list"
            role="region"
            aria-label="Recent conversion entries"
          >
            {#each filteredHistory as entry (entry.id)}
              <div class="history-row">
                <button
                  class="history-restore"
                  onclick={() => restoreConversion(entry)}
                  title="Restore this conversion"
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
                  ><Icon name="lock" size={13} />Private to this browser. No
                  account needed.</span
                >
              </div>
            {/each}
          </div>
        </div>
      </details>
    </section>
  </div>

  {#if saved.length}<section
      class="swimboard page-width"
      aria-labelledby="swimboard-title"
    >
      <div class="board-heading">
        <h2 id="swimboard-title">
          Saved comparisons<span>{saved.length}</span>
        </h2>
        <p>Saved on this device.</p>
      </div>
      <div class="saved-grid">
        {#each saved as swim}<div class="saved-card">
            <button
              class="restore-swim"
              onclick={() => {
                form = { ...swim.form };
                restoreCalculationOptions();
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
  <section
    class="method-section page-width"
    id="method"
    aria-labelledby="method-title"
  >
    <details bind:open={methodologyOpen}>
      <summary
        ><h2 id="method-title">Sources &amp; methodology</h2>
        <Icon name="chevron" size={16} /></summary
      >
      <div class="method-content">
        <div class="method-intro">
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
                NCAA metric-to-yards tables power course conversions by default.
                Reverse conversions and meter-to-meter comparisons use ratios of
                those factors and are labeled as derived estimates. Unsupported
                events stay unavailable. Colorado Timing formulas are available
                under Calculation options in the converter.
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
                standards, revised October 2025. The ladder compares your input
                in its original course, age group, and published category.
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
                Optional altitude adjustments follow USA Swimming’s published
                table. They’re applied to eligible individual events before
                course conversion. Your meet’s rules still govern accepted
                entries.
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
                World Aquatics points compare entered metric swims against
                published 2026 base times. This is a separate scoring system
                from course conversion and age-group targets.
              </p>
              <a href={pointsSource.method} target="_blank" rel="noreferrer"
                >World Aquatics scoring method<Icon
                  name="external"
                  size={12}
                /></a
              >
            </div>
          </article>
        </div>
      </div>
    </details>
  </section>
  <section
    class="resources-section page-width"
    id="resources"
    aria-labelledby="resources-title"
  >
    <details bind:open={resourcesOpen}>
      <summary
        ><h2 id="resources-title">Swimming resources</h2>
        <Icon name="chevron" size={16} /></summary
      >
      <p>
        Find meet results, swimmer profiles and published sources elsewhere in
        the swimming community.
      </p>
      <div class="resource-grid">
        {#each resources as resource}
          <article>
            <h3>
              <a href={resource.url} target="_blank" rel="noreferrer"
                >{resource.name}<Icon name="external" size={12} /></a
              >
            </h3>
            <p>{resource.description}</p>
          </article>
        {/each}
      </div>
    </details>
  </section>
</main>
<div class="appearance-row page-width" role="region" aria-label="Appearance">
  <Theme />
</div>
<footer class="page-width">
  <div class="footer-top">
    <a class="footer-brand wordmark" href="./" aria-label="Turnmark home"
      >turnmark<span class="brand-period">.</span></a
    >
    <p class="footer-credit">
      Built by <a
        href="https://bristanback.com"
        target="_blank"
        rel="noreferrer">Bri Stanback</a
      ><span>Open source, always.</span>
    </p>
  </div>
  <div class="footer-bottom">
    <nav class="footer-docs" aria-label="Documentation">
      <a href="#method" onclick={() => (methodologyOpen = true)}>Methodology</a
      ><a href="#resources" onclick={() => (resourcesOpen = true)}>Resources</a
      ><a href="/embed/">Widget setup</a><a href="/mcp/">MCP setup</a>
    </nav>
    <div class="footer-meta">
      <span>No account. No uploads.</span><span
        >Sources checked October 16, 2026</span
      >
    </div>
  </div>
</footer>
<nav class="mobile-nav" aria-label="Mobile navigation">
  {#each [{ id: "converter", icon: "wave", label: "Converter" }, { id: "standards", icon: "standards", label: "Standards" }, { id: "history", icon: "history", label: "History" }] as item}
    <button
      class:active={activeSection === item.id}
      aria-current={activeSection === item.id ? "location" : undefined}
      onclick={() => go(item.id)}
      ><span class="mobile-nav-icon"><Icon name={item.icon} size={21} /></span
      ><span>{item.label}</span></button
    >
  {/each}
</nav>
<div
  class="toast"
  class:visible={!!toast}
  role="status"
  aria-label="Swim action"
  aria-live="polite"
>
  {#if toast}<Icon name="check" size={17} />{toast}{/if}
</div>
