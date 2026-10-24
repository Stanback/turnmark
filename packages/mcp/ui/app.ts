import {
  caveatText,
  formulaText,
  ncaaMethodExplanation,
  empiricalMethodExplanation,
  empiricalCalculationNote,
  poolLengthExplanation,
  methodComparisonCaveat,
} from "../../../src/lib/calculation-copy.js";
import { elevationDisplay } from "../../../src/lib/elevation-display.js";
import { placeSpectrumLabels } from "../../../src/lib/spectrum-layout.js";
import { App } from "@modelcontextprotocol/ext-apps";
import swimIcons from "../../../design/swim-icons.json";
import type {
  ConversionRequest,
  ConversionValue,
  Result,
} from "@turnmark/sdk/conversion";

const app = new App({ name: "Turnmark conversion", version: "0.3.0" }, {});
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const form = $("convert");
const time = $<HTMLInputElement>("time");
const course = $<HTMLSelectElement>("course");
const method = $<HTMLSelectElement>("method");
const altitudeEnabled = $<HTMLInputElement>("altitude-enabled");
const elevation = $<HTMLInputElement>("elevation");
const elevationUnit = $<HTMLSelectElement>("elevation-unit");
let previousElevationUnit: "feet" | "meters" = "feet";
elevationUnit.onchange = () => {
  const next = elevationUnit.value as "feet" | "meters";
  elevation.value = String(
    elevationDisplay(elevation.valueAsNumber, previousElevationUnit, next),
  );
  previousElevationUnit = next;
};
const altitudePolicy = $<HTMLSelectElement>("altitude-policy");
altitudeEnabled.onchange = () => {
  $("altitude-fields").hidden = !altitudeEnabled.checked;
};
const update = $<HTMLButtonElement>("update");
const cancel = $<HTMLButtonElement>("cancel");
const status = $("status");
const result = $("result");
let original: ConversionRequest | undefined;
let committed: ConversionRequest | undefined;
let pending: AbortController | undefined;
let generation = 0;
let connected = false;
const strokes = {
  freestyle: "Freestyle",
  backstroke: "Backstroke",
  breaststroke: "Breaststroke",
  butterfly: "Butterfly",
  "individual-medley": "IM",
};
function context(
  event: ConversionRequest["swim"]["event"],
  table: ConversionRequest["table"],
) {
  return `${event.distance} ${event.course === "SCY" ? "yd" : "m"} ${strokes[event.stroke]} · ${event.course} · ${table === "women" ? "Women" : "Men"}`;
}
function message(text: string) {
  status.textContent = text;
}
function swimIcon(name: keyof typeof swimIcons) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "swim-icon");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.65");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const path = document.createElementNS(svg.namespaceURI, "path");
  path.setAttribute("d", swimIcons[name]);
  svg.append(path);
  return svg;
}
function controls() {
  update.disabled = !connected || !original || !!pending;
  time.disabled = course.disabled = method.disabled = !original || !!pending;
  altitudeEnabled.disabled =
    elevation.disabled =
    elevationUnit.disabled =
    altitudePolicy.disabled =
      !original || !!pending;
  cancel.hidden = !pending;
  form.setAttribute("aria-busy", String(!!pending));
}
function stop() {
  generation++;
  pending?.abort();
  pending = undefined;
  controls();
}
function input(value: unknown): value is ConversionRequest {
  if (!value || typeof value !== "object") return false;
  const x = value as ConversionRequest;
  return (
    !!x.swim?.event &&
    typeof x.swim.time === "string" &&
    x.swim.time.length <= 128 &&
    ["SCY", "SCM", "LCM"].includes(x.swim.event.course) &&
    ["SCY", "SCM", "LCM"].includes(x.to) &&
    Object.hasOwn(strokes, x.swim.event.stroke) &&
    Number.isFinite(x.swim.event.distance) &&
    ["women", "men"].includes(x.table)
  );
}
// Shared layout keeps close method labels apart; before measurement each label
// falls back to the CSS position-share shift.
function layoutSpectrum(track: HTMLElement) {
  const width = track.clientWidth;
  const pins = [...track.querySelectorAll<HTMLElement>(".spectrum-pin")];
  const labels = pins.map((pin) =>
    pin.querySelector<HTMLElement>(".pin-name")!,
  );
  if (!width || labels.some((label) => !label.offsetWidth)) return;
  const xs = pins.map((pin) => pin.offsetLeft);
  const places = placeSpectrumLabels(
    labels.map((label, i) => ({ x: xs[i], width: label.offsetWidth })),
    width,
  );
  track.style.setProperty(
    "--pin-row",
    `${Math.max(...labels.map((label) => label.offsetHeight)) + 4}px`,
  );
  track.style.setProperty(
    "--label-rows",
    String(Math.max(...places.map((place) => place.row + 1))),
  );
  places.forEach((place, i) => {
    pins[i].style.setProperty("--label-row", String(place.row));
    pins[i].style.setProperty(
      "--label-shift",
      `${(place.left - xs[i]).toFixed(1)}px`,
    );
    pins[i].querySelector<HTMLElement>(".pin-leader")!.hidden = place.row === 0;
  });
}

