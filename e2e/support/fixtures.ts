import { test as base, expect, type Page } from "@playwright/test";
import * as emu from "./emulator";
import { TARGET } from "../playwright.config";

export { expect, TARGET };
export type { Account } from "./emulator";

/** Console messages that are expected noise when a test deliberately triggers an HTTP error. */
const BENIGN = /Failed to load resource|status of 4\d\d|net::ERR_|favicon/i;

export const test = base.extend<{
  /** Fails the test on uncaught page errors and console errors, and on any call to real Firebase hosts. */
  page: Page;
}>({
  page: async ({ page }, use, testInfo) => {
    const problems: string[] = [];
    page.on("pageerror", e => problems.push(`pageerror: ${e.message}`));
    page.on("console", m => { if (m.type() === "error" && !BENIGN.test(m.text())) problems.push(`console.error: ${m.text()}`); });
    if (TARGET === "emulator") {
      // Safety net: a build that is not pointed at the emulator must never create real Firebase accounts.
      await page.route(/https:\/\/(identitytoolkit|securetoken)\.googleapis\.com\//, route => {
        problems.push(`REAL FIREBASE CALL BLOCKED: ${route.request().url()}`);
        return route.abort();
      });
    }
    await use(page);
    // A test that breaks something on purpose (API down, ...) opts out with test.info().annotations.push({ type: "allow-errors" }).
    if (!testInfo.annotations.some(a => a.type === "allow-errors")) expect(problems, "unexpected browser errors").toEqual([]);
  },
});

/** The account a test signs in with: a fresh verified one (emulator) or the dedicated staging account. */
export async function accountFor(): Promise<emu.Account> {
  if (TARGET === "staging") {
    const { E2E_EMAIL: email, E2E_PASSWORD: password } = process.env;
    if (!email || !password) throw new Error("E2E_EMAIL and E2E_PASSWORD are required for E2E_TARGET=staging");
    return { email, password, uid: "staging" };
  }
  return emu.verifiedAccount();
}

export async function signInUi(page: Page, acct: { email: string; password: string }, opts: { remember?: boolean } = {}) {
  await page.goto("/");
  await page.getByLabel("Email address").fill(acct.email);
  await page.getByLabel("Password", { exact: true }).fill(acct.password);
  if (opts.remember === false) await page.getByLabel("Remember me").uncheck();
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

export async function goTo(page: Page, name: "Dashboard" | "Research" | "Workspaces" | "Alerts") {
  await page.getByRole("navigation", { name: "Main" }).getByRole("button", { name }).click();
}

/** Open a ticker's page through the Research list, the way a user does. */
export async function openTicker(page: Page, symbol: string) {
  await goTo(page, "Research");
  await page.getByRole("textbox", { name: "Search tickers and companies" }).fill(symbol);
  await page.getByText(symbol, { exact: true }).first().click();
  await expect(page.getByRole("button", { name: /^news$/i })).toBeVisible();
}

export async function createWorkspace(page: Page, name: string) {
  await goTo(page, "Workspaces");
  await page.getByRole("button", { name: "New Workspace" }).click();
  await page.getByLabel("Workspace name").fill(name);
  await page.getByRole("dialog").getByRole("button", { name: "Create Workspace" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
}
