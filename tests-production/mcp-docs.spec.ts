import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile } from "node:fs/promises";

test("agent index serves canonical Markdown references through the production host", async ({
  request,
}) => {
  const index = await request.get("llms.txt");
  expect(index.ok()).toBe(true);
  expect(index.headers()["content-type"]).toContain("text/plain");
  expect(index.headers()["cache-control"]).toBe("no-cache");
  const text = await index.text();
  expect(text).toMatch(/^# Turnmark\n/);
  const links = [...text.matchAll(/\]\((https:\/\/turnmark\.app\/[^)]+)\)/g)];
  expect(links.length).toBeGreaterThanOrEqual(4);
  for (const [, link] of links) {
    const response = await request.get(new URL(link).pathname);
    expect(response.ok(), link).toBe(true);
    if (new URL(link).pathname.endsWith(".md")) {
      expect(response.headers()["content-type"], link).toContain(
        "text/markdown",
      );
      expect(await response.text(), link).toMatch(/^# /);
    } else {
      expect(response.headers()["content-type"], link).toContain("text/html");
      expect(await response.text(), link).toContain('<link rel="canonical"');
    }
  }
  expect(await (await request.get("mcp/index.md")).text()).toBe(
    await readFile("packages/mcp/README.md", "utf8"),
  );
  const sitemap = await (await request.get("sitemap.xml")).text();
  expect(sitemap).toContain("https://turnmark.app/mcp/");
  const home = await (await request.get("./")).text();
  expect(home).toContain('href="/mcp/"');
  expect(home).toContain('rel="describedby"');
});

test("MCP quick start is readable without JavaScript in light and narrow dark appearances", async ({
  browser,
}, testInfo) => {
  for (const colorScheme of ["light", "dark"] as const) {
    const context = await browser.newContext({
      javaScriptEnabled: false,
      colorScheme,
      viewport: { width: colorScheme === "dark" ? 320 : 900, height: 900 },
    });
    try {
      const page = await context.newPage();
      await page.goto("http://127.0.0.1:4175/mcp/");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(
        "Use Turnmark with an AI assistant",
      );
      await expect(page.locator('link[rel="alternate"]')).toHaveAttribute(
        "href",
        "/mcp/index.md",
      );
      const config = JSON.parse(await page.locator("pre code").innerText());
      expect(config.mcpServers.turnmark).toEqual({
        type: "http",
        url: "https://mcp.turnmark.app/mcp",
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    } finally {
      await context.close();
    }
    // Axe's asynchronous audit needs JavaScript timers. Keep the no-script
    // rendering check above separate from the audit of the same static page.
    const audit = await browser.newContext({
      colorScheme,
      viewport: { width: colorScheme === "dark" ? 320 : 900, height: 900 },
    });
    try {
      const page = await audit.newPage();
      await page.goto("http://127.0.0.1:4175/mcp/");
      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
      await page.screenshot({
        path: testInfo.outputPath(`mcp-docs-${colorScheme}.png`),
        fullPage: true,
      });
    } finally {
      await audit.close();
    }
  }
});

test("installed app retains the documentation route and agent index offline", async ({
  page,
  context,
}) => {
  await page.goto("./");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller)
      await new Promise<void>((resolve) =>
        navigator.serviceWorker.addEventListener(
          "controllerchange",
          () => resolve(),
          { once: true },
        ),
      );
  });
  await context.setOffline(true);
  await page.goto("./mcp/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Use Turnmark with an AI assistant",
  );
  for (const path of ["/llms.txt", "/mcp/index.md"])
    expect(
      await page.evaluate(async (url) => (await fetch(url)).text(), path),
    ).toContain("# Turnmark");
});
