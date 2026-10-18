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
  await page.goto("http://127.0.0.1:4175/");
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
    "https://turnmark.app/",
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
  expect(
    await page.evaluate(async () => {
      const cache = await caches.open(
        (await caches.keys()).find((name) => name.startsWith("turnmark-"))!,
      );
      return (await cache.keys()).some((request) =>
        new URL(request.url).pathname.endsWith(".wasm"),
      );
    }),
  ).toBe(true);
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

test("a failed calculation-engine download shows a recovery message and reload can recover", async ({
  page,
}) => {
  await page.route("**/*.wasm", (route) => route.abort());
  await page.goto("./");
  await expect(page.getByRole("alert")).toHaveText(
    "Turnmark couldn’t load. Check your connection and reload the page.",
  );
  await page.unroute("**/*.wasm");
  await page.reload();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.locator("#swim-time").fill("1:00");
  await expect(page.locator("#swim-time")).toHaveValue("1:00");
});

test("manifest and icons support standalone installation, and native prompt is invoked on click", async ({
  page,
  request,
}) => {
  await page.goto("./");
  const manifest = await (await request.get("manifest.webmanifest")).json();
  expect(manifest.id).toBe("/");
  expect(manifest.start_url).toBe("/");
  expect(manifest.scope).toBe("/");
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

test("Cloudflare serves root assets, refreshable PWA files and legacy-path redirects", async ({
  request,
}) => {
  const response = await request.get("./");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response.headers()["referrer-policy"]).toBe(
    "strict-origin-when-cross-origin",
  );
  for (const path of ["sw.js", "manifest.webmanifest"]) {
    const asset = await request.get(path);
    expect(asset.ok()).toBe(true);
    expect(asset.headers()["cache-control"]).toBe("no-cache");
  }
  const redirect = await request.get("turnmark/", { maxRedirects: 0 });
  expect(redirect.status()).toBe(301);
  expect(new URL(redirect.headers().location, response.url()).pathname).toBe(
    "/",
  );
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
      response = (await cache.match("/"))!;
    const html = (await response.text()).replace(
      "<html",
      '<html data-cached-build="previous"',
    );
    await cache.put(
      "/",
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
