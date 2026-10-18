import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { createServer } from "node:http";

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

test("copy section provides a versioned embed, theme preview and manual copy fallback", async ({
  page,
  context,
}, testInfo) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("./");
  const section = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Add the converter to your site",
    }),
  });
  await section.getByLabel("Appearance").selectOption("dark");
  await expect(section.getByLabel("Embed code")).toHaveValue(
    /https:\/\/turnmark.app\/embed\/v1\/\?theme=dark/,
  );
  await section.getByRole("button", { name: "Copy embed code" }).click();
  await expect(section.getByRole("status")).toContainText("Embed code copied.");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "Swim time converter by Turnmark",
  );
  await section.getByText("Preview the converter", { exact: true }).click();
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
  await page
    .getByRole("group", { name: "Appearance", exact: true })
    .getByRole("button", { name: "Dark", exact: true })
    .click();
  await section
    .locator("details")
    .evaluate((node) => ((node as HTMLDetailsElement).open = false));
  await expect(section.locator("select")).toHaveCSS(
    "background-color",
    "rgb(23, 47, 67)",
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
});
