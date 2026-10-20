import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { createServer } from "node:http";

test("widget keeps NCAA default and offers Colorado offline without changing the entered swim", async ({
  page,
  context,
}) => {
  await page.goto("./embed/v1/?theme=dark");
  const scy = page
    .locator("article")
    .filter({ hasText: "100 Freestyle · SCY" });
  const lcm = page
    .locator("article")
    .filter({ hasText: "100 Freestyle · LCM" });
  await expect(scy).toContainText("52.44");
  await expect(page.locator(".method-options")).not.toHaveAttribute("open", "");
  await context.setOffline(true);
  await page.locator(".calculation-options summary").click();
  await page.locator(".method-options summary").click();
  const methods = page.getByRole("region", { name: "Compare methods in SCY" });
  await expect(methods.locator('[data-method="ncaa-2025-27"]')).toContainText(
    "52.44",
  );
  await expect(
    methods.locator('[data-method="colorado-teamunify-2026"]'),
  ).toContainText("52.61");
  await expect(methods).toContainText("Method difference: 0.17s");

  await page
    .getByRole("combobox", { name: "Course conversion", exact: true })
    .selectOption("colorado-teamunify-2026");
  await expect(scy).toContainText("52.61");
  await expect(lcm).toContainText("1:00.00");
  await expect(lcm).toContainText("Entered swim");
  await expect(
    page
      .locator("footer")
      .getByRole("link", { name: "Colorado Timing source" }),
  ).toHaveAttribute("href", /sportsengine/);
  await page
    .getByRole("combobox", { name: "Course conversion", exact: true })
    .selectOption("ncaa-2025-27");
  await expect(scy).toContainText("52.44");
});

