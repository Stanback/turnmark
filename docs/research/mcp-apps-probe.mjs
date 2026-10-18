// Research probe only; see ../MCP_APPS.md for isolated installation and scope.
import assert from "node:assert/strict";
import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { McpServer } from "@modelcontextprotocol/server";
import {
  registerAppTool,
  registerAppResource,
  RESOURCE_MIME_TYPE,
  getUiCapability,
} from "@modelcontextprotocol/ext-apps/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";
const uri = "ui://turnmark/research/probe.html";
const html =
  '<!doctype html><html lang="en"><title>Probe</title><p>Local compatibility probe</p></html>';
const observations = [];
const handler = createMcpHandler(
  ({ era }) => {
    const server = new McpServer({
      name: "turnmark-apps-research",
      version: "0.0.0",
    });
    const registeredWithCapability = !!getUiCapability(
      server.server.getClientCapabilities(),
    );
    registerAppTool(
      server,
      "probe",
      {
        inputSchema: z.strictObject({}),
        _meta: { ui: { resourceUri: uri } },
        annotations: { readOnlyHint: true },
      },
      () => {
        const hasUiCapability = !!getUiCapability(
          server.server.getClientCapabilities(),
        );
        observations.push({
          era,
          registeredWithCapability,
          callbackHasUiCapability: hasUiCapability,
        });
        return {
          content: [{ type: "text", text: "Capability probe complete." }],
          structuredContent: { hasUiCapability },
        };
      },
    );
    registerAppResource(
      server,
      "probe",
      uri,
      { mimeType: RESOURCE_MIME_TYPE },
      () => ({
        contents: [
          {
            uri,
            mimeType: RESOURCE_MIME_TYPE,
            text: html,
            _meta: {
              ui: {
                csp: {
                  connectDomains: [],
                  resourceDomains: [],
                  frameDomains: [],
                },
              },
            },
          },
        ],
      }),
    );
    return server;
  },
  {
    route: "/mcp",
    responseMode: "json",
    legacy: "stateless",
    corsOptions: false,
    allowedHostnames: ["localhost"],
  },
);
for (const mode of ["legacy", { pin: "2026-07-28" }]) {
  for (const ui of [false, true]) {
    const client = new Client(
      { name: "probe", version: "0.0.0" },
      {
        versionNegotiation: { mode },
        capabilities: ui
          ? {
              extensions: {
                "io.modelcontextprotocol/ui": {
                  mimeTypes: [RESOURCE_MIME_TYPE],
                },
              },
            }
          : {},
      },
    );
    await client.connect(
      new StreamableHTTPClientTransport(new URL("http://localhost/mcp"), {
        fetch: (input, init) => {
          const req = new Request(input, init);
          req.headers.set("Host", "localhost");
          return handler.fetch(req);
        },
      }),
    );
    const tools = (await client.listTools()).tools;
    assert.equal(tools[0]._meta.ui.resourceUri, uri);
    const result = await client.callTool({ name: "probe", arguments: {} });
    assert.equal(result.content[0].text, "Capability probe complete.");
    assert.equal(observations.at(-1).registeredWithCapability, false);
    assert.equal(
      result.structuredContent.hasUiCapability,
      typeof mode === "object" && ui,
    );
    const resource = await client.readResource({ uri });
    assert.equal(resource.contents[0].text, html);
    assert.equal(resource.contents[0].mimeType, RESOURCE_MIME_TYPE);
    assert.deepEqual(resource.contents[0]._meta.ui.csp.connectDomains, []);
    await client.close();
    console.log(
      JSON.stringify({
        mode,
        ui,
        ...observations.at(-1),
        resourceRead: true,
        textFallback: true,
      }),
    );
  }
}
