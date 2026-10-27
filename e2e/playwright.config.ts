import { defineConfig, devices } from "@playwright/test";

// E2E_TARGET=emulator (default): CI / local stack, Firebase Auth emulator, seeded Postgres. Every test runs.
// E2E_TARGET=staging: a deployed site (E2E_BASE_URL) and one dedicated test account
// (E2E_EMAIL / E2E_PASSWORD). Only tests tagged @staging run; they only read, except where noted.
export const TARGET = process.env.E2E_TARGET === "staging" ? "staging" : "emulator";

export default defineConfig({
  testDir: "./tests",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: process.env.CI ? 2 : 1,
  retries: process.env.CI ? 1 : 0,
  grep: TARGET === "staging" ? /@staging/ : undefined,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
    ["junit", { outputFile: "e2e-test-results.xml" }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    viewport: { width: 1280, height: 800 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } }],
});
