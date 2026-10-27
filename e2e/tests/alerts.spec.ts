import { test, expect, signInUi, accountFor, goTo } from "../support/fixtures";
import * as db from "../support/db";
import { execFileSync } from "node:child_process";
import path from "node:path";
import type { Page } from "@playwright/test";

async function openForm(page: Page) {
  await goTo(page, "Alerts");
  await page.getByRole("button", { name: "Add", exact: true }).click();
}

async function addSubscription(page: Page, ticker: string, type: string, threshold?: string) {
  await openForm(page);
  await page.getByLabel("Ticker").selectOption(ticker);
  await page.getByLabel("Alert type").selectOption(type);
  if (threshold !== undefined) await page.getByLabel("Price threshold in dollars").fill(threshold);
  await page.getByRole("button", { name: "Save" }).click();
}

test.describe("alert subscriptions", () => {
  test("add all four kinds and see them listed after a reload", async ({ page }) => {
    await signInUi(page, await accountFor());
    await addSubscription(page, "NVDA", "price_above", "500");
    await expect(page.getByText("Price closes above $500")).toBeVisible();
    await addSubscription(page, "AAPL", "price_below", "1");
    await expect(page.getByText("Price closes below $1")).toBeVisible();
    await addSubscription(page, "TGT", "news");
    await expect(page.getByText("New news articles")).toBeVisible();
    await addSubscription(page, "KO", "filing");
    await expect(page.getByText("New SEC filing")).toBeVisible();
    await page.reload();
    await goTo(page, "Alerts");
    for (const text of ["Price closes above $500", "Price closes below $1", "New news articles", "New SEC filing"]) await expect(page.getByText(text)).toBeVisible();
  });

  test("the form blocks incomplete input", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openForm(page);
    const save = page.getByRole("button", { name: "Save" });
    await expect(save).toBeDisabled();                       // no ticker
    await page.getByLabel("Ticker").selectOption("NVDA");
    await expect(save).toBeDisabled();                       // price type, no threshold
    await page.getByLabel("Price threshold in dollars").fill("0");
    await expect(save).toBeDisabled();                       // zero is not a price
    await page.getByLabel("Price threshold in dollars").fill("10");
    await expect(save).toBeEnabled();
    await page.getByLabel("Alert type").selectOption("news");
    await expect(page.getByLabel("Price threshold in dollars")).toHaveCount(0);
    await expect(save).toBeEnabled();                        // no threshold needed
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByLabel("Ticker")).toHaveCount(0);
  });

  test("the ticker list is alphabetical", async ({ page }) => {
    await signInUi(page, await accountFor());
    await openForm(page);
    const symbols = (await page.getByLabel("Ticker").locator("option").evaluateAll(os => os.map(o => (o as HTMLOptionElement).value))).filter(Boolean);
    expect(symbols).toEqual([...symbols].sort((a, b) => a.localeCompare(b)));
  });

  test("pause and resume survive a reload", async ({ page }) => {
    await signInUi(page, await accountFor());
    await addSubscription(page, "NVDA", "price_below", "1");
    const pause = page.getByRole("switch", { name: "Pause NVDA alert" });
    await expect(pause).toHaveAttribute("aria-checked", "true");
    await pause.click();
    const resume = page.getByRole("switch", { name: "Resume NVDA alert" });
    await expect(resume).toHaveAttribute("aria-checked", "false");
    await page.reload();
    await goTo(page, "Alerts");
    await expect(page.getByRole("switch", { name: "Resume NVDA alert" })).toHaveAttribute("aria-checked", "false");
    await page.getByRole("switch", { name: "Resume NVDA alert" }).click();
    await expect(page.getByRole("switch", { name: "Pause NVDA alert" })).toHaveAttribute("aria-checked", "true");
  });
});

test.describe("alerts list", () => {
  test("empty state", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Alerts");
    await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
    await expect(page.getByText(/unread notifications?/)).toBeVisible();
  });

  test("severity and unread filters", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await db.seedAlerts(acct.email, [
      { ticker: "TGT", message: "e2e high one", severity: "high" },
      { ticker: "NVDA", message: "e2e medium one", severity: "medium" },
      { ticker: "KO", message: "e2e low read", severity: "low", read: true },
    ]);
    await page.reload();
    await goTo(page, "Alerts");
    for (const m of ["e2e high one", "e2e medium one", "e2e low read"]) await expect(page.getByText(m)).toBeVisible();
    await page.getByRole("button", { name: "high", exact: true }).click();
    await expect(page.getByText("e2e high one")).toBeVisible();
    await expect(page.getByText("e2e medium one")).toHaveCount(0);
    await page.getByRole("button", { name: "low", exact: true }).click();
    await expect(page.getByText("e2e low read")).toBeVisible();
    await expect(page.getByText("e2e high one")).toHaveCount(0);
    await page.getByRole("button", { name: "unread", exact: true }).click();
    await expect(page.getByText("e2e low read")).toHaveCount(0);
    await page.getByRole("button", { name: "all", exact: true }).click();
    await expect(page.getByText("e2e medium one")).toBeVisible();
  });

  test("opening the Alerts page clears the unread badge", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await db.seedAlerts(acct.email, [{ ticker: "TGT", message: "e2e badge one" }, { ticker: "KO", message: "e2e badge two" }]);
    await page.reload();
    await expect(page.getByRole("button", { name: "Notifications, 2 unread" })).toBeVisible();
    await goTo(page, "Alerts");
    await expect(page.getByRole("button", { name: "Notifications", exact: true })).toBeVisible();
    expect(await db.one("SELECT count(*)::int AS n FROM alerts WHERE user_id = $1 AND NOT read", [await db.userIdByEmail(acct.email)])).toEqual({ n: 0 });
  });

  test("Mark all read", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await goTo(page, "Alerts");
    await db.seedAlerts(acct.email, [{ ticker: "TGT", message: "e2e mark all" }]);
    await page.reload();
    await goTo(page, "Alerts");
    await page.getByRole("button", { name: "Mark all read" }).click();
    await expect(page.getByText("0 unread notifications")).toBeVisible();
  });
});

test("a price alert fires after the data sync, shows in the bell, and clears when the Alerts page is opened", async ({ page }) => {
  const acct = await accountFor();
  await signInUi(page, acct);
  await addSubscription(page, "NVDA", "price_above", "1");          // any real close is above $1
  await expect(page.getByText("Price closes above $1")).toBeVisible();
  // The nightly sync ends by evaluating every subscription: run that same step against the test database.
  execFileSync(process.env.E2E_PYTHON ?? "python", [path.resolve(__dirname, "../../scripts/evaluate_alert_subscriptions.py")], { env: process.env, stdio: "pipe" });
  await page.reload();
  const bell = page.getByRole("button", { name: /^Notifications, \d+ unread$/ });
  await expect(bell).toBeVisible();
  await bell.click();
  await expect(page.getByText(/NVDA/).first()).toBeVisible();
  await page.keyboard.press("Escape");
  await goTo(page, "Alerts");
  await expect(page.getByRole("button", { name: "Notifications", exact: true })).toBeVisible();
});
