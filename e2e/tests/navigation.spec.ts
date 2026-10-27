import { test, expect, signInUi, accountFor, goTo, TARGET } from "../support/fixtures";
import * as db from "../support/db";
import type { Page } from "@playwright/test";

const mainNav = (page: Page) => page.getByRole("navigation", { name: "Main" });
const dashboardHeading = (page: Page) => page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ });

test.describe("sidebar", () => {
  test("each sidebar button opens its page", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Research");
    await expect(page.getByRole("textbox", { name: "Search tickers and companies" })).toBeVisible();
    await goTo(page, "Workspaces");
    await expect(page.getByRole("heading", { name: "My Workspaces" })).toBeVisible();
    await goTo(page, "Alerts");
    await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
    await goTo(page, "Dashboard");
    await expect(dashboardHeading(page)).toBeVisible();
    await page.getByRole("button", { name: "Settings" }).click();
    await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible();
  });

  test("collapse and expand with the mouse, keeping every button reachable", { tag: "@desktop-only" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    const aside = page.locator("aside");
    const wide = (await aside.boundingBox())!.width;
    await page.getByRole("button", { name: "Collapse sidebar" }).click();
    await expect.poll(async () => (await aside.boundingBox())!.width).toBeLessThan(100);
    for (const name of ["Dashboard", "Research", "Workspaces", "Alerts"]) await expect(mainNav(page).getByRole("button", { name })).toBeVisible();
    await page.getByRole("button", { name: "Expand sidebar" }).click(); // a real click: it used to sit under the top bar
    await expect.poll(async () => (await aside.boundingBox())!.width).toBeGreaterThan(wide - 5);
  });

  test("a sidebar button works from the keyboard", async ({ page }) => {
    await signInUi(page, await accountFor());
    await mainNav(page).getByRole("button", { name: "Alerts" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
  });
});

test.describe("top bar", () => {
  test("top search opens Research with matching results", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await page.getByRole("textbox", { name: "Search tickers, companies, topics" }).fill("Nvidia");
    await page.keyboard.press("Enter");
    await expect(page.getByText("NVDA", { exact: true })).toBeVisible();
    await expect(page.getByText(/^\d+ tickers? tracked$/)).toBeVisible();
  });

  test("account menu shows who is signed in; Profile opens; Sign Out signs out", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await page.getByRole("button", { name: "Account menu" }).click();
    await expect(page.getByText(acct.email, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Profile" }).click();
    await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible();
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Sign Out" })).toHaveCount(0);
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("bell: empty state, then unread badge, list, mark all read, Escape", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await page.getByRole("button", { name: "Notifications", exact: true }).click();
    await expect(page.getByText("No notifications yet")).toBeVisible();
    await page.keyboard.press("Escape");

    await db.seedAlerts(acct.email, [
      { ticker: "TGT", message: "e2e bell alert one", severity: "high" },
      { ticker: "NVDA", message: "e2e bell alert two" },
      { ticker: "KO", message: "e2e bell alert three", severity: "low" },
      { ticker: "AAPL", message: "e2e bell already read", read: true },
    ]);
    await page.reload();
    const bell = page.getByRole("button", { name: "Notifications, 3 unread" });
    await expect(bell).toBeVisible();
    await bell.click();
    const panel = page.locator("div.absolute").filter({ hasText: "View all alerts and manage subscriptions" }).last();
    await expect(panel.getByText("e2e bell alert one")).toBeVisible();
    await expect(panel.getByText("e2e bell already read")).toBeVisible();
    await page.getByRole("button", { name: "Mark all read" }).click();
    await expect(page.getByRole("button", { name: "Notifications", exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByText("View all alerts and manage subscriptions")).toHaveCount(0);
  });

  test("clicking an alert in the bell opens the Alerts page", async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await db.seedAlerts(acct.email, [{ ticker: "NVDA", message: "e2e click-through alert" }]);
    await page.reload();
    await expect(page.getByRole("button", { name: "Notifications, 1 unread" })).toBeVisible();
    await expect(page.locator("[data-sonner-toast]")).toHaveCount(0, { timeout: 20_000 });   // the "new alert" pop-up sits over the bell panel
    await page.getByRole("button", { name: /^Notifications/ }).click();
    await page.locator("div.absolute").filter({ hasText: "View all alerts and manage subscriptions" }).last().getByText("e2e click-through alert").click();
    await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
  });
});

test("an inner page refresh keeps the user signed in", async ({ page }) => {
  await signInUi(page, await accountFor());
  await goTo(page, "Workspaces");
  await page.reload();
  await expect(mainNav(page)).toBeVisible(); // the app keeps its page in memory, so it lands back on a valid page
  await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible();
  expect(TARGET === "emulator" || TARGET === "staging").toBeTruthy();
});
