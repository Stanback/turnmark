<script lang="ts">
  import { onMount } from "svelte";
  import Icon from "./lib/Icon.svelte";
  import Pool from "./lib/Pool.svelte";
  import { altitudeSource, conversionSource } from "./data/conversions";
  import standardData from "./data/standards.json";
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
  let mounted = false;
  const time = $derived(parseTime(form.time));
  const altitudeValid = $derived(
    Number.isInteger(form.altitude) &&
      form.altitude >= 0 &&
      form.altitude <= 20000,
  );
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
        ? "Enter an elevation in whole feet, between 0 and 20,000."
        : time <= adjustment
          ? "The time must be longer than the altitude adjustment."
          : "",
  );
  const currentLabel = $derived(
    eventLabel(form.distance, form.course, form.stroke),
  );

  onMount(() => {
    form = readState(window.location.hash);
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
    mounted = true;
    const hashChange = () => {
      if (window.location.hash.startsWith("#t="))
        form = readState(window.location.hash);
    };
    window.addEventListener("hashchange", hashChange);
    return () => {
      clearTimeout(toastTimer);
      window.removeEventListener("hashchange", hashChange);
    };
  });
  function notify(message: string) {
    toast = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ""), 3500);
  }
  function go(id: string) {
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
    history.replaceState(null, "", location.pathname + location.search);
    notify("Back to the starting block.");
  }
  async function share() {
    if (error) return;
    const url = `${location.origin}${location.pathname}#${stateHash(form)}`;
    try {
      await navigator.clipboard.writeText(url);
      history.replaceState(null, "", url);
      notify("Link copied. Same swim, ready to share.");
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
      ["Standards source", standardData.source.url],
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

<svelte:head><title>Turnmark — Your swim. Any course.</title></svelte:head>
<a class="skip-link" href="#main">Skip to converter</a>
<header class="site-header">
  <div class="header-inner">
    <a class="wordmark" href="./" aria-label="Turnmark home"
      ><span class="brand-icon"><Icon name="turn" size={25} /></span
      >turnmark<span class="brand-period">.</span></a
    >
    <nav aria-label="Main navigation">
      <button class="nav-current" onclick={() => go("converter")}
        >Converter</button
      ><button onclick={() => go("standards")}>Time standards</button><button
        onclick={() => go("method")}>The method</button
      >
    </nav>
    <a
      class="github-link"
      href="https://github.com/Stanback/turnmark"
      target="_blank"
      rel="noreferrer"
      ><Icon name="github" size={18} /><span>Open source</span><Icon
        name="external"
        size={13}
      /></a
    >
  </div>
</header>
<main id="main">
  <section class="intro page-width" aria-labelledby="page-title">
    <div class="intro-copy">
      <div class="eyebrow">
        <span></span>A FRESH PERSPECTIVE ON YOUR PERSONAL BEST
      </div>
      <h1 id="page-title">
        Your swim.<br />Any
        <span class="course-word"
          >course<svg viewBox="0 0 320 15" aria-hidden="true"
            ><path d="M3 9q140-14 312-2" /></svg
          ></span
        >.
      </h1>
      <p>
        Different pool. Same potential. Convert your time,<br
          class="desktop-break"
        /> find your next goal, and make every turn count.
      </p>
    </div>
    <div class="intro-aside">
      <div class="watermark-number" aria-hidden="true">01<span>/ 03</span></div>
      <p>25 yards. 25 meters. 50 meters.<br />One clearer picture.</p>
      <div class="privacy-note">
        <span class="status-dot"></span>All in your browser. All yours.
      </div>
    </div>
  </section>

  <section
    id="converter"
    class="workspace page-width"
    aria-label="Swim time converter"
  >
    <div class="input-panel">
      <div class="section-label">
        <span class="section-number">01</span>THE STARTING BLOCK<button
          class="text-button reset"
          onclick={reset}>Reset</button
        >
      </div>
      <div class="panel-title">
        <h2>Tell us about your swim.</h2>
        <p>We’ll take it from here.</p>
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
        <label for="category"
          >Factor table <span>for course conversion</span></label
        >
        <div class="select-wrap">
          <select id="category" bind:value={form.category}
            ><option value="women">Women / girls</option><option value="men"
              >Men / boys</option
            ></select
          ><Icon name="chevron" size={13} />
        </div>
      </div>
      <details class="altitude-options">
        <summary
          ><span><Icon name="mountain" size={17} />Swam at altitude?</span><span
            class="summary-plus">+</span
          ></summary
        >
        <div class="altitude-body">
          <label for="altitude"
            >Pool elevation <span>feet above sea level</span></label
          ><input
            type="number"
            id="altitude"
            min="0"
            max="20000"
            step="1"
            bind:value={form.altitude}
          />
          <p>
            {adjustment
              ? `${adjustment.toFixed(2)} seconds subtracted before conversion.`
              : "Adjustments begin at 3,000 ft for eligible events of 200 or longer."}
          </p>
        </div>
      </details>
      <div class="input-footnote">
        <Icon name="info" size={14} /><span
          >Estimates for perspective. Meet rules decide entry eligibility.</span
        >
      </div>
    </div>

    <div class="results-panel">
      <div class="results-heading">
        <div>
          <div class="section-label">
            <span class="section-number">02</span>A CHANGE OF SCENERY
          </div>
          <h2>See the other side of the wall.</h2>
        </div>
        <span class="method-chip">NCAA factors <span>↗</span></span>
      </div>
      <div class="pool-scene">
        <div class="pool-scene-top">
          <div>
            <span class="tiny-label">IN FOCUS</span>
            <h3>
              {eventLabel(form.distance, focus, form.stroke)}
              <span>· {focus}</span>
            </h3>
          </div>
          <div class="pool-scene-caption">
            {courseInfo[focus].name}<span
              >{focused.kind === "swum"
                ? "Your entered course"
                : "A different kind of fast"}</span
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
                    : "YOUR SWIM"
                  : "ESTIMATE"}</span
              >
            </div>
            <div class="result-time" data-testid={`result-${result.course}`}>
              {formatTime(result.time)}
            </div>
            <div class="result-card-bottom">
              <span
                >{eventLabel(form.distance, result.course, form.stroke)}
                <span class="result-unit"
                  >{result.course === "SCY" ? "yd" : "m"}</span
                ></span
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
              ? `Your entered ${formatTime(time)} swim, less ${adjustment.toFixed(2)}s for altitude.`
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

  <section
    class="standards-section page-width"
    id="standards"
    aria-labelledby="standards-title"
  >
    <div class="standards-title-row">
      <div>
        <div class="section-label">
          <span class="section-number">03</span>THE NEXT PERSONAL BEST
        </div>
        <h2 id="standards-title">A little context. A new target.</h2>
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
        <span class="context-pill">{currentLabel} · {form.course}</span><span
          >{form.category === "women" ? "Girls" : "Boys"} · {ages.find(
            (a) => a.id === form.age,
          )?.label} <span class="context-divider">/</span>
          {adjustment ? "Altitude-adjusted input" : "Your entered course"}</span
        ><a href={standardData.source.url} target="_blank" rel="noreferrer"
          >Official table<Icon name="external" size={12} /></a
        >
      </div>
      {#if thresholds && standing && correctedTime !== null}<div
          class="standard-summary"
        >
          <div class="standard-achievement">
            <span class="achievement-badge"
              >{standing.achieved >= 0 ? levels[standing.achieved] : "→"}</span
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
                  to your next mark: <strong>{levels[standing.next]}</strong> in {formatTime(
                    nextTime,
                  )}.{:else}You’ve reached the top motivational standard for
                  this event.{/if}
              </p>
            </div>
          </div>
          <div class="goal-time">
            <span class="tiny-label"
              >{standing.next !== null
                ? `NEXT UP · ${levels[standing.next]}`
                : "TOP MARK · AAAA"}</span
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
                ><strong>{levels[i]}</strong><span>{formatTime(threshold)}</span
                >
              </div>{/each}
          </div>
        </div>
        <p class="standards-note">
          {#if adjustment}Altitude-adjusted comparison; confirm eligibility with
            your meet.{:else}Compared using your entered {form.course} time. Course
            estimates above don’t count as official swims.{/if}
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
  </section>

  {#if saved.length}<section
      class="swimboard page-width"
      aria-labelledby="swimboard-title"
    >
      <div class="board-heading">
        <h2 id="swimboard-title">Your swimboard<span>{saved.length}</span></h2>
        <p>Saved on this device. Ready for another look.</p>
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
              ><Icon name="close" size={13} /></button
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
      <div class="eyebrow">A CLEARER VIEW, NOT A CRYSTAL BALL</div>
      <h2 id="method-title">Every number has<br />a starting point.</h2>
      <p>
        Turns, technique, and race-day conditions make every swim different.
        Here’s what goes into your estimate.
      </p>
      <a
        href="https://github.com/Stanback/turnmark/blob/master/docs/METHODOLOGY.md"
        target="_blank"
        rel="noreferrer"
        >Read the full methodology<Icon name="arrow" size={17} /></a
      >
    </div>
    <div class="method-items">
      <article>
        <span>01</span>
        <div>
          <h3>Published factors. Visible math.</h3>
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
        <span>02</span>
        <div>
          <h3>Real standards. A meaningful next step.</h3>
          <p>
            2,892 published times from USA Swimming’s 2024–2028 age group
            standards, revised October 2025. The ladder compares your input in
            its original course, age group, and published category.
          </p>
          <a href={standardData.source.url} target="_blank" rel="noreferrer"
            >USA Swimming motivational standards<Icon
              name="external"
              size={12}
            /></a
          >
        </div>
      </article>
      <article>
        <span>03</span>
        <div>
          <h3>A little elevation, accounted for.</h3>
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
    </div>
  </section>
  <section class="closing-strip page-width">
    <span class="closing-turn"><Icon name="turn" size={32} /></span>
    <p>
      Made for the love of the swim.<span
        >From a little PHP tool in 2013 to a fresh lap around the pool.</span
      >
    </p>
    <span class="closing-year"
      >EST. 2013<br /><strong>REIMAGINED 2026</strong></span
    >
  </section>
</main>
<footer class="page-width">
  <a class="footer-brand" href="./">turnmark.</a><span
    >Built by <a href="https://bristanback.com" target="_blank" rel="noreferrer"
      >Bri Stanback</a
    > · Open source, always.</span
  ><span>Sources checked October 16, 2026</span>
</footer>
<div class="toast" class:visible={!!toast} role="status" aria-live="polite">
  {#if toast}<Icon name="check" size={17} />{toast}{/if}
</div>
