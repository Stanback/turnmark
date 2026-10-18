import { createMcpHandler } from "agents/mcp/server";
import { createServer } from "@turnmark/mcp";
import { createEngine, type Engine } from "@turnmark/sdk";
import wasm from "@turnmark/sdk/engine.wasm";

// Cached immutable engine, not request/user state. Initialization uses a bundled,
// precompiled module instead of runtime Wasm compilation or a network fetch.
let ready: Promise<Engine> | undefined;
function engine() {
  return (ready ??= createEngine({ wasm }).catch((error: unknown) => {
    ready = undefined;
    throw error;
  }));
}
const handler = createMcpHandler(async () => createServer(await engine()), {
  route: "/mcp",
  responseMode: "json",
  legacy: "stateless",
  maxRequestBodySize: 16 * 1024,
  maxSubscriptions: 0,
  allowedHostnames: ["mcp.turnmark.app", "localhost", "127.0.0.1"],
  allowedOriginHostnames: [
    "turnmark.app",
    "mcp.turnmark.app",
    "localhost",
    "127.0.0.1",
  ],
  corsOptions: false,
  onerror: () => console.error(JSON.stringify({ event: "mcp_protocol_error" })),
});
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!["mcp.turnmark.app", "localhost", "127.0.0.1"].includes(url.hostname))
      return new Response("Forbidden", { status: 403 });
    const ip = request.headers.get("CF-Connecting-IP") ?? "local";
    if (!(await env.REQUEST_LIMITER.limit({ key: ip })).success)
      return new Response("Too many requests", {
        status: 429,
        headers: { "Retry-After": "60" },
      });
    if (!(await env.REQUEST_BUDGET.limit({ key: "all" })).success)
      return new Response("Service busy; retry later", {
        status: 429,
        headers: { "Retry-After": "60" },
      });
    if (url.pathname === "/" && request.method === "GET") {
      try {
        return Response.json({
          service: "Turnmark MCP",
          version: (await engine()).version,
          endpoint: "/mcp",
          personalHistory: false,
        });
      } catch {
        return new Response("Calculation engine unavailable", { status: 503 });
      }
    }
    if (url.pathname !== "/mcp")
      return new Response("Not found", { status: 404 });
    if (request.method !== "POST")
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "POST" },
      });
    if (
      request.headers
        .get("Content-Type")
        ?.split(";")[0]
        .trim()
        .toLowerCase() !== "application/json"
    )
      return new Response("JSON content type required", { status: 415 });
    try {
      // Bound the read before the compatibility classifier parses JSON. The
      // upstream maxRequestBodySize alone does not cover that legacy lane.
      const reader = request.body?.getReader();
      const decoder = new TextDecoder();
      let bytes = 0;
      let body = "";
      if (reader) {
        try {
          while (true) {
            const chunk = await reader.read();
            if (chunk.done) break;
            bytes += chunk.value.byteLength;
            if (bytes > 16 * 1024) {
              await reader.cancel();
              return new Response("Request too large", { status: 413 });
            }
            body += decoder.decode(chunk.value, { stream: true });
          }
          body += decoder.decode();
        } finally {
          reader.releaseLock();
        }
      }
      let parsedBody: unknown;
      try {
        parsedBody = JSON.parse(body);
      } catch {
        return Response.json(
          {
            jsonrpc: "2.0",
            id: null,
            error: { code: -32700, message: "Parse error" },
          },
          { status: 400 },
        );
      }
      const response = await handler.fetch(request, { parsedBody });
      response.headers.set("Cache-Control", "no-store");
      response.headers.set("X-Content-Type-Options", "nosniff");
      return response;
    } catch {
      console.error(JSON.stringify({ event: "mcp_request_failed" }));
      return new Response("MCP service unavailable", { status: 503 });
    }
  },
} satisfies ExportedHandler<Env>;
