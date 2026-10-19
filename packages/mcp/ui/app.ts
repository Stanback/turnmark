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
        swum: "Original time",
        published: "Published conversion",
        derived: "Derived estimate",
      }[v.kind] +
        (v.kind !== "swum" && request.method === "colorado-teamunify-2026"
          ? " · Colorado Timing"
          : ""),
      "kind",
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
    details.append(p);
    const comparison = value as {
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
      const methods = document.createElement("dl");
      methods.className = "method-comparison";
      for (const item of comparison.methodComparison) {
        if (!["ncaa-2025-27", "colorado-teamunify-2026"].includes(item.method))
          continue;
        const row = document.createElement("div");
        row.dataset.method = item.method;
        const name = document.createElement("dt");
        name.textContent = `${item.label}${item.method === (request.method ?? "ncaa-2025-27") ? " · Selected" : ""}`;
        const time = document.createElement("dd");
        time.textContent =
          item.result.status === "available"
            ? item.result.value.time
            : "Unavailable for this event";
        row.append(name, time);
        methods.append(row);
      }
      details.append(methods);
      const difference = document.createElement("p");
      difference.className = "method-difference";
      difference.textContent = `${typeof comparison.methodDifferenceSeconds === "number" && Number.isFinite(comparison.methodDifferenceSeconds) ? `Method difference: ${comparison.methodDifferenceSeconds.toFixed(2)}s. ` : ""}Different conversion rules, not a prediction range or confidence interval. Follow the method required by your meet.`;
      details.append(difference);
    }
    const inputs = document.createElement("h2");
    inputs.textContent = "What goes into the calculation";
    details.append(inputs);
    for (const text of [
      "NCAA uses event- and category-specific metric-to-yards factors; reverse and SCM/LCM comparisons are derived. Colorado Timing uses event- and course-specific multipliers and fixed time offsets, without age or category inputs.",
      "Neither measures your turn technique, endurance or individual development. Pool length changes turns and distance; distance freestyle maps 500/1000/1650 yards to 400/800/1500 meters.",
      "Standards and points use the entered swim separately.",
    ]) {
      const explanation = document.createElement("p");
      explanation.textContent = text;
      details.append(explanation);
    }
    if (outcome.status === "available" && outcome.value.kind !== "swum") {
      const formula = document.createElement("p");
      formula.textContent = `Seconds × ${outcome.value.factor.toFixed(5)}${outcome.value.offsetSeconds ? ` ${outcome.value.offsetSeconds > 0 ? "+" : "−"} ${Math.abs(outcome.value.offsetSeconds)}s` : ""}; factor rounded for display, final result truncated to hundredths.`;
      details.append(formula);
    }
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
  time.value = args.swim.time;
  course.value = args.to;
  method.value =
    args.method === "colorado-teamunify-2026" ? args.method : "ncaa-2025-27";
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
