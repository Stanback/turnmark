import { McpServer } from "@modelcontextprotocol/server";
import {
  registerAppResource,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { conversionHtml } from "./generated/ui.js";

import { z } from "zod";
import type { Engine } from "@turnmark/sdk";
import {
  conversionMethod,
  conversionProvenance,
  altitudeProvenance,
} from "@turnmark/sdk/conversion";
import { youthEdition, youthAges, standardsSource } from "@turnmark/sdk/youth";
import {
  mastersEdition,
  mastersAges,
  mastersSource,
} from "@turnmark/sdk/masters";
import {
  pointsEdition,
  pointsSource,
  pointsValidity,
} from "@turnmark/sdk/points";

export const conversionResourceUri = "ui://turnmark/conversion/0.2.0.html";
const uiMeta = {
  ui: {
    csp: { connectDomains: [], resourceDomains: [], frameDomains: [] },
    prefersBorder: true,
  },
};

// Transport shape only. Rust remains responsible for time parsing, supported
// event combinations, age coverage, editions, ranges and numerical validation.
const event = z.strictObject({
  distance: z
    .number()
    .describe("Actual distance: 500 SCY corresponds to 400 SCM/LCM."),
  stroke: z.enum([
    "freestyle",
    "backstroke",
    "breaststroke",
    "butterfly",
    "individual-medley",
  ]),
  course: z.enum(["SCY", "SCM", "LCM"]),
});
const swim = z.strictObject({
  time: z
    .string()
    .describe(
      "Entered clock time, e.g. 58.32 or 1:02.45. No conversion estimates.",
    ),
  event,
});
const table = z
  .enum(["women", "men"])
  .describe("Category of the published source table.");
const provenance = z
  .object({
    id: z.string(),
    title: z.string(),
    url: z.string(),
    revision: z.string(),
  })
  .passthrough();
const outcome = z.discriminatedUnion("status", [
  z.object({
    status: z.literal("available"),
    value: z.record(z.string(), z.unknown()),
    provenance,
  }),
  z.object({
    status: z.literal("unavailable"),
    reason: z.string(),
    provenance,
  }),
  z.object({
    status: z.literal("invalid"),
    field: z.string(),
    reason: z.string(),
  }),
]);
const annotations = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
};
function result(value: Record<string, unknown>) {
  return {
    structuredContent: value,
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
  };
}

/** Fresh protocol server per connection/request; one immutable engine can be reused. */
export function createServer(engine: Engine) {
  const server = new McpServer(
    { name: "turnmark", version: "0.2.0" },
    {
      instructions:
        "Swimming calculations from published sources. Preserve available/unavailable/invalid, event/course context, published/derived kinds and source editions. Missing targets remain missing. Qualifying targets are benchmarks, not confirmation of entry eligibility. No personal history access or storage.",
    },
  );
  registerAppResource(
    server,
    "Turnmark conversion",
    conversionResourceUri,
    { mimeType: RESOURCE_MIME_TYPE, _meta: uiMeta },
    () => ({
      contents: [
        {
          uri: conversionResourceUri,
          mimeType: RESOURCE_MIME_TYPE,
          text: conversionHtml,
          _meta: uiMeta,
        },
      ],
    }),
  );
  server.registerTool(
    "convert_swim",
    {
      description:
        "Convert an entered swim to an explicit course using published NCAA factors or labeled derived reverse/cross-metric estimates.",
      inputSchema: z.strictObject({
        swim,
        to: z.enum(["SCY", "SCM", "LCM"]),
        table,
        method: z.string().optional(),
      }),
      _meta: {
        ui: {
          resourceUri: conversionResourceUri,
          visibility: ["model", "app"],
        },
      },
      outputSchema: outcome,
      annotations,
    },
    (input) =>
      result(
        engine.convert({
          ...input,
          method: input.method as typeof conversionMethod | undefined,
        }),
      ),
  );
  server.registerTool(
    "adjust_altitude",
    {
      description:
        "Adjust an entered swim at an explicit elevation using USA Swimming altitude adjustments. Separate from course conversion.",
      inputSchema: z.strictObject({
        swim,
        elevation: z.strictObject({
          value: z.number(),
          unit: z.enum(["feet", "meters"]),
        }),
      }),
      outputSchema: outcome,
      annotations,
    },
    (input) => result(engine.adjustAltitude(input)),
  );
  server.registerTool(
    "get_youth_standards",
    {
      description:
        "Look up published USA Swimming B–AAAA motivational standards for an event, category and age-group key (10u, 11-12, 13-14, 15-16, 17-18). Times are seconds.",
      inputSchema: z.strictObject({
        event,
        table,
        age: z.string(),
        edition: z.string().optional(),
      }),
      outputSchema: outcome,
      annotations,
    },
    (input) =>
      result(
        engine.youth({
          ...input,
          age: input.age as (typeof youthAges)[number],
          edition: input.edition as typeof youthEdition | undefined,
        }),
      ),
  );
  server.registerTool(
    "get_masters_target",
    {
      description:
        "Look up a 2026 USMS Nationals benchmark by event, category and age group (18-24, 25-29, five-year groups through 80-84, or 85+). Explicit NO TIME and unsupported coverage remain unavailable. Not entry eligibility.",
      inputSchema: z.strictObject({
        event,
        table,
        age: z.string(),
        edition: z.string().optional(),
      }),
      outputSchema: outcome,
      annotations,
    },
    (input) =>
      result(
        engine.masters({
          ...input,
          edition: input.edition as typeof mastersEdition | undefined,
        }),
      ),
  );
  server.registerTool(
    "get_world_points",
    {
      description:
        "Calculate World Aquatics points for the raw entered metric swim, with base time, validity and a derived next 100-point milestone. No SCY or age-adjusted points.",
      inputSchema: z.strictObject({
        swim,
        table,
        edition: z.string().optional(),
      }),
      outputSchema: outcome,
      annotations,
    },
    (input) =>
      result(
        engine.points({
          ...input,
          edition: input.edition as typeof pointsEdition | undefined,
        }),
      ),
  );
  server.registerTool(
    "get_sources",
    {
      description:
        "Return bundled engine version, methods, editions, age-group keys and source attribution. No network lookup.",
      inputSchema: z.strictObject({}),
      outputSchema: z.object({
        engineVersion: z.string(),
        conversion: z.unknown(),
        altitude: z.unknown(),
        youth: z.unknown(),
        masters: z.unknown(),
        points: z.unknown(),
      }),
      annotations,
    },
    () =>
      result({
        engineVersion: engine.version,
        conversion: conversionProvenance,
        altitude: altitudeProvenance,
        youth: {
          edition: youthEdition,
          ages: youthAges,
          source: standardsSource,
        },
        masters: {
          edition: mastersEdition,
          ages: mastersAges,
          source: mastersSource,
        },
        points: {
          edition: pointsEdition,
          source: pointsSource,
          validity: pointsValidity,
        },
      }),
  );
  return server;
}
