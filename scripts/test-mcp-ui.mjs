import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { unstable_dev } from "wrangler";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
process.chdir(fileURLToPath(new URL("../", import.meta.url)));
const mode = process.argv[2] === "http" ? "HTTP" : "stdio";
let worker;
const client = new Client(
  { name: "Turnmark UI test", version: "1" },
  {
    capabilities: {
      extensions: {
        "io.modelcontextprotocol/ui": {
          mimeTypes: ["text/html;profile=mcp-app"],
        },
      },
    },
  },
);
if (mode === "HTTP") {
  worker = await unstable_dev("packages/mcp-worker/src/index.ts", {
    config: "packages/mcp-worker/wrangler.jsonc",
    local: true,
    port: 0,
    ip: "127.0.0.1",
    persist: false,
    logLevel: "error",
    experimental: {
      disableExperimentalWarning: true,
      disableDevRegistry: true,
      watch: false,
    },
  });
  await client.connect(
    new StreamableHTTPClientTransport(
      new URL(`http://${worker.address}:${worker.port}/mcp`),
    ),
  );
} else {
  await client.connect(
    new StdioClientTransport({
      command: process.execPath,
      args: ["packages/mcp/dist/cli.js"],
      stderr: "pipe",
    }),
  );
}
const uri = "ui://turnmark/conversion/0.3.0-r8.html";
const card = (await client.readResource({ uri })).contents[0].text;
const host = await build({
  absWorkingDir: process.cwd(),
  entryPoints: ["packages/mcp/test/host.ts"],
  bundle: true,
  write: false,
  format: "iife",
  target: "es2022",
});
const server = createServer((req, res) => {
  if (req.url === "/host.js") {
    res.setHeader("Content-Type", "text/javascript");
    res.end(host.outputFiles[0].text);
  } else if (req.url === "/card") {
    res.setHeader("Content-Type", "text/html");
    res.end(card);
  } else {
    res.setHeader("Content-Type", "text/html");
    res.end(
      '<!doctype html><html lang="en"><head><title>MCP Apps bridge test</title></head><body style="margin:0"><script src="/host.js"></script></body></html>',
    );
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const input = {
  swim: {
    time: "58.32",
    event: { distance: 100, stroke: "freestyle", course: "SCY" },
  },
  to: "LCM",
  table: "women",
};
const initial = await client.callTool({
  name: "convert_swim",
  arguments: input,
});
const shots = `target/mcp-ui-review${mode === "HTTP" ? "/http" : ""}`;
await mkdir(shots, { recursive: true });
try {
  const context = await browser.newContext({
    viewport: { width: 680, height: 1000 },
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const external = [];
  page.on("request", (r) => {
    if (!r.url().startsWith(base) && !r.url().startsWith("data:"))
      external.push(r.url());
  });
  await page.exposeFunction("callConversion", (params) =>
    client.callTool(params),
  );
  await page.goto(base);
  await page.waitForFunction(() => typeof window.mount === "function");
  await page.evaluate(({ input, initial }) => window.mount(input, initial), {
    input,
    initial,
  });
  const frame = page.frameLocator("iframe").first();
  await frame.locator(".clock").getByText("1:06.72", { exact: true }).waitFor();
  await frame.locator("#result summary").click();
  await frame
    .locator("body")
    .screenshot({ path: `${shots}/mcp-methods-light.png` });
  assert.match(
    await frame.locator('[data-method="ncaa-2025-27"]').textContent(),
    /1:06.72/,
  );
  assert.match(
    await frame
      .locator('[data-method="colorado-teamunify-2026"]')
      .textContent(),
    /1:06.33/,
  );
  // Equivalent time from data/empirical.json 100-FR|women: 58.32 SCY through the
  // SCY and LCM course maps (knots on the shared latent scale) is 1:07.26, truncated once.
  const equivalence = await frame
    .locator('[data-method="turnmark-empirical-2026"]')
    .textContent();
  assert.match(equivalence, /Turnmark Equivalence/);
  assert.match(equivalence, /1:07.26/);
  assert.match(
    await frame.locator("#result").textContent(),
    /Estimates the equivalent time/,
  );
  assert.match(
    await frame.locator(".method-difference").textContent(),
    /0.39s/,
  );
  await frame.locator("#result summary").click();
  assert.equal(
    await frame.locator("#original").textContent(),
    "100 yd Freestyle · SCY · Women",
  );
  await frame.locator("#update").waitFor({ state: "visible" });
  await page.waitForFunction(
    () => !document.querySelector("iframe").contentDocument,
  ); // opaque origin
  const accessibility = await new AxeBuilder({ page })
    .include("iframe")
    .analyze();
  const violations = accessibility.violations;
  assert.deepEqual(
    accessibility.incomplete.filter((v) => v.id === "frame-tested"),
    [],
  );
  assert.deepEqual(
    violations.map((v) => ({ id: v.id, impact: v.impact })),
    [],
  );
  await frame
    .locator("body")
    .screenshot({ path: `${shots}/mcp-card-light.png` });
  // Keyboard-only update; the Rust tool owns all math and destination mapping.
  await frame.locator("#time").fill("1:00.25");
  await frame.locator("#course").selectOption("SCM");
  await frame.locator("#update").focus();
  await page.keyboard.press("Enter");
  await frame.locator(".clock").getByText("1:07.24", { exact: true }).waitFor();
  await page.waitForFunction(() => window.contexts.length === 1);
  assert.equal(
    (await page.evaluate(() => window.calls[0].arguments)).swim.event.course,
    "SCY",
  );
  assert.match(
    await page.evaluate(() => window.contexts[0].content[0].text),
    /1:07.24/,
  );
  await page.evaluate(() =>
    window.cards[0].setHostContext({ theme: "dark", displayMode: "inline" }),
  );
  await frame.locator('html[data-theme="dark"]').waitFor();
  await page.setViewportSize({ width: 320, height: 1100 });
  assert.equal(
    await frame
      .locator("body")
      .evaluate((el) => el.scrollWidth <= window.innerWidth),
    true,
  );
  await frame
    .locator("body")
    .screenshot({ path: `${shots}/mcp-card-dark-narrow.png` });
  // Cancellation discards a late result and retains the committed comparison.
  await page.evaluate(() => (window.delay = 300));
  await frame.locator("#time").fill("50");
  await frame.locator("#update").click();
  await frame.locator("#cancel").click();
  await page.waitForTimeout(400);
  assert.equal(await frame.locator(".clock").textContent(), "1:07.24");
  assert.equal(await page.evaluate(() => window.contexts.length), 1);
  await page.evaluate(() => {
    window.delay = 0;
    window.deny = true;
  });
  await frame.locator("#update").click();
  await frame
    .locator("#status")
    .getByText(/Couldn’t update/)
    .waitFor();
  assert.equal(await frame.locator(".clock").textContent(), "1:07.24");
  await page.evaluate(() => {
    window.deny = false;
    window.denyContext = true;
  });
  await frame.locator("#time").fill("1:60");
  await frame.locator("#update").click();
  await frame.getByRole("heading", { name: "Check your swim" }).waitFor();
  await frame
    .locator("#status")
    .getByText(/couldn’t share/)
    .waitFor();
  await frame.locator("#time").fill("58.32");
  await frame.locator("#update").click();
  await frame.locator(".clock").getByText("1:05.08", { exact: true }).waitFor();
  await page.evaluate(() => (window.malformed = true));
  await frame.locator("#update").click();
  await frame
    .locator("#status")
    .getByText(/Couldn’t update/)
    .waitFor();
  assert.equal(await frame.locator(".clock").textContent(), "1:05.08");
  await page.evaluate(() => (window.malformed = false));
  // A second independent card uses the returned destination event for 500→400.
  const distance = {
    ...input,
    swim: {
      time: "5:00",
      event: { distance: 500, stroke: "freestyle", course: "SCY" },
    },
  };
  const second = await client.callTool({
    name: "convert_swim",
    arguments: distance,
  });
  await page.evaluate(
    ({ distance, second }) => window.mount(distance, second, "dark"),
    { distance, second },
  );
  const other = page.frameLocator("iframe").nth(1);
  await other
    .getByRole("heading", { name: "400 m Freestyle · LCM · Women" })
    .waitFor();
  assert.equal(await frame.locator("#time").inputValue(), "58.32");
  // Unavailable results and hostile strings stay literal text, not markup.
  await page.evaluate(() =>
    window.cards[1].sendToolResult({
      structuredContent: {
        status: "unavailable",
        reason: "<img src=x onerror=alert(1)>",
        provenance: {
          id: "test",
          title: "<img src=x onerror=alert(1)>",
          revision: "test",
          url: "javascript:alert(1)",
        },
      },
      content: [],
    }),
  );
  await other
    .getByRole("heading", { name: "No conversion for this selection" })
    .waitFor();
  await other.locator("#result summary").click();
  await other.getByText(/<img src=x onerror=alert/).waitFor();
  assert.equal(await other.locator("img").count(), 0);
  assert.equal(
    await other
      .getByRole("button", { name: "Open published source ↗" })
      .count(),
    0,
  );
  // 200% text at narrow width, including expanded provenance.
  await frame.locator("html").evaluate((el) => (el.style.fontSize = "200%"));
  await frame.locator("#result summary").click();
  await frame.getByRole("button", { name: "Open published source ↗" }).click();
  await frame
    .locator("#status")
    .getByText(/can’t open the source/)
    .waitFor();
  assert.equal(
    await frame
      .locator("body")
      .evaluate((el) => el.scrollWidth <= window.innerWidth),
    true,
  );
  assert.equal(
    await frame.locator(".clock").evaluate((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      const rects = [...range.getClientRects()];
      // The main clock and highlighted hundredths are separate inline runs.
      // They must share one line and fit the available width.
      return (
        rects.length > 0 &&
        rects.every((rect) => Math.abs(rect.top - rects[0].top) < 1) &&
        el.scrollWidth <= el.clientWidth
      );
    }),
    true,
    "The result clock must remain on one line at large text",
  );
  assert.deepEqual(external, []);
  assert.deepEqual(errors, []);
  await frame
    .locator("body")
    .screenshot({ path: `${shots}/mcp-card-large-text.png` });
  // An alternative method stays in a collapsed control and is sent explicitly
  // through the official bridge; the SDK owns both multiplier and offset.
  await page.evaluate(() => (window.denyContext = false));
  await frame.locator("html").evaluate((el) => (el.style.fontSize = "100%"));
  await frame.locator(".calculation-options summary").click();
  await frame.locator("#method").selectOption("colorado-teamunify-2026");
  await frame.locator("#course").selectOption("LCM");
  await frame.locator("#update").click();
  await frame.locator(".clock").getByText("1:06.33", { exact: true }).waitFor();
  assert.equal(
    await page.evaluate(() => window.calls.at(-1).arguments.method),
    "colorado-teamunify-2026",
  );
  // Altitude stays explicit, uses the same Rust pipeline and retains raw input.
  await frame.locator("#altitude-enabled").check();
  await frame.locator("#elevation").fill("5000");
  await frame
    .locator("#altitude-policy")
    .selectOption("ncaa-altitude-2026-27-d1");
  await frame.locator("#update").click();
  await frame.locator(".clock").getByText("1:06.22", { exact: true }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.calls.at(-1).arguments)).swim.time,
    "58.32",
  );
  await frame.locator("#result summary").click();
  assert.match(await frame.locator("#result").textContent(), /58.22/);
  await frame
    .locator("body")
    .screenshot({ path: `${shots}/mcp-altitude-light.png` });
  // Close methods keep separate spectrum labels: women's 1650 SCY 17:36.20 -> SCM
  // put NCAA and Equivalence closer together than one label is wide.
  const mile = {
    ...input,
    swim: {
      time: "17:36.20",
      event: { distance: 1650, stroke: "freestyle", course: "SCY" },
    },
    to: "SCM",
  };
  const mileResult = await client.callTool({
    name: "convert_swim",
    arguments: mile,
  });
  await page.evaluate(
    ({ mile, mileResult }) => window.mount(mile, mileResult),
    { mile, mileResult },
  );
  const spectrumCard = page.frameLocator("iframe").nth(2);
  await spectrumCard.locator("#result summary").click();
  for (const width of [680, 390]) {
    await page.setViewportSize({ width, height: 1100 });
    await page.waitForTimeout(100);
    const layout = await spectrumCard
      .locator(".spectrum-track")
      .evaluate((track) => {
        const box = track.getBoundingClientRect();
        return [...track.querySelectorAll(".spectrum-pin")].map((pin) => ({
          pin: pin.getBoundingClientRect().left,
          dot: pin.querySelector(".pin-dot").getBoundingClientRect(),
          label: pin.querySelector(".pin-name").getBoundingClientRect(),
          track: { left: box.left, right: box.right, bottom: box.bottom },
        }));
      });
    assert.equal(layout.length, 3);
    for (const [i, a] of layout.entries()) {
      assert.ok(Math.abs(a.dot.left + a.dot.width / 2 - a.pin) < 1);
      assert.ok(a.label.left >= a.track.left - 0.5);
      assert.ok(a.label.right <= a.track.right + 0.5);
      assert.ok(a.label.bottom <= a.track.bottom + 0.5);
      for (const b of layout.slice(i + 1))
        assert.ok(
          a.label.right <= b.label.left ||
            b.label.right <= a.label.left ||
            a.label.bottom <= b.label.top ||
            b.label.bottom <= a.label.top,
          `Spectrum labels overlap at ${width}px`,
        );
    }
    await spectrumCard
      .locator(".method-spectrum")
      .screenshot({ path: `${shots}/mcp-spectrum-${width}.png` });
  }
  console.log(
    `MCP Apps: official AppBridge + real ${mode} tools; opaque sandbox/CSP, keyboard, theme, narrow/large text, cancellation, denied calls/context, invalid/unavailable, destination context and card isolation passed.`,
  );
} catch (error) {
  for (const p of browser.contexts().flatMap((c) => c.pages())) {
    console.log(await p.locator("body").innerText());
    for (const f of p.frames().slice(1))
      console.log(await f.locator("body").innerText());
    await p.screenshot({ path: `${shots}/failure.png` });
  }
  throw error;
} finally {
  await browser.close();
  await client.close();
  await worker?.stop();
  await new Promise((resolve) => server.close(resolve));
}
