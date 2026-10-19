import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("mobile age selectors leave space for their complete selected label", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  for (const [system, id, age] of [
    ["youth", "age-group", "10u"],
    ["masters", "masters-age", "40-44"],
  ]) {
    await page.locator("#standards-system").selectOption(system);
    const select = page.locator(`#${id}`);
    await select.selectOption(age);
    const fits = await select.evaluate((element) => {
      const control = element as HTMLSelectElement;
      const style = getComputedStyle(control);
      const context = document.createElement("canvas").getContext("2d")!;
      context.font = style.font;
      return (
        context.measureText(control.selectedOptions[0].text).width <=
        control.clientWidth -
          parseFloat(style.paddingLeft) -
          parseFloat(style.paddingRight)
      );
    });
    expect(fits).toBe(true);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});

test("remembers swimmer preferences without reusing race inputs, and shared swims override them", async ({
  page,
}) => {
  await page.goto("./");
  await page.locator("#category").selectOption("men");
  await page.locator("#age-group").selectOption("17-18");
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "LCM" })
    .click();
  await page.locator("#standards-system").selectOption("masters");
  await page.locator("#masters-age").selectOption("40-44");
  await page.locator(".altitude-options summary").click();
  const units = page.getByRole("group", { name: "Elevation units" });
  await units.getByRole("button", { name: "m", exact: true }).click();
  await expect(page.locator("#altitude")).toBeVisible();
  await units.getByRole("button", { name: "ft", exact: true }).click();
  await expect(page.locator("#altitude")).toBeVisible();
  await units.getByRole("button", { name: "m", exact: true }).click();
  await page.locator("#altitude").fill("1600");
  await page.locator("#swim-time").fill("2:00");
  await page.locator("#event").selectOption("BR:200");
  await page
    .getByRole("button", { name: "World Aquatics points", exact: true })
    .click();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          JSON.parse(localStorage.getItem("turnmark-preferences")!)
            .standardMode,
      ),
    )
    .toBe("points");
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "World Aquatics points",
      exact: true,
      level: 2,
    }),
  ).toBeVisible();
  await expect(page.locator("#swim-time")).toHaveValue("58.32");
  await expect(page.locator("#event")).toHaveValue("FR:100");
  await expect(page.locator("#category")).toHaveValue("men");
  await expect(
    page
      .getByRole("group", { name: "Swum in" })
      .getByRole("button", { name: "LCM" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".altitude-options")).toHaveAttribute("open", "");
  await expect(
    units.getByRole("button", { name: "m", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#altitude")).toHaveValue("1599.9");
  await page
    .getByRole("group", { name: "Performance comparison" })
    .getByRole("button", { name: "Time standards", exact: true })
    .click();
  await expect(page.locator("#standards-system")).toHaveValue("masters");
  await expect(page.locator("#masters-age")).toHaveValue("40-44");
  await page.locator("#standards-system").selectOption("youth");
  await expect(page.locator("#age-group")).toHaveValue("17-18");
  await page.goto("./#t=1%3A05&s=FR&d=100&c=SCM&g=women&a=13-14&h=0");
  await expect(page.locator("#category")).toHaveValue("women");
  await expect(page.locator("#age-group")).toHaveValue("13-14");
  await expect(
    page
      .getByRole("group", { name: "Swum in" })
      .getByRole("button", { name: "SCM" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#altitude")).toHaveValue("0");
  await expect(page.locator(".altitude-conversion")).toHaveCount(0);
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page.reload();
  await expect(page.locator("#category")).toHaveValue("women");
  await expect(page.locator("#age-group")).toHaveValue("15-16");
  await expect(
    page
      .getByRole("group", { name: "Swum in" })
      .getByRole("button", { name: "SCY" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".altitude-options")).not.toHaveAttribute("open");
});

test("dark standards keep long badges inside their circles and the swim marker visible", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("./#t=58&s=FR&d=100&c=SCM&g=women&a=15-16&h=0");
  await page.evaluate(() => document.fonts.ready);
  for (const [time, label] of [
    ["58", "AAA"],
    ["52.32", "AAAA"],
  ]) {
    await page.locator("#swim-time").fill(time);
    const badge = page.locator(".achievement-badge");
    await expect(badge).toHaveText(label);
    const fit = await badge.evaluate((element) => {
      const range = document.createRange();
      range.selectNodeContents(element);
      const text = range.getBoundingClientRect();
      const circle = element.getBoundingClientRect();
      return {
        left: text.left - circle.left,
        right: circle.right - text.right,
      };
    });
    expect(fit.left).toBeGreaterThan(4);
    expect(fit.right).toBeGreaterThan(4);
  }
  const contrast = await page.locator(".swim-marker").evaluate((element) => {
    const luminance = (color: string) => {
      const rgb = color
        .match(/[\d.]+/g)!
        .slice(0, 3)
        .map(Number)
        .map((channel) => {
          const v = channel / 255;
          return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        });
      return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
    };
    const marker = luminance(getComputedStyle(element).backgroundColor);
    const panel = luminance(
      getComputedStyle(element.closest(".standards-section")!).backgroundColor,
    );
    return (Math.max(marker, panel) + 0.05) / (Math.min(marker, panel) + 0.05);
  });
  expect(contrast).toBeGreaterThanOrEqual(3);
  await expect(page.locator(".standards-note")).toHaveCSS("font-size", "14px");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("live conversion, invalid input and course-specific unavailable events", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("./");
  await expect(page.getByTestId("result-SCY")).toHaveText("58.32");
  await page.locator("#category").selectOption("men");
  await page.locator("#event").selectOption("BR:200");
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "LCM" })
    .click();
  await page.locator("#swim-time").fill("2:16.71");
  await expect(page.getByTestId("result-SCY")).toHaveText("1:57.29");
  await page.locator("#swim-time").fill("1:60");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save comparison", exact: true }),
  ).toBeDisabled();
  await expect(page.getByTestId("result-SCY")).toHaveText("—");
  await page.locator("#swim-time").fill("1:00");
  await page.locator("#event").selectOption("IM:100");
  await expect(page.getByTestId("result-LCM")).toHaveText("—");
  await expect(
    page
      .getByRole("group", { name: "Swum in" })
      .getByRole("button", { name: "LCM" }),
  ).toBeDisabled();
  expect(errors).toEqual([]);
});
test("focused results follow the selected course, mapped event and invalid input", async ({
  page,
}) => {
  await page.goto("./");
  await page.getByLabel("Event", { exact: false }).selectOption("FR:400");
  await page.locator("#swim-time").fill("5:00");
  // The engine's canonical 400 free maps to 500 yards and 400 meters.
  await expect(page.locator("#event option:checked")).toHaveText(
    "500 Freestyle",
  );
  await expect(page.locator(".focused-context")).toHaveText(
    "400 Freestyle · LCM (50 m pool)",
  );
  await expect(page.getByTestId("focused-time")).toHaveText(
    (await page.getByTestId("result-LCM").textContent()) ?? "",
  );
  const original = page.getByRole("button", { name: /SCY ORIGINAL/ });
  await original.focus();
  await page.keyboard.press("Enter");
  await expect(original).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("focused-time")).toHaveText("5:00.00");
  await expect(page.locator(".focused-context")).toHaveText(
    "500 Freestyle · SCY (25 yd pool)",
  );
  await expect(page.locator(".focused-provenance")).toContainText(
    "Your original time",
  );
  await page.locator("#swim-time").fill("1:60");
  await expect(page.getByTestId("focused-time")).toHaveText("—");
  await expect(page.locator(".hundredths")).toHaveCount(0);
  await page.locator("#swim-time").fill("1:00");
  await page.locator("#event").selectOption("IM:100");
  await page.getByTestId("result-LCM").click();
  await expect(page.getByTestId("focused-time")).toHaveText("—");
  await expect(page.locator(".focused-provenance")).toContainText(
    "No conversion published",
  );
});

test("standards, altitude, local saves, restore and remove", async ({
  page,
}) => {
  await page.goto("./");
  await expect(
    page.getByRole("heading", { name: "A time, nicely done." }),
  ).toBeVisible();
  await expect(page.locator(".standard-achievement")).toContainText("1.83s");
  await page
    .getByRole("button", { name: "Save comparison", exact: true })
    .click();
  await expect(page.locator(".saved-card")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".saved-card")).toHaveCount(1);
  await page.locator("#swim-time").fill("1:04.00");
  await page.locator(".restore-swim").click();
  await expect(page.locator("#swim-time")).toHaveValue("58.32");
  await page.locator(".remove-swim").click();
  await expect(page.locator(".saved-card")).toHaveCount(0);
  await page.locator("#event").selectOption("FR:200");
  await page.locator("#swim-time").fill("2:00");
  await page.getByText("Swam at altitude?", { exact: true }).click();
  await page.locator("#altitude").fill("5280");
  await expect(page.getByTestId("result-SCY")).toHaveText("1:58.80");
});
test("share link restores inputs and CSV downloads", async ({ page }) => {
  await page.goto("./#t=2%3A16.71&s=BR&d=200&c=LCM&g=men&a=17-18&h=0");
  await expect(page.locator("#swim-time")).toHaveValue("2:16.71");
  await expect(page.getByTestId("result-SCY")).toHaveText("1:57.29");
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download course comparison as CSV" })
    .click();
  expect((await download).suggestedFilename()).toBe("turnmark-200-br.csv");
  await page.getByRole("button", { name: "Copy link", exact: true }).click();
  await expect(page.getByRole("status", { name: "Swim action" })).toContainText(
    /Link copied|Share link is ready/,
  );
});
test("responsive layout and accessible controls", async ({
  page,
}, testInfo) => {
  await page.goto("./");
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.screenshot({
    path: `test-results/turnmark-${testInfo.project.name}.png`,
    fullPage: true,
  });
});

test("long times and expanded elevation fit narrow layouts", async ({
  page,
}) => {
  for (const width of [320, 681]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("./");
    await page.locator("#swim-time").fill("60:00.00");
    if (!(await page.locator("#altitude").isVisible()))
      await page.getByText("Swam at altitude?", { exact: true }).click();
    await page.locator("#altitude").fill("5280");
    for (const time of await page
      .locator(".result-time, .focused-time, .elevation-entry")
      .all()) {
      expect(
        await time.evaluate(
          (element) => element.scrollWidth <= element.clientWidth,
        ),
      ).toBe(true);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});

test("conversion history records settled edits, persists, filters, restores and clears", async ({
  page,
}) => {
  await page.goto("./");
  await expect(page.locator(".history-row")).toHaveCount(0);
  await page.locator("#swim-time").fill("59.10");
  await expect(page.locator(".history-row")).toHaveCount(1);
  await expect(page.locator(".history-row")).toContainText("59.10");
  await page.reload();
  await expect(page.locator(".history-row")).toHaveCount(1);
  const historyA11y = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(historyA11y.violations.map((v) => v.id)).toEqual([]);
  await page.locator("#event").selectOption("BR:100");
  await page.locator("#swim-time").fill("1:12.50");
  await expect(page.locator(".history-row")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Filter history: Free", exact: true })
    .click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page.locator(".history-restore").click();
  await expect(page.locator("#swim-time")).toHaveValue("59.10");
  await expect(page.locator("#event")).toHaveValue("FR:100");
  // Invalid input must never enter history.
  await page.locator("#swim-time").fill("1:60");
  page.once("dialog", async (dialog) => {
    expect(dialog.type()).toBe("confirm");
    expect(dialog.message()).toContain(
      "Clear all conversion history on this device?",
    );
    await dialog.dismiss();
  });
  await page
    .getByRole("button", { name: "Clear history", exact: true })
    .click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".history-row")).toHaveCount(2);
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Clear history", exact: true })
    .click();
  await page.reload();
  await expect(page.locator(".history-row")).toHaveCount(0);
});

test("World Aquatics points score entered metric swims and leave yards unscored", async ({
  page,
}) => {
  await page.goto("./");
  await page
    .getByRole("button", { name: "World Aquatics points", exact: true })
    .click();
  await expect(page.getByTestId("points-score")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "SCY isn’t scored" }),
  ).toBeVisible();
  await expect(page.locator(".points-note")).toContainText("25m and 50m");
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "SCM" })
    .click();
  await page.locator("#swim-time").fill("49.93");
  await expect(page.getByTestId("points-score")).toHaveText("1,000");
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "LCM" })
    .click();
  await page.locator("#swim-time").fill("51.71");
  await expect(page.getByTestId("points-score")).toHaveText("1,000");
  const pointsA11y = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(pointsA11y.violations.map((v) => v.id)).toEqual([]);
});

