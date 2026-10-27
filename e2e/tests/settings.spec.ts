import { test, expect, signInUi, accountFor } from "../support/fixtures";
import * as emu from "../support/emulator";

const openProfile = async (page: import("@playwright/test").Page) => {
  await page.getByRole("button", { name: "Settings" }).click();
  await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible();
};
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", "base64");

test.describe("settings (profile page)", () => {
  test("shows the account email, which cannot be edited here", { tag: "@staging" }, async ({ page }) => {
    const acct = await accountFor();
    await signInUi(page, acct);
    await openProfile(page);
    await expect(page.getByText(acct.email, { exact: true }).first()).toBeVisible();
    await expect(page.getByLabel("First name")).toBeEditable();
    await expect(page.getByLabel("Last name")).toBeEditable();
    await expect(page.locator("input[type=email]")).toHaveCount(0);
  });

  test("saving a name updates the avatar and menu, and is still there after a reload", async ({ page }) => {
    await signInUi(page, await emu.verifiedAccount("profile"));
    await openProfile(page);
    await page.getByLabel("First name").fill("Ada");
    await page.getByLabel("Last name").fill("Lovelace");
    await page.getByRole("button", { name: "Save Profile" }).click();
    await expect(page.getByRole("button", { name: "Saved" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("button", { name: "Account menu" })).toHaveText("AL");
    await page.getByRole("button", { name: "Account menu" }).click();
    await expect(page.getByText("Ada Lovelace")).toBeVisible();
    await page.keyboard.press("Escape");
    await openProfile(page);
    await expect(page.getByLabel("First name")).toHaveValue("Ada");
    await expect(page.getByLabel("Last name")).toHaveValue("Lovelace");
  });

  test("a profile photo can be chosen and is kept on this device", async ({ page }) => {
    await signInUi(page, await emu.verifiedAccount("photo"));
    await openProfile(page);
    await page.getByLabel("Upload profile photo").setInputFiles({ name: "me.png", mimeType: "image/png", buffer: png });
    await expect(page.locator('img[src^="data:image"]').first()).toBeVisible();
    await page.reload();
    await openProfile(page);
    await expect(page.locator('img[src^="data:image"]').first()).toBeVisible();
  });

  test("Security: the reset link email is requested for this account", async ({ page }) => {
    const acct = await emu.verifiedAccount("security");
    await signInUi(page, acct);
    await openProfile(page);
    await page.getByRole("button", { name: "security", exact: true }).click();
    await expect(page.getByText(acct.email).first()).toBeVisible();
    await page.getByRole("button", { name: "Email me a reset link" }).click();
    await expect.poll(async () => (await emu.latestOob(acct.email, "PASSWORD_RESET")) !== undefined).toBe(true);
    await page.getByRole("button", { name: "profile", exact: true }).click();
    await expect(page.getByLabel("First name")).toBeVisible();
  });
});
