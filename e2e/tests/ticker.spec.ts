import { test, expect, signInUi, accountFor, openTicker, createWorkspace, goTo, TARGET } from "../support/fixtures";
import * as db from "../support/db";
import type { Page } from "@playwright/test";

const newsTab = (page: Page) => page.getByRole("button", { name: /^news$/i });
const total = async (page: Page) => {
  const label = page.getByText(/Showing .* of \d+ articles/);
  await expect(label).toBeVisible();
  return parseInt(/of (\d+) articles/.exec((await label.textContent())!)![1], 10);
};
const dbCount = async (sql: string, args: unknown[] = []) => Number((await db.one<{ n: string }>(sql, args)).n);

test.describe("ticker page: overview", () => {
  test("header, key financials and a chart that follows the cursor", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await expect(page.getByText("NVDA", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/\$\d/).first()).toBeVisible();
    await expect(page.getByText("Key Financials")).toBeVisible();
    await expect(page.getByText("Current Price")).toBeVisible();
    const chart = page.locator(".recharts-wrapper").first();
    await expect(chart).toBeVisible();
    const box = (await chart.boundingBox())!;
    const tooltip = page.locator(".recharts-tooltip-wrapper").first();
    const seen = new Set<string>();
    for (let x = 0; x < box.width; x += 4) {                   // days without a quote have no tooltip, so sweep the plot
      await page.mouse.move(box.x + x, box.y + box.height * 0.5);
      if (await tooltip.isVisible()) seen.add((await tooltip.innerText()).trim());
    }
    expect(seen.size, "the tooltip follows the cursor to different days").toBeGreaterThanOrEqual(2);
    expect([...seen][0]).toMatch(/\$\d/);
  });

  test("a ticker whose quote is old shows when that quote is from", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "EA");
    await expect(page.getByText(/2026-08-0[34]/).first()).toBeVisible();
  });

  test("Overview and News tabs switch", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await newsTab(page).click();
    await expect(page.getByText(/Showing .* of \d+ articles/)).toBeVisible();
    await page.getByRole("button", { name: /^overview$/i }).click();
    await expect(page.getByText("Key Financials")).toBeVisible();
  });
});

test.describe("ticker page: news", () => {
  test("date presets show the right number of articles", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await newsTab(page).click();
    const counts: Record<string, number> = {};
    for (const [name, days] of [["30 days", 30], ["90 days", 90], ["1 year", 365]] as const) {
      await page.getByRole("button", { name, exact: true }).click();
      await expect.poll(async () => total(page)).toBeGreaterThan(0);
      counts[name] = await total(page);
      if (TARGET === "emulator") {
        expect(counts[name]).toBe(await dbCount("SELECT count(*) AS n FROM staging_gnews WHERE target_ticker = 'NVDA' AND normalized_calendar_date >= current_date - $1::int", [days]));
      }
    }
    await page.getByRole("button", { name: /^All/ }).click();
    counts.all = await total(page);
    expect(counts["30 days"]).toBeLessThanOrEqual(counts["90 days"]);
    expect(counts["90 days"]).toBeLessThanOrEqual(counts["1 year"]);
    expect(counts["1 year"]).toBeLessThanOrEqual(counts.all);
  });

  test("every article of the ticker is shown, whatever its attribution label", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await newsTab(page).click();
    await page.getByRole("button", { name: /^All/ }).click();
    expect(await total(page)).toBe(await dbCount("SELECT count(*) AS n FROM staging_gnews WHERE target_ticker = 'NVDA'"));
    const labels = await db.many<{ attributed_by: string | null }>("SELECT DISTINCT attributed_by FROM staging_gnews WHERE target_ticker = 'NVDA' AND content_body LIKE 'E2E NVDA%'");
    expect(labels.map(l => l.attributed_by).sort()).toEqual([null, "batch", "dollar", "name", "none"].sort());
  });

  test("custom date range", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await newsTab(page).click();
    await page.getByRole("button", { name: "Custom" }).click();
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    const to = new Date(); const from = new Date(Date.now() - 60 * 864e5);
    await page.getByLabel("From", { exact: true }).fill(iso(from));
    await page.getByLabel("To", { exact: true }).fill(iso(to));
    await expect.poll(async () => total(page)).toBe(await dbCount(
      "SELECT count(*) AS n FROM staging_gnews WHERE target_ticker = 'NVDA' AND normalized_calendar_date BETWEEN $1 AND $2", [iso(from), iso(to)]));
  });

  test("pagination: Next, Prev, Oldest, Newest", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await newsTab(page).click();
    await page.getByRole("button", { name: /^All/ }).click();
    const n = await total(page);
    expect(n).toBeGreaterThan(40);
    const range = page.getByText(/Showing .* of \d+ articles/);
    await expect(range).toContainText(`Showing 1–20 of ${n}`);
    await page.getByRole("button", { name: "Next" }).click();
    await expect(range).toContainText(`Showing 21–40 of ${n}`);
    await page.getByRole("button", { name: "Prev" }).click();
    await expect(range).toContainText(`Showing 1–20 of ${n}`);
    await page.getByRole("button", { name: "Oldest" }).click();
    await expect(range).toContainText(`of ${n}`);
    await expect(range).not.toContainText("Showing 1–20");
    await page.getByRole("button", { name: "Newest" }).click();
    await expect(range).toContainText(`Showing 1–20 of ${n}`);
  });

  test("View article links open the source in a new tab", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await newsTab(page).click();
    const link = page.getByRole("link", { name: "View article" }).first();
    await expect(link).toHaveAttribute("href", /^https?:\/\//);
    await expect(link).toHaveAttribute("target", "_blank");
  });

  test("a ticker with a few articles lists them all", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "KO");
    await newsTab(page).click();
    await page.getByRole("button", { name: /^All/ }).click();
    expect(await total(page)).toBe(await dbCount("SELECT count(*) AS n FROM staging_gnews WHERE target_ticker = 'KO'"));
  });
});

test.describe("ticker page: actions", () => {
  test("Set Alert opens the Alerts form with this ticker chosen", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await page.getByRole("button", { name: "Set Alert" }).first().click();
    await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
    await expect(page.getByLabel("Ticker", { exact: true })).toHaveValue("NVDA");
  });

  test("Add to Workspace with no workspace offers to create one", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openTicker(page, "NVDA");
    await page.getByRole("button", { name: "Add to Workspace" }).first().click();
    await expect(page.getByRole("dialog", { name: "Add NVDA to a workspace" })).toBeVisible();
    await expect(page.getByText("You don't have any workspaces yet.")).toBeVisible();
    await page.getByRole("button", { name: "Create a workspace" }).click();
    await expect(page.getByRole("heading", { name: "My Workspaces" })).toBeVisible();
  });

  test("Add to Workspace adds the ticker to a chosen workspace", async ({ page }) => {
    await signInUi(page, await accountFor());
    await createWorkspace(page, "E2E picker workspace");
    await openTicker(page, "NVDA");
    await page.getByRole("button", { name: "Add to Workspace" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Add NVDA to a workspace" });
    await dialog.getByRole("button", { name: /E2E picker workspace/ }).click();
    await expect(dialog.getByText("Added")).toBeVisible();
    await page.keyboard.press("Escape");
    await goTo(page, "Workspaces");
    await page.getByRole("heading", { name: "E2E picker workspace" }).click();
    await expect(page.getByText("NVDA", { exact: true })).toBeVisible();
  });
});