test("mobile navigation reaches history and standards without covering content", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "Mobile navigation only");
  await page.goto("./");
  const resultsJump = page.getByRole("button", {
    name: "See your results",
    exact: true,
  });
  await resultsJump.click();
  await expect(page.locator("#results-title")).toBeFocused();
  await expect
    .poll(() =>
      page
        .locator("#results-title")
        .evaluate((element) => element.getBoundingClientRect().top),
    )
    .toBeLessThan(100);
  const seam = await page.evaluate(() =>
    Math.abs(
      document.querySelector(".input-panel")!.getBoundingClientRect().bottom -
        document.querySelector(".results-panel")!.getBoundingClientRect().top,
    ),
  );
  expect(seam).toBeGreaterThanOrEqual(12);
  expect(seam).toBeLessThanOrEqual(20);
  await page.locator("#swim-time").fill("invalid");
  await expect(resultsJump).toBeDisabled();
  await page.locator("#swim-time").fill("58.32");
  const nav = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(nav.getByRole("button")).toHaveText([
    "Converter",
    "Standards",
    "History",
  ]);
  await expect(nav.getByRole("button")).toHaveCount(3);
  await expect(nav.getByRole("button", { name: "The method" })).toHaveCount(0);
  await nav.getByRole("button", { name: "History", exact: true }).click();
  await expect(page.locator("#history")).toBeInViewport();
  await nav.getByRole("button", { name: "Standards", exact: true }).click();
  await expect(page.locator("#standards")).toBeInViewport();
  await expect(
    nav.getByRole("button", { name: "Standards", exact: true }),
  ).toHaveAttribute("aria-current", "location");
  await page.getByRole("button", { name: "How this is calculated" }).click();
  await expect(page.locator("#method")).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("history remembers target-course changes and explicit saves without duplicates", async ({
  page,
}) => {
  await page.goto("./");
  await page
    .getByRole("button", { name: "Save comparison", exact: true })
    .click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Save comparison", exact: true })
    .click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page.getByTestId("result-SCM").click();
  await expect(page.locator(".history-row")).toHaveCount(2);
  await expect(page.locator(".history-row").first()).toContainText("SCY → SCM");
  await page.locator(".history-remove").first().click();
  await expect(page.locator(".history-row")).toHaveCount(1);
});