function render(value: unknown, request: ConversionRequest) {
  if (!value || typeof value !== "object" || !("status" in value))
    throw new Error("Missing result");
  const outcome = value as Result<ConversionValue>;
  const content = document.createDocumentFragment();
  function line(tag: string, text: string, className?: string) {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    content.append(node);
    return node;
  }
  if (outcome.status === "available") {
    const v = outcome.value;
    if (
      typeof v?.time !== "string" ||
      !["swum", "published", "derived"].includes(v.kind) ||
      !input({ ...request, swim: { ...request.swim, event: v.event } })
    )
      throw new Error("Invalid result");
    line("p", "EQUIVALENT TIME", "eyebrow");
    line("h1", context(v.event, request.table), "context").prepend(
      swimIcon(v.event.stroke),
    );
    const clock = line("p", "", "clock");
    const dot = v.time.lastIndexOf(".");
    if (dot >= 0) {
      clock.append(document.createTextNode(v.time.slice(0, dot)));
      const hundredths = document.createElement("span");
      hundredths.className = "hundredths";
      hundredths.textContent = v.time.slice(dot);
      clock.append(hundredths);
    } else clock.textContent = v.time;
    line(
      "p",
      {
        swum:
          (v.altitude?.value.adjustmentSeconds ?? 0) > 0
            ? "Sea-level estimate"
            : "Original time",
        published: "Published conversion",
        derived: "Derived estimate",
      }[v.kind] +
        (v.kind !== "swum" && request.method === "colorado-teamunify-2026"
          ? " · Colorado Timing"
          : v.kind !== "swum" && request.method === "turnmark-empirical-2026"
            ? " · Turnmark Equivalence"
            : ""),
      "kind",
    );
    if (v.caveat) line("p", caveatText(v.caveat), "muted");
    line(
      "p",
      "Converted times are estimates. Check your meet’s entry rules.",
      "muted",
    );
    line(
      "p",
      `From ${request.swim.time} · ${context(request.swim.event, request.table)}`,
      "muted",
    );
  } else if (outcome.status === "unavailable") {
    line("h1", "No conversion for this selection", "context");
    line(
      "p",
      "This event or course isn’t covered by the selected published method. Ask for another event or comparison course.",
      "muted",
    );
  } else if (outcome.status === "invalid") {
    line("h1", "Check your swim", "context");
    line(
      "p",
      outcome.reason === "invalid-time"
        ? "Enter seconds or a time like 58.32 or 1:02.45."
        : "Ask your assistant to check the original event, course, category and conversion method.",
      "muted",
    );
  } else throw new Error("Unknown result");
  if (outcome.status !== "invalid") {
    const source = outcome.provenance;
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "How this is calculated";
    details.append(summary);
    const p = document.createElement("p");
    p.textContent = `${source.title} · ${source.id} · ${source.revision}`;
    const comparison = value as {
      event?: { distance: number; course: string };
      methodComparison?: {
        method: string;
        label: string;
        result: Result<ConversionValue>;
      }[];
      methodDifferenceSeconds?: number;
    };
    if (Array.isArray(comparison.methodComparison)) {
      const heading = document.createElement("h2");
      heading.textContent = `Compare methods · ${request.to}`;
      details.append(heading);
      const validMethods = comparison.methodComparison.filter((item) =>
        [
          "ncaa-2025-27",
          "colorado-teamunify-2026",
          "turnmark-empirical-2026",
        ].includes(item.method),
      );
      const ncaaEntry = validMethods.find(
        (item) => item.method === "ncaa-2025-27",
      );
      const ncaaH =
        ncaaEntry?.result.status === "available"
          ? ncaaEntry.result.value.hundredths
          : null;
      if (
        comparison.event &&
        request.swim?.event &&
        request.swim.event.course !== comparison.event.course
      ) {
        const srcPool = request.swim.event.course === "LCM" ? 50 : 25;
        const dstPool = comparison.event.course === "LCM" ? 50 : 25;
        const srcTurns = Math.max(
          0,
          Math.round(request.swim.event.distance / srcPool) - 1,
        );
        const dstTurns = Math.max(
          0,
          Math.round(comparison.event.distance / dstPool) - 1,
        );
        const turnDelta = dstTurns - srcTurns;
        const geo = document.createElement("p");
        geo.className = "course-geometry";
        geo.textContent = `${request.swim.event.distance} ${request.swim.event.course === "SCY" ? "yd" : "m"} ${request.swim.event.course} (${srcTurns} ${srcTurns === 1 ? "turn" : "turns"}) → ${comparison.event.distance} ${comparison.event.course === "SCY" ? "yd" : "m"} ${comparison.event.course} (${dstTurns} ${dstTurns === 1 ? "turn" : "turns"})${turnDelta !== 0 ? ` · ${turnDelta > 0 ? `+${turnDelta}` : `−${Math.abs(turnDelta)}`} ${Math.abs(turnDelta) === 1 ? "wall" : "walls"}` : ""}`;
        details.append(geo);
      }
      const availMethods = validMethods.filter(
        (
          item,
        ): item is typeof item & {
          result: { status: "available"; value: ConversionValue };
        } => item.result.status === "available",
      );
      if (
        availMethods.length >= 2 &&
        request.swim?.event?.course !== request.to
      ) {
        const hs = availMethods.map((item) => item.result.value.hundredths);
        const minH = Math.min(...hs);
        const maxH = Math.max(...hs);
        const spanH = maxH - minH;
        const spec = document.createElement("div");
        spec.className = "method-spectrum";
        const specTop = document.createElement("div");
        specTop.className = "spectrum-labels";
        const fastSpan = document.createElement("span");
        fastSpan.textContent = "Faster";
        const spreadSpan = document.createElement("span");
        spreadSpan.textContent = `Method spread: ${(spanH / 100).toFixed(2)}s`;
        const slowSpan = document.createElement("span");
        slowSpan.textContent = "Slower";
        specTop.append(fastSpan, spreadSpan, slowSpan);
        const track = document.createElement("div");
        track.className = "spectrum-track";
        const rail = document.createElement("div");
        rail.className = "spectrum-rail";
        track.append(rail);
        availMethods.forEach((item, idx) => {
          const pct =
            spanH > 0
              ? 10 + ((item.result.value.hundredths - minH) / spanH) * 80
              : 25 + idx * 25;
          const pin = document.createElement("div");
          pin.className = `spectrum-pin${item.method === (request.method ?? "ncaa-2025-27") ? " selected" : ""}`;
          pin.style.left = `${pct.toFixed(1)}%`;
          pin.style.setProperty("--pin-at", pct.toFixed(1));
          const dot = document.createElement("span");
          dot.className = "pin-dot";
          const leader = document.createElement("span");
          leader.className = "pin-leader";
          leader.hidden = true;
          const lbl = document.createElement("span");
          lbl.className = "pin-name";
          lbl.textContent =
            item.method === "ncaa-2025-27"
              ? "NCAA"
              : item.method === "colorado-teamunify-2026"
                ? "Colorado"
                : "Equivalence";
          pin.append(dot, leader, lbl);
          track.append(pin);
        });
        // Labels have no size until the collapsed details open, so lay them out
        // whenever the track is measured (on open, resize and text zoom).
        new ResizeObserver(() => layoutSpectrum(track)).observe(track);
        spec.append(specTop, track);
        details.append(spec);
      }
      const methods = document.createElement("dl");
      methods.className = "method-comparison";
      for (const item of validMethods) {
        const row = document.createElement("div");
        row.dataset.method = item.method;
        const name = document.createElement("dt");
        const titleSpan = document.createElement("span");
        titleSpan.textContent = `${item.label}${item.method === (request.method ?? "ncaa-2025-27") ? " · Selected" : ""}`;
        name.append(titleSpan);
        if (
          item.result.status === "available" &&
          item.result.value.kind !== "swum"
        ) {
          const formulaSpan = document.createElement("small");
          formulaSpan.className = "method-formula";
          const off = item.result.value.offsetSeconds;
          const kind = formulaText(item.result.value.formula);
          formulaSpan.textContent = `× ${item.result.value.factor.toFixed(5)}${off ? ` ${off > 0 ? "+" : "−"} ${Math.abs(off).toFixed(2)}s` : ""}${kind ? ` · ${kind}` : ""}`;
          name.append(formulaSpan);
        }
        const time = document.createElement("dd");
        if (item.result.status === "available") {
          const timeStrong = document.createElement("strong");
          timeStrong.textContent = item.result.value.time;
          time.append(timeStrong);
          if (ncaaH !== null && request.swim?.event?.course !== request.to) {
            const deltaH = item.result.value.hundredths - ncaaH;
            const deltaSmall = document.createElement("small");
            deltaSmall.className = "method-delta";
            deltaSmall.textContent =
              item.method === "ncaa-2025-27"
                ? "NCAA baseline"
                : `${deltaH >= 0 ? "+" : "−"}${(Math.abs(deltaH) / 100).toFixed(2)}s vs NCAA`;
            time.append(deltaSmall);
          }
        } else {
          time.textContent = "Unavailable for this event";
        }
        row.append(name, time);
        methods.append(row);
      }
      details.append(methods);
      const difference = document.createElement("p");
      difference.className = "method-difference";
      difference.textContent = `${typeof comparison.methodDifferenceSeconds === "number" && Number.isFinite(comparison.methodDifferenceSeconds) ? `Method difference: ${comparison.methodDifferenceSeconds.toFixed(2)}s. ` : ""}${methodComparisonCaveat}`;
      details.append(difference);
    }
    const caveats = new Set(
      (comparison.methodComparison ?? []).flatMap((item) =>
        item.result.status === "available" && item.result.value.caveat
          ? [caveatText(item.result.value.caveat)]
          : [],
      ),
    );
    for (const text of caveats) {
      const note = document.createElement("p");
      note.textContent = text;
      details.append(note);
    }
    const altitudeRows = (
      value as {
        altitudeComparison?: {
          policy: string;
          label: string;
          result: Result<{ adjustedTime: string; adjustmentSeconds: number }>;
        }[];
      }
    ).altitudeComparison;
    if (Array.isArray(altitudeRows) && request.elevation) {
      const heading = document.createElement("h2");
      heading.textContent = "Sea-level estimates";
      details.append(heading);
      const raw = document.createElement("p");
      raw.textContent = `Entered swim: ${request.swim.time} · ${request.elevation.value} ${request.elevation.unit}`;
      details.append(raw);
      for (const item of altitudeRows) {
        if (
          !["usa-swimming-altitude-2026", "ncaa-altitude-2026-27-d1"].includes(
            item.policy,
          ) ||
          item.result.status !== "available"
        )
          continue;
        const row = document.createElement("p");
        row.textContent = `${item.label.replace(" (default)", "")}${item.policy === (request.altitudePolicy ?? "usa-swimming-altitude-2026") ? " · Selected" : ""}: −${item.result.value.adjustmentSeconds.toFixed(2)}s → ${item.result.value.adjustedTime}`;
        details.append(row);
        const source = document.createElement("button");
        source.type = "button";
        source.className = "link";
        source.textContent = `${item.label.replace(" (default)", "")} altitude source ↗`;
        const url = item.result.provenance.url;
        if (typeof url === "string" && url.startsWith("https://")) {
          source.onclick = () => {
            void app
              .openLink({ url })
              .catch(() => message("This host couldn’t open the source link."));
          };
          details.append(source);
        }
      }
      const note = document.createElement("p");
      note.textContent =
        "Altitude is deducted before course conversion. Below 3,000 ft, or where the table has no deduction, the time stays unchanged. Use the policy required by your meet.";
      details.append(note);
    }
    const inputs = document.createElement("h2");
    inputs.textContent = "Why the times differ";
    details.append(inputs);
    for (const [title, text] of [
      ["NCAA", ncaaMethodExplanation],
      [
        "Colorado Timing",
        "Documented multipliers plus fixed time offsets. The formulas vary by event and course, not age or category.",
      ],
      ["Turnmark Equivalence", empiricalMethodExplanation],
      ["Pool length", poolLengthExplanation],
      [
        "Distance events",
        "500, 1000 and 1650 yards map to 400, 800 and 1500 meters.",
      ],
    ]) {
      const group = document.createElement("div");
      group.className = "calculation-explanation";
      const heading = document.createElement("h3");
      heading.textContent = title;
      const explanation = document.createElement("p");
      explanation.textContent = text;
      group.append(heading, explanation);
      details.append(group);
    }
    if (outcome.status === "available" && outcome.value.kind !== "swum") {
      const heading = document.createElement("h2");
      heading.textContent = "Selected calculation";
      details.append(heading);
      const formula = document.createElement("p");
      formula.textContent = `${outcome.value.altitude ? "After the altitude deduction, seconds" : "Seconds"} × ${outcome.value.factor.toFixed(5)}${outcome.value.offsetSeconds ? ` ${outcome.value.offsetSeconds > 0 ? "+" : "−"} ${Math.abs(outcome.value.offsetSeconds)}s` : ""}; factor rounded for display, final result truncated to hundredths.`;
      details.append(formula);
      if (request.method === "turnmark-empirical-2026") {
        const note = document.createElement("p");
        note.textContent = empiricalCalculationNote;
        details.append(note);
      }
    }
    const sourceHeading = document.createElement("h2");
    sourceHeading.textContent = "Source";
    details.append(sourceHeading, p);
    if (typeof source.url === "string" && source.url.startsWith("https://")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "link";
      button.textContent = "Open published source ↗";
      button.onclick = () => {
        void app
          .openLink({ url: source.url })
          .catch(() =>
            message(
              "This host can’t open the source link. See the source and method details above.",
            ),
          );
      };
      details.append(button);
    }
    content.append(details);
  }
  result.replaceChildren(content);
  committed = structuredClone(request);
}
app.ontoolinput = ({ arguments: args }) => {
  stop();
  if (!input(args)) {
    original = undefined;
    result.replaceChildren();
    message(
      "This card needs complete conversion inputs. Ask for a conversion with an event, course and category.",
    );
    controls();
    return;
  }
  original = structuredClone(args);
  $<HTMLDetailsElement>("calculation-options").open =
    !!args.elevation ||
    args.method === "colorado-teamunify-2026" ||
    args.method === "turnmark-empirical-2026";
  altitudeEnabled.checked = !!args.elevation;
  $("altitude-fields").hidden = !args.elevation;
  elevation.value = String(args.elevation?.value ?? 0);
  elevationUnit.value = args.elevation?.unit ?? "feet";
  previousElevationUnit = args.elevation?.unit ?? "feet";
  altitudePolicy.value =
    args.altitudePolicy === "ncaa-altitude-2026-27-d1"
      ? args.altitudePolicy
      : "usa-swimming-altitude-2026";
  time.value = args.swim.time;
  course.value = args.to;
  method.value =
    args.method === "colorado-teamunify-2026" ||
    args.method === "turnmark-empirical-2026"
      ? args.method
      : "ncaa-2025-27";
  $("original").textContent = context(args.swim.event, args.table);
  message("Waiting for the conversion…");
  controls();
};
app.ontoolresult = (response) => {
  stop();
  if (!original) return;
  try {
    render(response.structuredContent, original);
    message("");
  } catch {
    message(
      "The host returned an unreadable result. Ask for the conversion again.",
    );
  }
};
app.ontoolcancelled = () => {
  stop();
  message("Conversion cancelled. You can try again.");
};
app.onhostcontextchanged = (ctx) => theme(ctx.theme);
function theme(value?: string) {
  if (value === "light" || value === "dark") {
    document.documentElement.dataset.theme = value;
    document.documentElement.style.colorScheme = value;
  }
}
app.onteardown = async () => {
  stop();
  return {};
};
cancel.onclick = () => {
  stop();
  message("Update cancelled. The previous comparison is still shown.");
};
time.onkeydown = (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    update.click();
  }
};
update.onclick = async () => {
  if (!original || pending || !connected) return;
  const request: ConversionRequest = {
    ...original,
    swim: { ...original.swim, time: time.value.trim() },
    to: course.value as ConversionRequest["to"],
    method: method.value as ConversionRequest["method"],
  };
  delete request.elevation;
  delete request.altitudePolicy;
  if (altitudeEnabled.checked) {
    if (!Number.isFinite(elevation.valueAsNumber)) {
      message("Enter a valid pool elevation.");
      return;
    }
    request.elevation = {
      value: elevation.valueAsNumber,
      unit: elevationUnit.value as "feet" | "meters",
    };
    request.altitudePolicy =
      altitudePolicy.value as ConversionRequest["altitudePolicy"];
  }
  const controller = (pending = new AbortController());
  const id = ++generation;
  controls();
  message("Updating comparison…");
  try {
    const response = await app.callServerTool(
      { name: "convert_swim", arguments: { ...request } },
      { signal: controller.signal, timeout: 20000 },
    );
    if (id !== generation) return;
    if (response.isError) throw new Error("Tool denied");
    render(response.structuredContent, request);
    // The comparison is committed; cancellation only applies before this point.
    cancel.hidden = true;
    message("");
    try {
      await app.updateModelContext(
        {
          content: [
            {
              type: "text",
              text: `Turnmark comparison updated by the user. Inputs: ${JSON.stringify(committed)}. Result: ${JSON.stringify(response.structuredContent)}. Estimates are not recorded swims or entry eligibility.`,
            },
          ],
        },
        { signal: controller.signal, timeout: 5000 },
      );
    } catch {
      if (id === generation)
        message(
          "Comparison updated. This host couldn’t share the change with the conversation; mention it in your next message.",
        );
    }
  } catch {
    if (id === generation)
      message(
        "Couldn’t update. The previous comparison is still shown. The host may have denied the call or the service may be busy; wait a minute and retry.",
      );
  } finally {
    if (id === generation) {
      pending = undefined;
      controls();
    }
  }
};
controls();
void app
  .connect()
  .then(() => {
    connected = true;
    theme(app.getHostContext()?.theme);
    controls();
  })
  .catch(() => {
    message(
      "Open this card in an MCP Apps compatible host. The text conversion remains available in your conversation.",
    );
  });
