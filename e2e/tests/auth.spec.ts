import { test, expect, signInUi, accountFor } from "../support/fixtures";
import * as emu from "../support/emulator";
import type { Page } from "@playwright/test";

const dashboardHeading = (page: Page) => page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ });
const mainNav = (page: Page) => page.getByRole("navigation", { name: "Main" });

async function persistedSessions(page: Page) {
  return page.evaluate(async () => {
    const session = Object.keys(sessionStorage).filter(k => k.startsWith("firebase:authUser")).length;
    const local = await new Promise<number>(resolve => {
      const req = indexedDB.open("firebaseLocalStorageDb");
      req.onerror = () => resolve(0);
      req.onsuccess = () => {
        try {
          const keys = req.result.transaction("firebaseLocalStorage").objectStore("firebaseLocalStorage").getAllKeys();
          keys.onsuccess = () => resolve((keys.result as string[]).filter(k => String(k).startsWith("firebase:authUser")).length);
          keys.onerror = () => resolve(0);
        } catch { resolve(0); }
      };
    });
    return { session, local };
  });
}

test.describe("sign in page", () => {
  test("show/hide password, remember me, and an empty form is blocked", async ({ page }) => {
    await page.goto("/");
    const pw = page.getByLabel("Password", { exact: true });
    await expect(pw).toHaveAttribute("type", "password");
    await page.getByRole("button", { name: "Show password" }).click();
    await expect(pw).toHaveAttribute("type", "text");
    await page.getByRole("button", { name: "Hide password" }).click();
    await expect(pw).toHaveAttribute("type", "password");
    const remember = page.getByLabel("Remember me");
    await expect(remember).toBeChecked();
    await remember.uncheck();
    await expect(remember).not.toBeChecked();
    await expect(page.getByRole("button", { name: "Sign In" })).toBeDisabled();
    await page.getByLabel("Email address").fill("someone@example.test");
    await expect(page.getByRole("button", { name: "Sign In" })).toBeDisabled();
    await pw.fill("x");
    await expect(page.getByRole("button", { name: "Sign In" })).toBeEnabled();
  });

  test("links between sign in, forgot password and create account", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Forgot password?" }).click();
    await expect(page.getByRole("heading", { name: "Reset your password" })).toBeVisible();
    await page.getByRole("button", { name: "Back to sign in" }).click();
    await page.getByRole("button", { name: "Create an account" }).click();
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    await page.getByRole("button", { name: "Back to sign in" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("keyboard only: Tab to the fields and Enter signs in", async ({ page }) => {
    const acct = await accountFor();
    await page.goto("/");
    await page.getByLabel("Email address").focus();
    await page.keyboard.type(acct.email);
    await page.keyboard.press("Tab");
    await page.keyboard.type(acct.password);
    await page.keyboard.press("Enter");
    await expect(mainNav(page)).toBeVisible();
  });
});

test.describe("signing in and out", () => {
  test("wrong password is refused with a clear message", async ({ page }) => {
    const acct = await emu.verifiedAccount("wrongpw");
    await page.goto("/");
    await page.getByLabel("Email address").fill(acct.email);
    await page.getByLabel("Password", { exact: true }).fill("not-the-password");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
    await expect(mainNav(page)).toHaveCount(0);
  });

  test("sign in, survive a reload, sign out, sign back in", { tag: "@staging" }, async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await expect(dashboardHeading(page)).toBeVisible();
    await page.reload();
    await expect(mainNav(page)).toBeVisible();
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await signInUi(page, acct);
  });

  test("remember me keeps the session on this browser; unticked keeps it for the tab only", async ({ page }) => {
    const acct = await emu.verifiedAccount("remember");
    await signInUi(page, acct, { remember: true });
    await expect.poll(() => persistedSessions(page)).toEqual({ session: 0, local: 1 });
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await signInUi(page, acct, { remember: false });
    await expect.poll(() => persistedSessions(page)).toEqual({ session: 1, local: 0 });
  });

  test("an account created before email verification was required gets straight in", async ({ page }) => {
    const email = "legacy.unverified@example.test";
    await emu.importLegacyUser("e2e-legacy-uid", email, "Passw0rd!x", new Date("2026-09-01T10:00:00Z"));
    await signInUi(page, { email, password: "Passw0rd!x" });
    await expect(dashboardHeading(page)).toBeVisible();
  });
});

test.describe("forgot password", () => {
  test("reset link is sent, the new password works and the old one does not", async ({ page }) => {
    const acct = await emu.verifiedAccount("forgot");
    await page.goto("/");
    await page.getByRole("button", { name: "Forgot password?" }).click();
    await page.getByLabel("Email address").fill(acct.email);
    await page.getByRole("button", { name: "Send Reset Link" }).click();
    await expect(page.getByRole("button", { name: "Return to Sign In" })).toBeVisible();
    const oob = await emu.latestOob(acct.email, "PASSWORD_RESET");
    expect(oob, "the emulator recorded a password-reset email").toBeTruthy();
    await emu.resetPassword(oob!.oobCode, "NewPassw0rd!y");
    await page.getByRole("button", { name: "Return to Sign In" }).click();
    await page.getByLabel("Email address").fill(acct.email);
    await page.getByLabel("Password", { exact: true }).fill(acct.password);
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
    await page.getByLabel("Password", { exact: true }).fill("NewPassw0rd!y");
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(mainNav(page)).toBeVisible();
  });

  test("the send button needs a plausible email", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Forgot password?" }).click();
    await expect(page.getByRole("button", { name: "Send Reset Link" })).toBeDisabled();
    await page.getByLabel("Email address").fill("not-an-email");
    await expect(page.getByRole("button", { name: "Send Reset Link" })).toBeDisabled();
    await page.getByLabel("Email address").fill("a@b.co");
    await expect(page.getByRole("button", { name: "Send Reset Link" })).toBeEnabled();
  });
});

test.describe("create account and email verification", () => {
  test("password rules guide the form and an invalid form is blocked", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Create an account" }).click();
    const create = page.getByRole("button", { name: "Create Account" });
    await expect(create).toBeDisabled();
    await page.getByLabel("Email address").fill("someone@example.test");
    await page.getByLabel("Password", { exact: true }).fill("abc");
    await expect(page.getByText("8+ characters")).toBeVisible();
    await expect(page.getByText("Uppercase letter")).toBeVisible();
    await expect(page.getByText("Number")).toBeVisible();
    await expect(create).toBeDisabled();
    await page.getByLabel("Password", { exact: true }).fill("Passw0rd!x");
    await expect(create).toBeEnabled();
  });

  test("a new account is held on the verify page until its email link is used", async ({ page }) => {
    const email = emu.uniqueEmail("signup");
    const password = "Passw0rd!x";
    await page.goto("/");
    await page.getByRole("button", { name: "Create an account" }).click();
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Create Account" }).click();
    const verifyHeading = page.getByRole("heading", { name: "Check your inbox" });
    await expect(verifyHeading).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();

    // Pressing the button before verifying re-checks the live status and stays put with a message.
    await page.getByRole("button", { name: "I verified my email" }).click();
    await expect(page.getByRole("alert")).toContainText("isn't verified yet");
    await expect(verifyHeading).toBeVisible();
    await expect(mainNav(page)).toHaveCount(0);

    // The API refuses the same account too, not just the screen.
    const token = await emu.idTokenFor(email, password);
    const refused = await page.request.get("/api/workspaces", { headers: { Authorization: `Bearer ${token}` } });
    expect(refused.status()).toBe(403);
    expect(await refused.json()).toMatchObject({ detail: "email_not_verified" });

    // A reload does not let them in.
    await page.reload();
    await expect(verifyHeading).toBeVisible();
    await expect(mainNav(page)).toHaveCount(0);

    // Resend sends another email.
    await page.getByRole("button", { name: "Resend verification email" }).click();
    await expect(page.getByText("Email resent!")).toBeVisible();
    await expect.poll(async () => (await emu.oobCodes(email)).filter(o => o.requestType === "VERIFY_EMAIL").length).toBeGreaterThanOrEqual(2);

    // Using the link, then the button, lets them in and the API accepts them.
    const link = await emu.latestOob(email, "VERIFY_EMAIL");
    await emu.followLink(link!.oobLink);
    await page.getByRole("button", { name: "I verified my email" }).click();
    await expect(mainNav(page)).toBeVisible();
    await expect(dashboardHeading(page)).toBeVisible();
    await expect(page.getByText("Tickers Tracked")).toBeVisible();
  });

  test("Back to sign in from the verify page signs the unverified user out", async ({ page }) => {
    const email = emu.uniqueEmail("signup-back");
    await page.goto("/");
    await page.getByRole("button", { name: "Create an account" }).click();
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Password", { exact: true }).fill("Passw0rd!x");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByRole("heading", { name: "Check your inbox" })).toBeVisible();
    await page.getByRole("button", { name: "Back to sign in" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });
});
