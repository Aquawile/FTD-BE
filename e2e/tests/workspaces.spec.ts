import { test, expect, signInUi, accountFor, goTo, createWorkspace } from "../support/fixtures";
import type { Page } from "@playwright/test";

const openWorkspace = async (page: Page, name: string) => {
  await goTo(page, "Workspaces");
  await page.getByRole("heading", { name }).click();
  await expect(page.getByText(/\d+ \/ 50 tickers/)).toBeVisible();
};
const addTicker = async (page: Page, query: string, symbol: string) => {
  await page.getByRole("button", { name: "Add Ticker" }).click();
  await page.getByRole("textbox", { name: "Search ticker or company name" }).fill(query);
  await page.getByRole("dialog").getByText(symbol, { exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
};

test.describe("creating", () => {
  test("by button, with the date shown plainly", { tag: "@staging" }, async ({ page }) => {
    await signInUi(page, await accountFor());
    await createWorkspace(page, "E2E created by button");
    await goTo(page, "Workspaces");
    await expect(page.getByText(/^Created \d{4}-\d{2}-\d{2} · 0 tickers$/)).toBeVisible();
    await page.getByRole("button", { name: "Archive E2E created by button" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Archive" }).click();
    await expect(page.getByRole("heading", { name: "E2E created by button" })).toHaveCount(0);
  });

  test("by pressing Enter, and an empty name is blocked", async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Workspaces");
    await page.getByRole("button", { name: "New Workspace" }).click();
    const name = page.getByLabel("Workspace name");
    await expect(page.getByRole("dialog").getByRole("button", { name: "Create Workspace" })).toBeDisabled();
    await name.fill("   ");
    await name.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();     // blank name: Enter does nothing
    await name.fill("E2E created by enter");
    await name.press("Enter");
    await expect(page.getByRole("heading", { name: "E2E created by enter" })).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("the dialog closes with X, Cancel, Escape and a click outside", async ({ page }) => {
    await signInUi(page, await accountFor());
    await goTo(page, "Workspaces");
    const open = () => page.getByRole("button", { name: "New Workspace" }).click();
    const dialog = page.getByRole("dialog", { name: "Create New Workspace" });
    await open(); await expect(dialog).toBeVisible();
    await page.getByRole("button", { name: "Close dialog" }).click(); await expect(dialog).toHaveCount(0);
    await open(); await page.getByRole("button", { name: "Cancel" }).click(); await expect(dialog).toHaveCount(0);
    await open(); await page.keyboard.press("Escape"); await expect(dialog).toHaveCount(0);
    await open(); await page.mouse.click(5, 5); await expect(dialog).toHaveCount(0);
  });
});

test.describe("inside a workspace", () => {
  test("add a ticker by company name, show its change to two decimals, open it, remove it", async ({ page }) => {
    await signInUi(page, await accountFor());
    await createWorkspace(page, "E2E tickers");
    await goTo(page, "Workspaces");
    await page.getByRole("heading", { name: "E2E tickers" }).click();
    await expect(page.getByText("0 / 50 tickers")).toBeVisible();
    await addTicker(page, "Target", "TGT");
    await expect(page.getByText("1 / 50 tickers")).toBeVisible();
    await expect(page.getByText(/^[+-]\d+\.\d{2}%$/)).toBeVisible();      // 6.2517 in the data, shown as 6.25
    await page.getByText("TGT", { exact: true }).click();                 // the card opens the ticker page
    await expect(page.getByRole("button", { name: /^news$/i })).toBeVisible();
    await goTo(page, "Workspaces");
    await page.getByRole("heading", { name: "E2E tickers" }).click();
    await page.getByRole("button", { name: "Remove TGT" }).click();
    await expect(page.getByText("0 / 50 tickers")).toBeVisible();
    await expect(page.getByText("TGT", { exact: true })).toHaveCount(0);
  });

  test("the add-ticker list is alphabetical and its search finds by name", async ({ page }) => {
    await signInUi(page, await accountFor());
    await createWorkspace(page, "E2E add list");
    await goTo(page, "Workspaces");
    await page.getByRole("heading", { name: "E2E add list" }).click();
    await page.getByRole("button", { name: "Add Ticker" }).click();
    const symbols = await page.getByRole("dialog").locator("button .font-mono").allTextContents();
    expect(symbols.length).toBeGreaterThan(3);
    expect(symbols).toEqual([...symbols].sort((a, b) => a.localeCompare(b)));
    await page.getByRole("textbox", { name: "Search ticker or company name" }).fill("coca");
    await expect(page.getByRole("dialog").getByText("KO", { exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
});

test.describe("workspace settings", () => {
  test("rename, describe, toggle filing alerts; everything is still there after a reload", async ({ page }) => {
    await signInUi(page, await accountFor());
    await createWorkspace(page, "E2E settings before");
    await goTo(page, "Workspaces");
    await page.getByRole("heading", { name: "E2E settings before" }).click();
    await page.getByRole("button", { name: "Settings" }).click();
    await page.getByLabel("Workspace name").fill("E2E settings after");
    await page.getByLabel("Description (optional)").fill("e2e description");
    await page.getByRole("button", { name: "Save Changes" }).click();
    await expect(page.getByRole("button", { name: "Save Changes" })).toBeVisible();
    const toggle = page.getByRole("switch", { name: "Alert on new SEC filings" });
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-checked", "true");
    await page.reload();
    await goTo(page, "Workspaces");
    await page.getByRole("button", { name: "E2E settings after settings" }).click();      // the card's three-dot button
    await expect(page.getByLabel("Workspace name")).toHaveValue("E2E settings after");
    await expect(page.getByLabel("Description (optional)")).toHaveValue("e2e description");
    await expect(page.getByRole("switch", { name: "Alert on new SEC filings" })).toHaveAttribute("aria-checked", "true");
  });

  test("archive: Escape cancels, confirming hides the workspace for good", async ({ page }) => {
    await signInUi(page, await accountFor());
    await createWorkspace(page, "E2E to archive");
    await goTo(page, "Workspaces");
    await page.getByRole("heading", { name: "E2E to archive" }).click();
    await page.getByRole("button", { name: "Settings" }).click();
    await page.getByRole("button", { name: "Archive Workspace" }).click();
    await expect(page.getByRole("dialog", { name: "Archive workspace?" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.getByRole("button", { name: "Archive Workspace" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Archive" }).click();
    await expect(page.getByRole("heading", { name: "My Workspaces" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "E2E to archive" })).toHaveCount(0);
    await page.reload();
    await goTo(page, "Workspaces");
    await expect(page.getByRole("heading", { name: "E2E to archive" })).toHaveCount(0);
  });

  test.fixme("a workspace holds at most 50 tickers (the page says so; the API does not enforce it yet)", async ({ page }) => {
    // Known defect: POST /workspaces/{id}/tickers has no cap, while the UI shows "n / 50 tickers".
    // Remove the fixme once the API refuses the 51st ticker.
    await signInUi(page, await accountFor());
  });
});
