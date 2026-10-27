import { test, expect, signInUi, accountFor, goTo, createWorkspace, TARGET } from "../support/fixtures";
import * as db from "../support/db";
import type { Page } from "@playwright/test";

const percents = async (page: Page) => (await page.locator("main").getByText(/^[+-]\d+\.\d{2}%$/).allTextContents()).map(t => parseFloat(t));
const isNonIncreasingAbs = (xs: number[]) => xs.every((x, i) => i === 0 || Math.abs(xs[i - 1]) >= Math.abs(x));

test.describe("dashboard", () => {
  test("stats, Top Movers (largest moves first) and the Top Mover row opens its ticker", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await expect(page.getByText("Articles Analyzed")).toBeVisible();
    await expect(page.getByText("Tickers Tracked")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Top Movers" })).toBeVisible();
    await expect.poll(async () => (await percents(page)).length).toBeGreaterThanOrEqual(3);
    expect(isNonIncreasingAbs(await percents(page))).toBe(true);
    if (TARGET === "emulator") {
      const { n } = await db.one<{ n: string }>("SELECT count(*) AS n FROM tickers");
      await expect(page.getByText("Tickers Tracked").locator("xpath=..")).toContainText(n);
    }
    const first = page.locator("main").getByText(/^[A-Z]{1,5}$/).first();
    await first.click();
    await expect(page.getByRole("button", { name: /^news$/i })).toBeVisible();
  });

  test("View all, All alerts and Manage links go to their pages", async ({ page }) => {
    await signInUi(page, await accountFor());
    await page.getByRole("button", { name: "View all →" }).click();
    await expect(page.getByRole("textbox", { name: "Search tickers and companies" })).toBeVisible();
    await goTo(page, "Dashboard");
    await page.getByRole("button", { name: "All alerts →" }).click();
    await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
    await goTo(page, "Dashboard");
    await page.getByRole("button", { name: "Manage →" }).click();
    await expect(page.getByRole("heading", { name: "My Workspaces" })).toBeVisible();
  });

  test("Recent Alerts and My Workspaces panels show the user's own data", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await expect(page.getByText("No workspaces yet")).toBeVisible();
    await db.seedAlerts(acct.email, [{ ticker: "TGT", message: "e2e dashboard alert" }]);
    await createWorkspace(page, "E2E dashboard workspace");
    await goTo(page, "Dashboard");
    await expect(page.getByText("e2e dashboard alert").first()).toBeVisible();
    await expect(page.getByText("E2E dashboard workspace").first()).toBeVisible();
    await page.getByText("E2E dashboard workspace").click();
    await expect(page.getByRole("heading", { name: "E2E dashboard workspace" })).toBeVisible();
  });
});

test.describe("research", () => {
  test("lists every tracked ticker with its company name", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Research");
    const count = page.getByText(/^\d+ tickers? tracked$/);
    await expect(count).toBeVisible();
    const shown = parseInt((await count.textContent())!, 10);
    if (TARGET === "emulator") {
      const { n } = await db.one<{ n: string }>("SELECT count(*) AS n FROM tickers");
      expect(shown).toBe(Number(n));
      await expect(page.getByText("Target Corporation")).toBeVisible();
      await expect(page.getByText("NVIDIA Corp")).toBeVisible();
    } else {
      expect(shown).toBeGreaterThan(100);
    }
  });

  test("search by symbol or company name, then clear", async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Research");
    const box = page.getByRole("textbox", { name: "Search tickers and companies" });
    const count = page.getByText(/^\d+ tickers? tracked$/);
    const all = await count.textContent();
    await box.fill("electronic");
    await expect(count).toHaveText("1 tickers tracked");
    await expect(page.getByText("Electronic Arts")).toBeVisible();
    await box.fill("tgt");
    await expect(page.getByText("Target Corporation")).toBeVisible();
    await box.fill("zzzzzz");
    await expect(page.getByText("No tickers found")).toBeVisible();
    await box.fill("");
    await expect(count).toHaveText(all!);
  });

  test("sort by biggest daily move puts the largest absolute change first", async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Research");
    await page.getByRole("combobox", { name: "Sort tickers by" }).selectOption("change");
    await expect.poll(async () => isNonIncreasingAbs((await percents(page)).slice(0, 12))).toBe(true);
  });

  test("the dead sector chips and Filter button are gone", async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Research");
    await expect(page.getByRole("button", { name: /^Filter$/ })).toHaveCount(0);
    for (const chip of ["SEMICONDUCTORS", "CLOUD", "All sectors"]) await expect(page.getByText(chip, { exact: true })).toHaveCount(0);
  });

  test("a ticker row opens that ticker", async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Research");
    await page.getByRole("textbox", { name: "Search tickers and companies" }).fill("nvda");
    await page.getByText("NVDA", { exact: true }).click();
    await expect(page.getByRole("button", { name: /^news$/i })).toBeVisible();
  });
});
