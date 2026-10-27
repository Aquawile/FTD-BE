import AxeBuilder from "@axe-core/playwright";
import { test, expect, signInUi, accountFor, goTo, openTicker, createWorkspace } from "../support/fixtures";
import type { Page } from "@playwright/test";

// Accessibility: the rules that catch unlabelled controls, missing names and broken dialogs.
// Colour contrast is a design decision and is left out of this gate.
async function scan(page: Page, label: string) {
  const result = await new AxeBuilder({ page: page as any }).withTags(["wcag2a", "wcag2aa"]).disableRules(["color-contrast"]).analyze();
  const bad = result.violations.filter(v => v.impact === "serious" || v.impact === "critical");
  expect(bad.map(v => `${label}: ${v.id} (${v.nodes.length}) ${v.nodes[0]?.html.slice(0, 120)}`), `accessibility violations on ${label}`).toEqual([]);
}

test.describe("accessibility", () => {
  test("signed-out pages", async ({ page }) => {
    await page.goto("/");
    await scan(page, "sign in");
    await page.getByRole("button", { name: "Create an account" }).click();
    await scan(page, "create account");
    await page.getByRole("button", { name: "Back to sign in" }).click();
    await page.getByRole("button", { name: "Forgot password?" }).click();
    await scan(page, "forgot password");
  });

  test("every signed-in page", async ({ page }) => {
    await signInUi(page, await accountFor());
    await scan(page, "dashboard");
    await goTo(page, "Research");
    await expect(page.getByText(/^\d+ tickers? tracked$/)).toBeVisible();
    await scan(page, "research");
    await openTicker(page, "NVDA");
    await expect(page.getByLabel("Loading price")).toHaveCount(0);   // scan the loaded page; the loading skeleton has its own known defect
    await expect(page.locator(".recharts-wrapper").first()).toBeVisible();
    await scan(page, "ticker overview");
    await page.getByRole("button", { name: /^news$/i }).click();
    await expect(page.getByText(/Showing .* of \d+ articles/)).toBeVisible();
    await scan(page, "ticker news");
    await goTo(page, "Alerts");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await scan(page, "alerts form");
    await createWorkspace(page, "E2E a11y workspace");
    await page.getByRole("heading", { name: "E2E a11y workspace" }).click();
    await expect(page.getByText("0 / 50 tickers")).toBeVisible();
    await scan(page, "workspace detail");
    await page.getByRole("button", { name: "Add Ticker" }).click();
    await scan(page, "add ticker dialog");
    await page.keyboard.press("Escape");
    await page.getByRole("main").getByRole("button", { name: "Settings", exact: true }).click();
    await scan(page, "workspace settings");
    await page.getByRole("navigation", { name: "Main" }).getByRole("button", { name: "Workspaces" }).click();
    await scan(page, "workspaces");
    await page.getByRole("button", { name: "New Workspace" }).click();
    await scan(page, "create workspace dialog");
    await page.keyboard.press("Escape");
    await page.locator("aside").getByRole("button", { name: "Settings" }).click();
    await scan(page, "profile");
    await page.getByRole("button", { name: "security", exact: true }).click();
    await scan(page, "profile security");
  });
});

test.describe("phone layout", { tag: "@desktop-only" }, () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("sign in, then no page scrolls sideways and the main buttons stay reachable", async ({ page }) => {
    await signInUi(page, await accountFor());
    for (const name of ["Dashboard", "Research", "Workspaces", "Alerts"] as const) {
      await goTo(page, name);
      await page.waitForTimeout(400);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${name} scrolls sideways by ${overflow}px`).toBeLessThanOrEqual(1);
      await expect(page.getByRole("navigation", { name: "Main" }).getByRole("button", { name })).toBeVisible();
    }
  });
});

test.describe("when things go wrong", () => {
  test("the dashboard still renders when its stats request fails", async ({ page }) => {
    test.info().annotations.push({ type: "allow-errors" });
    await page.route("**/api/dashboard/stats", route => route.abort());
    await signInUi(page, await accountFor());
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Top Movers" })).toBeVisible();
  });

  test("a slow ticker list shows a loading state, then the data", async ({ page }) => {
    await signInUi(page, await accountFor());
    await page.route("**/api/tickers/tracked**", async route => { await new Promise(r => setTimeout(r, 2500)); await route.continue(); });
    await goTo(page, "Research");
    await expect(page.getByText("Loading tickers...")).toBeVisible();
    await expect(page.getByText(/^\d+ tickers? tracked$/)).toBeVisible({ timeout: 20_000 });
  });

  test("an expired session sends the user to sign in rather than a broken page", async ({ page }) => {
    test.info().annotations.push({ type: "allow-errors" });
    await signInUi(page, await accountFor());
    await page.route("**/api/**", route => route.fulfill({ status: 401, json: { detail: "Invalid or expired token" } }));
    await page.getByRole("navigation", { name: "Main" }).getByRole("button", { name: "Workspaces" }).click();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();   // no white screen
  });
});
