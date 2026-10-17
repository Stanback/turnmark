import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("live conversion, invalid input and course-specific unavailable events", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("./");
  await expect(page.getByTestId("result-SCY")).toHaveText("58.32");
  await page.locator("#category").selectOption("men");
  await page.getByRole("button", { name: "Breast", exact: true }).click();
  await page.locator("#distance").selectOption("200");
  await page
    .getByRole("group", { name: "Swum in" })
    .getByRole("button", { name: "LCM" })
    .click();
  await page.locator("#swim-time").fill("2:16.71");
  await expect(page.getByTestId("result-SCY")).toHaveText("1:57.29");
  await page.locator("#swim-time").fill("1:60");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save swim", exact: true }),
  ).toBeDisabled();
  await expect(page.getByTestId("result-SCY")).toHaveText("—");
  await page.locator("#swim-time").fill("1:00");
  await page.getByRole("button", { name: "IM", exact: true }).click();
  await page.locator("#distance").selectOption("100");
  await expect(page.getByTestId("result-LCM")).toHaveText("—");
  await expect(
    page
      .getByRole("group", { name: "Swum in" })
      .getByRole("button", { name: "LCM" }),
  ).toBeDisabled();
  expect(errors).toEqual([]);
});
test("standards, altitude, local saves, restore and remove", async ({
  page,
}) => {
  await page.goto("./");
  await expect(
    page.getByRole("heading", { name: "A time, nicely done." }),
  ).toBeVisible();
  await expect(page.locator(".standard-achievement")).toContainText("1.83s");
  await page.getByRole("button", { name: "Save swim", exact: true }).click();
  await expect(page.locator(".saved-card")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".saved-card")).toHaveCount(1);
  await page.locator("#swim-time").fill("1:04.00");
  await page.locator(".restore-swim").click();
  await expect(page.locator("#swim-time")).toHaveValue("58.32");
  await page.locator(".remove-swim").click();
  await expect(page.locator(".saved-card")).toHaveCount(0);
  await page.locator("#distance").selectOption("200");
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
  await expect(page.getByRole("status")).toContainText(
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

test("long times fit the narrow desktop layout", async ({ page }) => {
  await page.setViewportSize({ width: 681, height: 1000 });
  await page.goto("./");
  await page.locator("#swim-time").fill("60:00.00");
  for (const time of await page.locator(".result-time").all()) {
    expect(
      await time.evaluate(
        (element) => element.scrollWidth <= element.clientWidth,
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
  await page.getByRole("button", { name: "Breast", exact: true }).click();
  await page.locator("#swim-time").fill("1:12.50");
  await expect(page.locator(".history-row")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Filter history: Free", exact: true })
    .click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page.locator(".history-restore").click();
  await expect(page.locator("#swim-time")).toHaveValue("59.10");
  await expect(
    page
      .getByRole("group", { name: "Stroke", exact: true })
      .getByRole("button", { name: "Free", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  // Invalid input must never enter history.
  await page.locator("#swim-time").fill("1:60");
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
  await expect(page.getByTestId("points-score")).toHaveText("—");
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
  const nav = page.getByRole("navigation", { name: "Mobile navigation" });
  await nav.getByRole("button", { name: "History", exact: true }).click();
  await expect(page.locator("#history")).toBeInViewport();
  await nav.getByRole("button", { name: "Standards", exact: true }).click();
  await expect(page.locator("#standards")).toBeInViewport();
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
  await page.getByRole("button", { name: "Save swim", exact: true }).click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page.getByRole("button", { name: "Save swim", exact: true }).click();
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page.getByTestId("result-SCM").click();
  await expect(page.locator(".history-row")).toHaveCount(2);
  await expect(page.locator(".history-row").first()).toContainText("SCY → SCM");
  await page.locator(".history-remove").first().click();
  await expect(page.locator(".history-row")).toHaveCount(1);
});
