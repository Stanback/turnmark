<script lang="ts">
  import {
    caveatText,
    ncaaMethodExplanation,
    empiricalMethodExplanation,
    empiricalCalculationNote,
    poolLengthExplanation,
    methodComparisonCaveat,
  } from "./calculation-copy";
  import AltitudeComparison from "./AltitudeComparison.svelte";
  import {
    type Converter,
    conversionMethods,
    type ConversionRequest,
    type ConversionMethod,
  } from "@turnmark/sdk/converter";

  let {
    converter,
    request,
    selected,
    adjusted = false,
    onSelect,
  }: {
    converter: Pick<Converter, "convert" | "adjustAltitude" | "parseTime">;
    request: ConversionRequest;
    selected: ConversionMethod;
    adjusted?: boolean;
    onSelect?: (method: ConversionMethod) => void;
  } = $props();

  function formatHundredthsToClock(hundredths: number): string {
    const safe = Math.max(1, Math.round(hundredths));
    const totalSeconds = Math.floor(safe / 100);
    const cs = safe % 100;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const csStr = String(cs).padStart(2, "0");
    return minutes > 0
      ? `${minutes}:${String(seconds).padStart(2, "0")}.${csStr}`
      : `${seconds}.${csStr}`;
  }

  function formatSignedDelta(deltaHundredths: number): string {
    if (deltaHundredths === 0) return "0.00s vs NCAA";
    const sign = deltaHundredths > 0 ? "+" : "−";
    return `${sign}${(Math.abs(deltaHundredths) / 100).toFixed(2)}s vs NCAA`;
  }

  function poolLengthForCourse(course: "SCY" | "SCM" | "LCM"): number {
    return course === "LCM" ? 50 : 25;
  }

  const comparisons = $derived(
    conversionMethods.map((method) => ({
      ...method,
      shortLabel:
        method.id === "ncaa-2025-27"
          ? "NCAA"
          : method.id === "colorado-teamunify-2026"
            ? "Colorado"
            : "Equivalence",
      result: converter.convert({ ...request, method: method.id }),
    })),
  );
  const chosen = $derived(comparisons.find((item) => item.id === selected)!);
  // One note per distinct engine caveat across the compared methods.
  const caveatNotes = $derived([
    ...new Set(
      comparisons.flatMap((item) =>
        item.result.status === "available" && item.result.value.caveat
          ? [caveatText(item.result.value.caveat)]
          : [],
      ),
    ),
  ]);
  const ncaaHundredths = $derived(
    comparisons[0]?.result.status === "available"
      ? comparisons[0].result.value.hundredths
      : null,
  );
  const difference = $derived.by(() => {
    const a = comparisons[0]?.result;
    const b =
      selected === "turnmark-empirical-2026"
        ? chosen?.result
        : comparisons[1]?.result;
    return a?.status === "available" && b?.status === "available"
      ? (Math.abs(a.value.hundredths - b.value.hundredths) / 100).toFixed(2)
      : null;
  });

  const geometry = $derived.by(() => {
    if (chosen?.result.status !== "available") return null;
    const srcEvent = request.swim.event;
    const dstEvent = chosen.result.value.event;
    const srcPool = poolLengthForCourse(srcEvent.course);
    const dstPool = poolLengthForCourse(dstEvent.course);
    const srcLengths = Math.round(srcEvent.distance / srcPool);
    const dstLengths = Math.round(dstEvent.distance / dstPool);
    const srcTurns = Math.max(0, srcLengths - 1);
    const dstTurns = Math.max(0, dstLengths - 1);
    const turnDelta = dstTurns - srcTurns;
    return {
      srcDistance: srcEvent.distance,
      srcCourse: srcEvent.course,
      srcUnit: srcEvent.course === "SCY" ? "yd" : "m",
      srcLengths,
      srcTurns,
      dstDistance: dstEvent.distance,
      dstCourse: dstEvent.course,
      dstUnit: dstEvent.course === "SCY" ? "yd" : "m",
      dstLengths,
      dstTurns,
      turnDelta,
      sameCourse: srcEvent.course === dstEvent.course,
    };
  });

  const spectrum = $derived.by(() => {
    const avail = comparisons.filter(
      (
        item,
      ): item is typeof item & {
        result: Extract<typeof item.result, { status: "available" }>;
      } => item.result.status === "available",
    );
    if (avail.length < 2 || request.swim.event.course === request.to) {
      return null;
    }
    const times = avail.map((item) => item.result.value.hundredths);
    const minH = Math.min(...times);
    const maxH = Math.max(...times);
    const spanH = maxH - minH;
    return {
      minTime: formatHundredthsToClock(minH),
      maxTime: formatHundredthsToClock(maxH),
      spreadSeconds: (spanH / 100).toFixed(2),
      nodes: avail.map((item, idx) => {
        const h = item.result.value.hundredths;
        const pct =
          spanH > 0 ? 10 + ((h - minH) / spanH) * 80 : 25 + idx * 25;
        const deltaH = ncaaHundredths !== null ? h - ncaaHundredths : 0;
        return {
          id: item.id,
          label: item.label.replace(" (default)", ""),
          shortLabel: item.shortLabel,
          time: item.result.value.time,
          pct,
          deltaText:
            item.id === "ncaa-2025-27"
              ? "NCAA baseline"
              : formatSignedDelta(deltaH),
          selected: item.id === selected,
        };
      }),
    };
  });

  const paceExplorer = $derived.by(() => {
    if (
      chosen?.result.status !== "available" ||
      comparisons[0]?.result.status !== "available" ||
      request.swim.event.course === request.to
    ) {
      return null;
    }
    // Sample around the entered swim itself; each sample is converted by the
    // engine with the same request, so altitude is still applied once.
    const enteredSeconds = converter.parseTime(request.swim.time);
    if (enteredSeconds === null) return null;
    const estSourceH = Math.round(enteredSeconds * 100);
    if (!Number.isFinite(estSourceH) || estSourceH < 1500) return null;

    const scales = [
      0.88, 0.9, 0.92, 0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06, 1.08, 1.1,
      1.12,
    ];
    const samples: {
      scale: number;
      inputClock: string;
      ncaaTime: string;
      colTime: string | null;
      empTime: string;
      empDeltaS: number;
      colDeltaS: number | null;
    }[] = [];

    for (const sc of scales) {
      const sampleH = Math.max(1500, Math.round(estSourceH * sc));
      const clock = formatHundredthsToClock(sampleH);
      const baseReq = {
        ...request,
        swim: { ...request.swim, time: clock },
      };
      const rNcaa = converter.convert({ ...baseReq, method: "ncaa-2025-27" });
      const rCol = converter.convert({
        ...baseReq,
        method: "colorado-teamunify-2026",
      });
      const rEmp = converter.convert({
        ...baseReq,
        method: "turnmark-empirical-2026",
      });
      if (rNcaa.status !== "available" || rEmp.status !== "available") continue;
      samples.push({
        scale: sc,
        inputClock: clock,
        ncaaTime: rNcaa.value.time,
        colTime: rCol.status === "available" ? rCol.value.time : null,
        empTime: rEmp.value.time,
        empDeltaS: (rEmp.value.hundredths - rNcaa.value.hundredths) / 100,
        colDeltaS:
          rCol.status === "available"
            ? (rCol.value.hundredths - rNcaa.value.hundredths) / 100
            : null,
      });
    }
    if (samples.length < 5) return null;

    const allDeltas = samples.flatMap((s) =>
      s.colDeltaS !== null ? [0, s.empDeltaS, s.colDeltaS] : [0, s.empDeltaS],
    );
    const maxAbs = Math.max(0.4, ...allDeltas.map((d) => Math.abs(d))) * 1.18;
    const W = 340;
    const H = 96;
    const padX = 24;
    const padY = 16;
    const xAt = (idx: number) =>
      padX + (idx / Math.max(1, samples.length - 1)) * (W - padX * 2);
    const yAt = (val: number) =>
      H / 2 - (val / maxAbs) * (H / 2 - padY);

    const empPoints = samples
      .map((s, i) => `${xAt(i).toFixed(1)},${yAt(s.empDeltaS).toFixed(1)}`)
      .join(" ");
    const colSamples = samples.filter((s) => s.colDeltaS !== null);
    const colPoints =
      colSamples.length === samples.length
        ? samples
            .map(
              (s, i) =>
                `${xAt(i).toFixed(1)},${yAt(s.colDeltaS ?? 0).toFixed(1)}`,
            )
            .join(" ")
        : null;

    const midIdx = samples.findIndex((s) => s.scale === 1.0);
    const fastSample = samples.find((s) => s.scale === 0.92) ?? samples[0];
    const currentSample =
      (midIdx >= 0 ? samples[midIdx] : null) ??
      samples[Math.floor(samples.length / 2)];
    const slowSample =
      samples.find((s) => s.scale === 1.08) ?? samples[samples.length - 1];

    return {
      W,
      H,
      zeroY: yAt(0),
      empPoints,
      colPoints,
      markerX: xAt(midIdx >= 0 ? midIdx : Math.floor(samples.length / 2)),
      markerY: yAt(currentSample.empDeltaS),
      maxLabel: `+${maxAbs.toFixed(1)}s`,
      minLabel: `−${maxAbs.toFixed(1)}s`,
      strip: [
        { label: "Faster (−8%)", sample: fastSample, isCurrent: false },
        { label: "Your swim", sample: currentSample, isCurrent: true },
        { label: "Slower (+8%)", sample: slowSample, isCurrent: false },
      ],
    };
  });