test("publisher iframe converts offline without reading the host app's storage", async ({
  page,
  context,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() => {
    for (const name of ["localStorage", "sessionStorage", "indexedDB"])
      Object.defineProperty(window, name, {
        get() {
          throw new Error(`Widget accessed ${name}`);
        },
      });
  });
  await page.goto("./embed/v1/?theme=light");
  await expect(
    page.getByRole("heading", { name: "100 Freestyle · SCY" }),
  ).toBeVisible();
  await expect(
    page.locator("article").filter({ hasText: "100 Freestyle · SCY" }),
  ).toContainText("52.44");
  await context.setOffline(true);
  await page.getByLabel("Entered time").fill("2:16.71");
  await page
    .getByRole("combobox", { name: "Stroke", exact: true })
    .selectOption("breaststroke");
  await page
    .getByRole("combobox", { name: "Distance", exact: true })
    .selectOption("200");
  await page
    .getByRole("combobox", { name: "Published table", exact: true })
    .selectOption("men");
  const scy = page
    .locator("article")
    .filter({ hasText: "200 Breaststroke · SCY" });
  await expect(scy).toContainText("1:57.29");
  await expect(scy).toContainText("Published factor");
  await page
    .locator(".converter")
    .screenshot({ path: testInfo.outputPath("widget-light.png") });
  await page.getByLabel("Entered time").fill("oops");
  await expect(page.getByLabel("Entered time")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await expect(page.getByText("1:57.29", { exact: true })).toHaveCount(0);
  await page.getByLabel("Entered time").fill("2:16.71");
  await expect(scy).toContainText("1:57.29");
  expect(errors).toEqual([]);
});

test("actual cross-origin iframe works at narrow width with source and destination context", async ({
  page,
}, testInfo) => {
  const publisher = createServer((_request, response) => {
    response.setHeader("Content-Type", "text/html");
    response.end(
      '<!doctype html><title>Publisher fixture</title><iframe title="Swimming calculator" src="http://127.0.0.1:4175/embed/v1/?theme=dark" width="320" height="740" style="border:0"></iframe>',
    );
  });
  await new Promise<void>((resolve) =>
    publisher.listen(0, "127.0.0.1", resolve),
  );
  const address = publisher.address();
  if (!address || typeof address === "string")
    throw new Error("No fixture port");
  try {
    await page.goto(`http://localhost:${address.port}/`);
    const frame = page.frameLocator("iframe");
    await expect(
      frame.getByRole("heading", { name: "Swim time converter", exact: true }),
    ).toBeVisible();
    expect(
      await frame
        .getByRole("combobox", { name: "Distance", exact: true })
        .evaluate((select) => select.getBoundingClientRect().width),
    ).toBeGreaterThan(240);
    await frame
      .getByRole("combobox", { name: "Distance", exact: true })
      .selectOption("400");
    await expect(
      frame.getByRole("heading", { name: "500 Freestyle · SCY" }),
    ).toBeVisible();
    await frame
      .getByRole("combobox", { name: "Stroke", exact: true })
      .selectOption("backstroke");
    await frame
      .getByRole("combobox", { name: "Distance", exact: true })
      .selectOption("50");
    await expect(
      frame.locator("article").filter({ hasText: "SCY" }),
    ).toContainText("No published factor");
    await expect(frame.getByRole("link", { name: "Turnmark" })).toHaveAttribute(
      "target",
      "_blank",
    );
    const widget = page.frames().find((f) => f.url().includes("/embed/v1/"))!;
    expect(
      await widget.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page
      .locator("iframe")
      .screenshot({ path: testInfo.outputPath("widget-dark.png") });
  } finally {
    await new Promise<void>((resolve, reject) =>
      publisher.close((error) => (error ? reject(error) : resolve())),
    );
  }
});

test("cross-origin height signals are metadata-only and resizing stays publisher-owned", async ({
  page,
}) => {
  const publisher = createServer((_request, response) => {
    response.setHeader("Content-Type", "text/html");
    response.end(`<!doctype html><title>Optional sizing fixture</title>
      <script>
        window.heights = [];
        window.resizeEnabled = false;
        addEventListener("message", event => {
          const frame = document.querySelector("iframe");
          if (event.origin !== "http://127.0.0.1:4175" ||
              event.source !== frame?.contentWindow) return;
          const data = event.data;
          if (!data || data.type !== "turnmark:resize" || data.version !== 1 ||
              !Number.isSafeInteger(data.height) || data.height < 240 || data.height > 4000) return;
          window.heights.push(data);
          if (window.resizeEnabled) frame.style.height = data.height + "px";
        });
      </script>
      <iframe title="Swimming calculator" referrerpolicy="no-referrer"
        src="http://127.0.0.1:4175/embed/v1/" width="640" height="820" style="border:0"></iframe>`);
  });
  await new Promise<void>((resolve) =>
    publisher.listen(0, "127.0.0.1", resolve),
  );
  const address = publisher.address();
  if (!address || typeof address === "string")
    throw new Error("No fixture port");
  const heights = () =>
    page.evaluate(
      () =>
        (window as any).heights as {
          type: string;
          version: number;
          height: number;
        }[],
    );
  try {
    await page.goto(`http://localhost:${address.port}/`);
    await expect.poll(async () => (await heights()).length).toBeGreaterThan(0);
    const iframe = page.locator("iframe");
    await expect(iframe).toHaveCSS("height", "820px");
    const wideHeight = (await heights()).at(-1)!.height;
    await iframe.evaluate((frame) => {
      frame.style.width = "320px";
    });
    await expect
      .poll(async () => (await heights()).at(-1)!.height)
      .toBeGreaterThan(wideHeight);
    await expect(iframe).toHaveCSS("height", "820px");
    const widget = page
      .frames()
      .find((frame) => frame.url().includes("/embed/v1/"))!;
    expect(await widget.evaluate(() => document.referrer)).toBe("");
    const narrowHeight = (await heights()).at(-1)!.height;
    await page.evaluate(() => {
      (window as any).resizeEnabled = true;
    });
    // Text reflow changes content size without a new navigation or width change.
    await widget.addStyleTag({
      content:
        ".converter, .converter :is(label, p, h1, h2, input, select, a, strong) { font-size: 24px !important; line-height: 1.5 !important; }",
    });
    await expect
      .poll(async () => (await heights()).at(-1)!.height)
      .not.toBe(narrowHeight);
    await expect
      .poll(async () =>
        Number.parseFloat(await iframe.evaluate((frame) => frame.style.height)),
      )
      .toBe((await heights()).at(-1)!.height);
    await page
      .frameLocator("iframe")
      .getByLabel("Entered time")
      .fill("2:16.71");
    for (const message of await heights()) {
      expect(Object.keys(message).sort()).toEqual([
        "height",
        "type",
        "version",
      ]);
      expect(message.type).toBe("turnmark:resize");
      expect(message.version).toBe(1);
      expect(Number.isSafeInteger(message.height)).toBe(true);
    }
    // A publisher-origin message must not impersonate the widget's signal.
    // Acknowledge that exact event after the fixture's earlier listener runs;
    // legitimate content/font reflows can still arrive independently.
    await page.evaluate(
      () =>
        new Promise<void>((resolve) => {
          const acknowledge = (event: MessageEvent) => {
            if (
              event.source === window &&
              event.data?.publisherProbe === true
            ) {
              window.removeEventListener("message", acknowledge);
              resolve();
            }
          };
          window.addEventListener("message", acknowledge);
          window.postMessage(
            {
              type: "turnmark:resize",
              version: 1,
              height: 333,
              publisherProbe: true,
            },
            "*",
          );
        }),
    );
    expect(
      (await heights()).some((message) => "publisherProbe" in message),
    ).toBe(false);
  } finally {
    await new Promise<void>((resolve, reject) =>
      publisher.close((error) => (error ? reject(error) : resolve())),
    );
  }
});

test("copy section provides a versioned embed, theme preview and manual copy fallback", async ({
  page,
  context,
}, testInfo) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("./embed/");
  const section = page.locator("main.embed-section");
  await section.getByLabel("Appearance").selectOption("dark");
  await expect(section.getByLabel("Embed code")).toHaveValue(
    /https:\/\/turnmark.app\/embed\/v1\/\?theme=dark/,
  );
  await section.getByRole("button", { name: "Copy embed code" }).click();
  await expect(section.getByRole("status")).toContainText("Embed code copied.");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "Swim time converter by Turnmark",
  );
  await expect(section.locator("details")).toHaveAttribute("open", "");
  await expect(section.locator("iframe")).toHaveAttribute("src", /theme=dark/);
  await expect(
    section
      .frameLocator("iframe")
      .getByRole("heading", { name: "Swim time converter", exact: true }),
  ).toBeVisible();
  await page.evaluate(() =>
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: () => Promise.reject(new Error("blocked")) },
    }),
  );
  await section.getByLabel("Appearance").selectOption("light");
  await section.getByRole("button", { name: "Copy embed code" }).click();
  await expect(section.getByRole("status")).toContainText("copy it manually");
  await page.emulateMedia({ colorScheme: "dark" });
  await section
    .locator("details")
    .evaluate((node) => ((node as HTMLDetailsElement).open = false));
  await expect(section.locator("select")).toHaveCSS(
    "background-color",
    "rgb(18, 45, 59)",
  );
  expect(
    (await new AxeBuilder({ page }).include(".embed-section").analyze())
      .violations,
  ).toEqual([]);
  await section.screenshot({
    path: testInfo.outputPath("embed-code-dark.png"),
    animations: "disabled",
  });
});