test("elevation units preserve altitude and show the sea-level transformation", async ({
  page,
}) => {
  await page.goto("./#t=21%3A00.20&s=FR&d=1500&c=SCY&g=women&a=17-18&h=7200");
  await expect(page.locator("#altitude")).toBeVisible();
  await expect(page.getByTestId("altitude-original")).toHaveText("21:00.20");
  await expect(page.getByTestId("altitude-corrected")).toHaveText("20:27.70");
  await expect(page.locator(".altitude-before")).toContainText("7,200 ft");
  await expect(page.locator(".altitude-difference")).toContainText("−32.50s");
  const units = page.getByRole("group", { name: "Elevation units" });
  await units.getByRole("button", { name: "m", exact: true }).click();
  await expect(page.locator("#altitude")).toHaveValue("2194.6");
  await expect(page.locator(".altitude-before")).toContainText("2,194.6 m");
  await expect(page.getByTestId("altitude-corrected")).toHaveText("20:27.70");
  await units.getByRole("button", { name: "ft", exact: true }).click();
  await expect(page.locator("#altitude")).toHaveValue("7200");
  // Metric inputs use the same published bands as canonical feet.
  await page.locator("#event").selectOption("FR:200");
  await page.locator("#swim-time").fill("2:00");
  await units.getByRole("button", { name: "m", exact: true }).click();
  await page.locator("#altitude").fill("914.4");
  await expect(page.getByTestId("altitude-corrected")).toHaveText("1:59.50");
  await units.getByRole("button", { name: "ft", exact: true }).click();
  await expect(page.locator("#altitude")).toHaveValue("3000");
  await page.locator("#altitude").fill("2999");
  await expect(page.locator(".altitude-conversion")).toHaveCount(0);
  await expect(page.locator("#elevation-help")).toContainText(
    "no adjustment applies",
  );
  await page.locator("#altitude").fill("5280");
  await expect(page.getByTestId("altitude-corrected")).toHaveText("1:58.80");
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.locator("#altitude").fill("");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.locator(".altitude-conversion")).toHaveCount(0);
});

