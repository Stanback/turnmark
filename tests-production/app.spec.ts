import { test, expect } from "@playwright/test";

test("built HTML contains useful content, metadata and valid structured data without JavaScript", async ({
  browser,
  request,
}) => {
  const response = await request.get("./");
  const html = await response.text();
  expect(html).toContain(
    "How do I convert swim times between yards and meters?",
  );
  expect(html).toContain("Swim time converter for yards and meters");
  expect(html.match(/<h1[\s>]/g)).toHaveLength(1);
  expect(html.match(/<title>/g)).toHaveLength(1);
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:4175/turnmark/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page
    .getByText("What do SCY, SCM, and LCM mean?", { exact: true })
    .click();
  await expect(
    page.locator(".faq-answer").filter({ hasText: "25-yard pool" }),
  ).toBeVisible();
  const structured = JSON.parse(
    (await page.locator('script[type="application/ld+json"]').textContent()) ??
      "{}",
  );
  expect(structured["@type"]).toBe("WebApplication");
  expect(await page.locator('link[rel="canonical"]').getAttribute("href")).toBe(
    "https://stanback.github.io/turnmark/",
  );
  await context.close();
});

test("production hydrates, registers scoped offline support and converts with no connection", async ({
  page,
  context,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.text().includes("hydration")) errors.push(message.text());
  });
  await page.goto(
    "./#t=21%3A00.20&s=FR&d=1500&c=SCY&g=women&a=17-18&h=7200&b=masters&ma=40-44",
  );
  await expect(page.getByTestId("altitude-corrected")).toHaveText("20:27.70");
  await expect(page.locator("#masters-age")).toHaveValue("40-44");
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
  await page.reload();
  await expect(page.getByTestId("altitude-corrected")).toHaveText("20:27.70");
  await page.locator("#swim-time").fill("20:00.20");
  await expect(page.getByTestId("altitude-corrected")).toHaveText("19:27.70");
  await page.getByRole("button", { name: "Save swim", exact: true }).click();
  await expect(page.locator(".saved-card")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".saved-card")).toHaveCount(1);
  expect(errors).toEqual([]);
});

test("manifest and icons support standalone installation, and native prompt is invoked on click", async ({
  page,
  request,
}) => {
  await page.goto("./");
  const manifest = await (await request.get("manifest.webmanifest")).json();
  expect(manifest.start_url).toBe("/turnmark/");
  expect(manifest.scope).toBe("/turnmark/");
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons.map((icon: { sizes: string }) => icon.sizes)).toEqual(
    expect.arrayContaining(["192x192", "512x512"]),
  );
  for (const icon of manifest.icons)
    expect((await request.get(icon.src)).ok()).toBe(true);
  await page.evaluate(() => {
    const event = new Event("beforeinstallprompt", { cancelable: true });
    Object.assign(event, {
      prompt: async () => {
        document.body.dataset.prompted = "true";
      },
      userChoice: Promise.resolve({ outcome: "dismissed" }),
    });
    window.dispatchEvent(event);
  });
  await page.getByRole("button", { name: "Install app", exact: true }).click();
  await expect(page.locator("body")).toHaveAttribute("data-prompted", "true");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("online navigation preserves a consistent offline build until a new worker activates", async ({
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
    const name = (await caches.keys()).find((name) =>
      name.startsWith("turnmark-"),
    )!;
    const cache = await caches.open(name),
      response = (await cache.match("/turnmark/"))!;
    const html = (await response.text()).replace(
      "<html",
      '<html data-cached-build="previous"',
    );
    await cache.put(
      "/turnmark/",
      new Response(html, { headers: { "Content-Type": "text/html" } }),
    );
  });
  await page.reload();
  await expect(page.locator("html")).not.toHaveAttribute(
    "data-cached-build",
    "previous",
  );
  await context.setOffline(true);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute(
    "data-cached-build",
    "previous",
  );
  await page.locator("#swim-time").fill("59.10");
  await expect(page.getByTestId("result-SCY")).toHaveText("59.10");
});
