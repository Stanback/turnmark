import { test, expect } from "@playwright/test";

test("desktop history fits the standards panel and keeps long lists reachable", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.addInitScript(() => {
    localStorage.setItem(
      "turnmark-history",
      JSON.stringify(
        Array.from({ length: 50 }, (_, i) => ({
          id: `sample-${i}`,
          hash: `t=${58 + i / 100}&s=FR&d=100&c=SCY&g=women&a=17-18&h=0`,
          target: "LCM",
          createdAt: Date.now() - i * 60000,
        })),
      ),
    );
  });
  await page.goto("./");
  await expect(page.locator(".history-row")).toHaveCount(50);
  const history = page.locator(".history-panel");
  const standards = page.locator(".standards-section");
  const list = page.getByRole("region", { name: "Recent conversion entries" });
  const aligned = async () => {
    const left = (await history.boundingBox())!;
    const right = (await standards.boundingBox())!;
    expect(Math.abs(left.y - right.y)).toBeLessThan(1);
    expect(Math.abs(left.height - right.height)).toBeLessThanOrEqual(1);
    expect(
      await list.evaluate((node) => node.scrollHeight > node.clientHeight),
    ).toBe(true);
  };
  await aligned();
  await page.locator(".history-remove").last().focus();
  expect(await list.evaluate((node) => node.scrollTop)).toBeGreaterThan(0);
  await expect(page.locator(".history-remove").last()).toBeInViewport();
  await list.evaluate((node) => {
    node.scrollTop = 0;
  });
  await history.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("desktop-grid-dark.png") });
  await page
    .getByRole("button", { name: "World Aquatics points", exact: true })
    .click();
  await aligned();
  await page
    .getByRole("group", { name: "Performance comparison" })
    .getByRole("button", { name: "Time standards", exact: true })
    .click();
  await page.locator("#standards-system").selectOption("masters");
  await aligned();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(list).toHaveCSS("overflow-y", "visible");
  expect(
    await list.evaluate((node) => node.scrollHeight <= node.clientHeight + 1),
  ).toBe(true);
});

test("setup pages share branded content bounds in both appearances", async ({
  page,
}, testInfo) => {
  for (const colorScheme of ["light", "dark"] as const) {
    for (const width of [1440, 390]) {
      await page.emulateMedia({ colorScheme });
      await page.setViewportSize({ width, height: 1000 });
      let bounds: { x: number; width: number } | undefined;
      for (const route of ["embed/", "mcp/"]) {
        await page.goto(route);
        await page.evaluate(() => document.fonts.ready);
        await expect(
          page.getByRole("link", { name: "Turnmark home", exact: true }),
        ).toBeVisible();
        const box = (await page.locator("main").boundingBox())!;
        if (bounds) {
          expect(box.x).toBe(bounds.x);
          expect(box.width).toBe(bounds.width);
        }
        bounds = box;
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        await page.screenshot({
          path: testInfo.outputPath(
            `${route.slice(0, -1)}-${width}-${colorScheme}.png`,
          ),
          fullPage: true,
        });
      }
    }
  }
  await page.goto("./");
  await page.setViewportSize({ width: 1440, height: 1000 });
  const method = (await page.locator(".method-items").boundingBox())!;
  const faq = (await page.locator(".faq-list").boundingBox())!;
  expect(method.x).toBe(faq.x);
  expect(method.width).toBe(faq.width);
  const title = (await page.locator(".method-intro h2").boundingBox())!;
  expect(title.y).toBe(method.y);
  await page.locator("#method").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: testInfo.outputPath("method-alignment-dark.png"),
  });
});