test("USMS adult targets handle categories, courses, missing data and share context", async ({
  page,
}) => {
  await page.goto("./");
  await page.locator("#standards-system").selectOption("masters");
  await expect(page.getByTestId("masters-target")).toHaveText("1:04.07");
  await expect(page.locator(".masters-status")).toContainText("5.75s faster");
  await page.locator("#masters-age").selectOption("25-29");
  await page.locator("#category").selectOption("men");
  await expect(page.getByTestId("masters-target")).toHaveText("53.00");
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "SCM" })
    .click();
  await expect(
    page.getByRole("heading", { name: "No SCM Nationals target" }),
  ).toBeVisible();
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "LCM" })
    .click();
  await expect(page.getByTestId("masters-target")).toHaveText("1:02.23");
  await page.locator("#masters-age").selectOption("85+");
  await expect(
    page.getByRole("heading", { name: "No NQT for ages 85+" }),
  ).toBeVisible();
  await page.goto(
    "./#t=58.32&s=FR&d=100&c=SCY&g=women&a=15-16&h=0&b=masters&ma=40-44",
  );
  await expect(page.locator("#standards-system")).toHaveValue("masters");
  await expect(page.locator("#masters-age")).toHaveValue("40-44");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});

test("theme follows system changes, respects a saved override and keeps dark controls accessible", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await page.goto("./");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const themes = page.getByRole("group", { name: "Appearance", exact: true });
  await themes.getByRole("button", { name: "Light", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await themes.getByRole("button", { name: "Auto", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});

test("method retains the NCAA source and install instructions are usable", async ({
  page,
}) => {
  await page.goto("./");
  await expect(
    page.locator("#method").getByRole("link", { name: /2025–27 NCAA rules/ }),
  ).toHaveAttribute("href", /PRXSW_RulesBook/);
  await page.getByRole("button", { name: "Install app", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "Install Turnmark" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Got it", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .getByText("What do SCY, SCM, and LCM mean?", { exact: true })
    .click();
  await expect(
    page.locator(".faq-answer").filter({ hasText: "25-yard pool" }),
  ).toBeVisible();
});

test("points explain the reference and next milestone; swimboard remove buttons stay circular", async ({
  page,
}) => {
  await page.goto("./#t=1%3A05&s=FR&d=100&c=SCM&g=women&a=15-16&h=0");
  await page
    .getByRole("button", { name: "World Aquatics points", exact: true })
    .click();
  await expect(page.locator(".points-tldr")).toContainText(
    "1,000 points matches the world-record reference time",
  );
  await expect(page.locator(".points-next")).toContainText("500 points");
  await expect(page.getByTestId("points-next-time")).not.toHaveText("—");
  await page
    .getByRole("button", { name: "Save comparison", exact: true })
    .click();
  const bounds = await page.locator(".remove-swim").boundingBox();
  expect(bounds).not.toBeNull();
  expect(Math.abs(bounds!.width - bounds!.height)).toBeLessThan(1);
  await expect(page.getByRole("status", { name: "Swim action" })).toHaveCSS(
    "opacity",
    "1",
  );
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page
    .getByRole("button", { name: "Compare with age-group time standards" })
    .click();
  await expect(page.locator("#standards-system")).toBeVisible();
});