</script>

<section
  class="method-comparison"
  aria-label={`Compare methods in ${request.to}`}
>
  <div class="comparison-header">
    <h3>Compare methods · {request.to}</h3>
    {#if geometry && !geometry.sameCourse}
      <p class="course-geometry" aria-label="Course turn geometry">
        <span>
          {geometry.srcDistance}
          {geometry.srcUnit}
          {geometry.srcCourse} ({geometry.srcLengths}
          {geometry.srcLengths === 1 ? "length" : "lengths"} · {geometry.srcTurns}
          {geometry.srcTurns === 1 ? "turn" : "turns"})
        </span>
        <span aria-hidden="true">→</span>
        <span>
          {geometry.dstDistance}
          {geometry.dstUnit}
          {geometry.dstCourse} ({geometry.dstLengths}
          {geometry.dstLengths === 1 ? "length" : "lengths"} · {geometry.dstTurns}
          {geometry.dstTurns === 1 ? "turn" : "turns"})
        </span>
        {#if geometry.turnDelta !== 0}
          <strong class="turn-delta">
            {geometry.turnDelta > 0 ? `+${geometry.turnDelta}` : `−${Math.abs(geometry.turnDelta)}`}
            {Math.abs(geometry.turnDelta) === 1 ? "wall" : "walls"}
          </strong>
        {/if}
      </p>
    {/if}
  </div>

  {#if spectrum}
    <div class="method-spectrum" aria-label="Relative time spectrum across conversion methods">
      <div class="spectrum-labels">
        <span>Faster ({spectrum.minTime})</span>
        <span class="spectrum-spread">Method spread: {spectrum.spreadSeconds}s</span>
        <span>Slower ({spectrum.maxTime})</span>
      </div>
      <div class="spectrum-track">
        <div class="spectrum-rail"></div>
        {#each spectrum.nodes as node}
          <button
            type="button"
            class="spectrum-pin"
            class:selected={node.selected}
            style={`left: ${node.pct.toFixed(1)}%`}
            disabled={!onSelect}
            onclick={() => onSelect?.(node.id)}
            title={`${node.label}: ${node.time} (${node.deltaText})`}
          >
            <span class="pin-dot" aria-hidden="true"></span>
            <span class="pin-name">{node.shortLabel}</span>
            <span class="pin-time">{node.time}</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <dl>
    {#each comparisons as item}
      {@const val = item.result.status === "available" ? item.result.value : null}
      {@const deltaH =
        val !== null && ncaaHundredths !== null
          ? val.hundredths - ncaaHundredths
          : null}
      <div
        data-method={item.id}
        class:selected-row={item.id === selected}
      >
        <dt>
          <span class="method-title">
            {item.label.replace(" (default)", "")}{#if item.id === selected}<span
                class="selected-badge">Selected</span
              >{/if}
          </span>
          {#if val !== null && val.kind !== "swum"}
            <span class="method-formula">
              × {val.factor.toFixed(5)}{val.offsetSeconds
                ? ` ${val.offsetSeconds > 0 ? "+" : "−"} ${Math.abs(val.offsetSeconds).toFixed(2)}s`
                : ""}
              {#if item.id === "turnmark-empirical-2026"}
                · equivalent time
              {:else if item.id === "colorado-teamunify-2026"}
                · fixed turn offset
              {:else}
                · flat multiplier
              {/if}
            </span>
          {/if}
        </dt>
        <dd>
          {#if item.result.status === "available"}
            <div class="method-time-row">
              {#if deltaH !== null && request.swim.event.course !== request.to}
                <span
                  class="delta-badge"
                  class:delta-faster={deltaH < 0}
                  class:delta-slower={deltaH > 0}
                >
                  {item.id === "ncaa-2025-27"
                    ? "NCAA baseline"
                    : formatSignedDelta(deltaH)}
                </span>
              {/if}
              <strong>{item.result.value.time}</strong>
            </div>
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
  {#each caveatNotes as note}<p class="distance-caveat">{note}</p>{/each}
  {#if difference !== null}<p class="method-gap">
      Method difference: <strong>{difference}s</strong>
    </p>{/if}
  <p>{methodComparisonCaveat}</p>

  {#if paceExplorer}
    <div class="pace-explorer" aria-label="Equivalent time compared with NCAA across paces">
      <div class="pace-explorer-head">
        <h4>Equivalent time vs. NCAA across paces</h4>
        <span>Each point converts an entered time up to 12% faster or slower and subtracts the NCAA conversion of that same time.</span>
      </div>
      <p class="pace-legend" aria-hidden="true">
        <span class="pace-key pace-key-emp">Equivalence</span>
        {#if paceExplorer.colPoints}<span class="pace-key pace-key-col"
            >Colorado</span
          >{/if}
      </p>
      <svg
        class="pace-chart"
        viewBox={`0 0 ${paceExplorer.W} ${paceExplorer.H}`}
        role="img"
        aria-label={`Difference from the NCAA conversion for Turnmark Equivalence${paceExplorer.colPoints ? " and Colorado Timing" : ""} across faster and slower swims`}
      >
        <line
          x1="24"
          y1={paceExplorer.zeroY}
          x2={paceExplorer.W - 24}
          y2={paceExplorer.zeroY}
          class="pace-zero-line"
        />
        {#if paceExplorer.colPoints}
          <polyline
            fill="none"
            points={paceExplorer.colPoints}
            class="pace-col-line"
          />
        {/if}
        <polyline
          fill="none"
          points={paceExplorer.empPoints}
          class="pace-emp-line"
        />
        <circle
          cx={paceExplorer.markerX}
          cy={paceExplorer.markerY}
          r="4.5"
          class="pace-current-dot"
        />
        <text x="24" y="12" class="pace-axis-label">Faster pace</text>
        <text
          x={paceExplorer.W - 24}
          y="12"
          text-anchor="end"
          class="pace-axis-label">Slower pace</text
        >
        <text
          x="24"
          y={paceExplorer.zeroY - 4}
          class="pace-zero-label">NCAA 0.00s</text
        >
      </svg>
      <div class="pace-strip">
        {#each paceExplorer.strip as col}
          <div class="pace-cell" class:current={col.isCurrent}>
            <span class="pace-cell-title">{col.label}</span>
            <span class="pace-cell-input">In: {col.sample.inputClock}</span>
            <span class="pace-cell-emp">
              Equivalence: <strong>{col.sample.empTime}</strong>
              <small>
                ({col.sample.empDeltaS >= 0 ? "+" : "−"}{Math.abs(
                  col.sample.empDeltaS,
                ).toFixed(2)}s vs NCAA)
              </small>
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  {#if request.elevation}<AltitudeComparison
      {converter}
      swim={request.swim}
      elevation={request.elevation}
      selected={request.altitudePolicy ?? "usa-swimming-altitude-2026"}
    />{/if}
  <h3>Why the times differ</h3>
  <div class="explanations">
    <div>
      <h4>NCAA</h4>
      <p>{ncaaMethodExplanation}</p>
    </div>
    <div>
      <h4>Colorado Timing</h4>
      <p>
        Documented multipliers plus fixed time offsets. The formulas vary by
        event and course, not age or category.
      </p>
    </div>
    <div>
      <h4>Turnmark Equivalence</h4>
      <p>{empiricalMethodExplanation}</p>
    </div>
    <div>
      <h4>Pool length</h4>
      <p>{poolLengthExplanation}</p>
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
            : chosen.id === "turnmark-empirical-2026"
              ? empiricalCalculationNote
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
            : item.id === "turnmark-empirical-2026"
              ? "Turnmark Equivalence report"
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
  .comparison-header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px 16px;
    margin: 20px 0 12px;
  }
  h3 {
    color: var(--tm-color-text);
    font: inherit;
    font-weight: 650;
    margin: 20px 0 10px;
  }
  .comparison-header h3 {
    margin: 0;
  }
  .course-geometry {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 8px;
    margin: 0;
    padding: 4px 10px;
    border-radius: var(--tm-radius-control);
    border: 1px solid var(--tm-color-border-subtle);
    background: var(--tm-color-surface);
    font-size: 0.775rem;
    font-variant-numeric: tabular-nums;
  }
  .turn-delta {
    color: var(--tm-color-accent);
    font-weight: 650;
  }
  .method-spectrum {
    margin: 0 0 14px;
    padding: 12px 14px 16px;
    border-radius: var(--tm-radius-control);
    border: 1px solid var(--tm-color-border-subtle);
    background: var(--tm-color-surface);
  }
  .spectrum-labels {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
    margin-bottom: 12px;
  }
  .spectrum-spread {
    color: var(--tm-color-text);
    font-weight: 600;
  }
  .spectrum-track {
    position: relative;
    height: 46px;
  }
  .spectrum-rail {
    position: absolute;
    left: 8%;
    right: 8%;
    top: 8px;
    height: 3px;
    border-radius: 3px;
    background: var(--tm-color-border-subtle);
  }
  .spectrum-pin {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 0 4px;
    border: 0;
    background: transparent;
    color: var(--tm-color-text-muted);
    font: inherit;
    cursor: pointer;
  }
  .spectrum-pin:disabled {
    cursor: default;
  }
  .pin-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--tm-color-border-control);
    background: var(--tm-color-surface);
  }
  .spectrum-pin.selected .pin-dot {
    border-color: var(--tm-color-result-highlight);
    background: var(--tm-color-result-highlight);
  }
  .pin-name {
    font-size: 0.7rem;
    font-weight: 650;
    color: var(--tm-color-text);
    white-space: nowrap;
  }
  .pin-time {
    font-size: 0.72rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .spectrum-pin.selected .pin-time {
    color: var(--tm-color-result-highlight);
    font-weight: 650;
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
    padding: 10px 8px;
    border-bottom: 1px solid var(--tm-color-border-subtle);
    border-radius: var(--tm-radius-control);
  }
  dl > div.selected-row {
    background: color-mix(
      in srgb,
      var(--tm-color-selected-surface) 55%,
      transparent
    );
  }
  dt {
    display: flex;
    flex-direction: column;
    gap: 2px;
    color: var(--tm-color-text);
  }
  .method-title {
    font-weight: 600;
  }
  .selected-badge {
    display: inline-block;
    margin-inline-start: 8px;
    font-size: 0.75rem;
    color: var(--tm-color-accent);
  }
  .method-formula {
    font-size: 0.75rem;
    color: var(--tm-color-text-muted);
    font-variant-numeric: tabular-nums;
  }
  dd {
    display: grid;
    justify-items: end;
    margin: 0;
  }
  .method-time-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
  .delta-badge {
    font-size: 0.72rem;
    font-variant-numeric: tabular-nums;
    padding: 1px 6px;
    border-radius: 6px;
    border: 1px solid var(--tm-color-border-subtle);
    color: var(--tm-color-text-muted);
  }
  .delta-badge.delta-faster {
    color: var(--tm-color-result-highlight);
    border-color: color-mix(
      in srgb,
      var(--tm-color-result-highlight) 45%,
      var(--tm-color-border-subtle)
    );
  }
  .delta-badge.delta-slower {
    color: var(--tm-color-accent);
    border-color: color-mix(
      in srgb,
      var(--tm-color-accent) 45%,
      var(--tm-color-border-subtle)
    );
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
  .pace-explorer {
    margin: 16px 0;
    padding: 12px 14px;
    border-radius: var(--tm-radius-control);
    border: 1px solid var(--tm-color-border-subtle);
    background: var(--tm-color-surface);
  }
  .pace-explorer-head {
    display: grid;
    gap: 2px;
    margin-bottom: 8px;
  }
  .pace-explorer-head span {
    font-size: 0.775rem;
  }
  .pace-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin: 0;
    font-size: 0.72rem;
  }
  .pace-key {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .pace-key::before {
    content: "";
    width: 16px;
    border-top: 2.25px solid var(--tm-color-accent);
  }
  .pace-key-col::before {
    border-top: 1.5px dashed var(--tm-color-text-muted);
  }
  .pace-chart {
    width: 100%;
    height: auto;
    max-height: 110px;
    display: block;
    margin: 6px 0 10px;
  }
  .pace-zero-line {
    stroke: var(--tm-color-border-control);
    stroke-width: 1;
    stroke-dasharray: 4 3;
  }
  .pace-col-line {
    stroke: var(--tm-color-text-muted);
    stroke-width: 1.5;
    stroke-dasharray: 2 2;
    opacity: 0.75;
  }
  .pace-emp-line {
    stroke: var(--tm-color-accent);
    stroke-width: 2.25;
  }
  .pace-current-dot {
    fill: var(--tm-color-result-highlight);
    stroke: var(--tm-color-surface);
    stroke-width: 1.5;
  }
  .pace-axis-label,
  .pace-zero-label {
    fill: var(--tm-color-text-muted);
    font-size: 9px;
  }
  .pace-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .pace-cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px;
    border-radius: 8px;
    border: 1px solid var(--tm-color-border-subtle);
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
  }
  .pace-cell.current {
    border-color: var(--tm-color-accent);
    background: color-mix(
      in srgb,
      var(--tm-color-selected-surface) 55%,
      transparent
    );
  }
  .pace-cell-title {
    font-weight: 650;
    color: var(--tm-color-text);
  }
  .pace-cell-emp strong {
    color: var(--tm-color-text);
  }
  .pace-cell-emp small {
    display: block;
    font-size: 0.7rem;
  }
  @media (max-width: 520px) {
    .pace-strip {
      grid-template-columns: minmax(0, 1fr);
    }
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
