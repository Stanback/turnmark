#!/usr/bin/env node
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { createEngine } from "@turnmark/sdk/node";
import { createServer } from "./server.js";

try {
  const engine = await createEngine();
  const handle = serveStdio(() => createServer(engine), {
    onerror: () => console.error("Turnmark MCP protocol error."),
  });
  const stop = () => {
    void handle.close().then(
      () => process.exit(0),
      () => process.exit(1),
    );
  };
  process.once("SIGINT", stop);
  process.once("SIGTERM", stop);
} catch {
  console.error(
    "Turnmark MCP could not initialize its bundled calculation engine.",
  );
  process.exitCode = 1;
}