test("widget handles loading failure and passes accessibility checks in both themes", async ({
  page,
}) => {
  await page.route("**/*.wasm", (route) => route.abort());
  await page.goto("./embed/v1/");
  await expect(page.getByRole("alert")).toContainText(
    "converter couldn’t load",
  );
  await page.unroute("**/*.wasm");
  for (const theme of ["light", "dark"]) {
    await page.goto(`./embed/v1/?theme=${theme}`);
    await expect(
      page.getByRole("heading", { name: "Swim time converter", exact: true }),
    ).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
});

test("installed app caches the widget route for offline navigation", async ({
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
  await page.goto("./embed/v1/");
  await expect(
    page.getByRole("heading", { name: "Swim time converter", exact: true }),
  ).toBeVisible();
  await expect(
    page.locator("article").filter({ hasText: "100 Freestyle · SCY" }),
  ).toContainText("52.44");
  await page.goto("./embed/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Embed the swim time converter",
  );
  await page.getByLabel("Appearance", { exact: true }).selectOption("dark");
  await expect(page.getByLabel("Embed code")).toHaveValue(/theme=dark/);
  await expect(
    page
      .frameLocator("iframe")
      .getByRole("heading", { name: "Swim time converter", exact: true }),
  ).toBeVisible();
});

test("widget setup has pre-rendered instructions, its own route and accessible responsive appearances", async ({
  browser,
  page,
  request,
}, testInfo) => {
  await page.goto("./");
  await page.getByRole("link", { name: "Widget setup", exact: true }).click();
  await expect(page).toHaveURL(/\/embed\/$/);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const staticContext = await browser.newContext({ javaScriptEnabled: false });
  try {
    const staticPage = await staticContext.newPage();
    await staticPage.goto("http://127.0.0.1:4175/embed/");
    await expect(staticPage.getByRole("heading", { level: 1 })).toHaveText(
      "Embed the swim time converter",
    );
    await expect(staticPage.getByLabel("Embed code")).toHaveValue(
      /https:\/\/turnmark.app\/embed\/v1\//,
    );
    await expect(
      staticPage.getByText("Add it to a page", { exact: true }),
    ).toBeVisible();
    await expect(staticPage.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      "https://turnmark.app/embed/",
    );
  } finally {
    await staticContext.close();
  }
  expect(await (await request.get("sitemap.xml")).text()).toContain(
    "https://turnmark.app/embed/",
  );
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.setViewportSize({
      width: colorScheme === "dark" ? 320 : 900,
      height: 900,
    });
    await page.goto("./embed/");
    await expect(
      page
        .frameLocator("iframe")
        .getByRole("heading", { name: "Swim time converter", exact: true }),
    ).toBeVisible();
    await expect
      .poll(() =>
        page.locator("iframe").evaluate((frame) => {
          const content = frame.contentDocument?.getElementById("widget");
          if (!content) return false;
          const expected = Math.max(
            240,
            Math.ceil(content.getBoundingClientRect().height) + 2,
          );
          return Math.abs(frame.getBoundingClientRect().height - expected) <= 2;
        }),
      )
      .toBe(true);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`widget-setup-${colorScheme}.png`),
      fullPage: true,
    });
  }
  expect(errors).toEqual([]);
});

test("widget applies altitude before conversion offline and keeps raw input", async ({
  page,
  context,
}) => {
  await page.goto("./embed/v1/?theme=light");
  await page.getByLabel("Entered time").fill("58.32");
  await page
    .getByRole("combobox", { name: "Entered course", exact: true })
    .selectOption("SCY");
  await context.setOffline(true);
  await page.locator(".calculation-options summary").click();
  await page.getByLabel("Adjust for altitude").check();
  await page.getByLabel("Pool elevation", { exact: true }).fill("5000");
  await page
    .getByRole("combobox", { name: "Altitude policy", exact: true })
    .selectOption("ncaa-altitude-2026-27-d1");
  const lcm = page
    .locator("article")
    .filter({ hasText: "100 Freestyle · LCM" });
  await expect(lcm).toContainText("1:06.61");
  await expect(page.getByLabel("Entered time")).toHaveValue("58.32");
  await page.locator(".method-options summary").click();
  await expect(
    page.getByRole("region", { name: "Compare altitude policies" }),
  ).toContainText("58.22");
  await page.getByLabel("Adjust for altitude").uncheck();
  await expect(lcm).toContainText("1:06.72");
});
