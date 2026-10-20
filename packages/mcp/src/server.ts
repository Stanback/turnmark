import { McpServer } from "@modelcontextprotocol/server";
import {
  registerAppResource,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { conversionHtml } from "./generated/ui.js";

import { z } from "zod";
import type { Engine } from "@turnmark/sdk";
import {
  conversionMethods,
  altitudePolicies,
  type ConversionMethod,
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

export const conversionResourceUri = "ui://turnmark/conversion/0.3.0-r3.html";
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
const elevation = z.strictObject({
  value: z.number(),
  unit: z.enum(["feet", "meters"]),
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
    { name: "turnmark", version: "0.3.0" },
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
        "Convert an entered swim to an explicit course. NCAA is the default; colorado-teamunify-2026 selects documented Colorado Timing formulas. The selected method drives the primary result; methodComparison also returns NCAA and Colorado for the same destination. methodDifferenceSeconds is a difference between rules, not a confidence interval. Optional elevation is deducted from the original event first, using altitudePolicy (USA Swimming default); value.altitude retains the original time, deduction and source. altitudeComparison returns both policies. value.caveat identifies the documented Colorado SCM/SCY unequal-distance freestyle limitation; show it alongside that result. Preserve each source; conversions are estimates, not entry approval.",
      inputSchema: z.strictObject({
        swim,
        to: z.enum(["SCY", "SCM", "LCM"]),
        table,
        method: z.string().optional(),
        elevation: elevation.optional(),
        altitudePolicy: z.string().optional(),
      }),
      _meta: {
        ui: {
          resourceUri: conversionResourceUri,
          visibility: ["model", "app"],
        },
      },
      outputSchema: outcome.and(
        z.object({
          methodComparison: z
            .array(
              z.object({
                method: z.string(),
                label: z.string(),
                result: outcome,
              }),
            )
            .optional(),
          methodDifferenceSeconds: z.number().nonnegative().optional(),
          altitudeComparison: z
            .array(
              z.object({
                policy: z.string(),
                label: z.string(),
                result: outcome,
              }),
            )
            .optional(),
        }),
      ),
      annotations,
    },
    (input) => {
      const primary = engine.convert({
        ...input,
        method: input.method as ConversionMethod | undefined,
        altitudePolicy: input.altitudePolicy as
          (typeof altitudePolicies)[number]["id"] | undefined,
      });
      if (primary.status === "invalid") return result(primary);
      const methodComparison = conversionMethods.map((method) => ({
        method: method.id,
        label: method.label,
        result:
          method.id === (input.method ?? conversionMethods[0].id)
            ? primary
            : engine.convert({
                ...input,
                method: method.id,
                altitudePolicy: input.altitudePolicy as
                  (typeof altitudePolicies)[number]["id"] | undefined,
              }),
      }));
      const [ncaa, colorado] = methodComparison.map((item) => item.result);
      return result({
        ...primary,
        methodComparison,
        ...(input.elevation
          ? {
              altitudeComparison: altitudePolicies.map((policy) => ({
                policy: policy.id,
                label: policy.label,
                result: engine.adjustAltitude({
                  swim: input.swim,
                  elevation: input.elevation!,
                  policy: policy.id,
                }),
              })),
            }
          : {}),
        ...(ncaa.status === "available" && colorado.status === "available"
          ? {
              methodDifferenceSeconds:
                Math.abs(ncaa.value.hundredths - colorado.value.hundredths) /
                100,
            }
          : {}),
      });
    },
  );
  server.registerTool(
    "adjust_altitude",
    {
      description:
        "Adjust an entered swim at an explicit elevation using USA Swimming altitude adjustments. USA Swimming is the default; ncaa-altitude-2026-27-d1 selects the NCAA Division I 2026–27 altitude table. Separate from course-conversion method.",
      inputSchema: z.strictObject({
        swim,
        elevation,
        policy: z.string().optional(),
      }),
      outputSchema: outcome,
      annotations,
    },
    (input) =>
      result(
        engine.adjustAltitude({
          ...input,
          policy: input.policy as
            (typeof altitudePolicies)[number]["id"] | undefined,
        }),
      ),
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
        conversionMethods: z.unknown(),
        altitude: z.unknown(),
        altitudePolicies: z.unknown(),
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
        conversionMethods,
        altitude: altitudeProvenance,
        altitudePolicies,
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
