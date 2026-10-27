import fs from "node:fs";
import path from "node:path";
import { test, expect, TARGET } from "../support/fixtures";
import * as emu from "../support/emulator";

// Firebase and Postgres themselves: not clicks, but the services every click depends on.
// Staging target: the real Firebase project and the deployed API/database. Emulator target: the local stack.

const apiKey = (() => {
  const src = fs.readFileSync(path.resolve(__dirname, "../../context/figma_prototype/src/app/firebase.ts"), "utf8");
  return /apiKey:\s*"([^"]+)"/.exec(src)![1];   // the web key is public by design (it ships in the browser bundle)
})();
const idtBase = TARGET === "emulator" ? `http://${process.env.FIREBASE_AUTH_EMULATOR_HOST ?? "127.0.0.1:9099"}/identitytoolkit.googleapis.com` : "https://identitytoolkit.googleapis.com";

test.describe("Firebase", () => {
  test("the sign-in service answers and rejects an unknown login the right way", { tag: "@staging" }, async ({ request }) => {
    const r = await request.post(`${idtBase}/v1/accounts:signInWithPassword?key=${apiKey}`, {
      data: { email: "nobody-health-probe@example.invalid", password: "x", returnSecureToken: true },
    });
    expect(r.status()).toBe(400);
    const message = (await r.json()).error.message as string;
    expect(message).toMatch(TARGET === "staging" ? /^INVALID_LOGIN_CREDENTIALS$/ : /INVALID_LOGIN_CREDENTIALS|EMAIL_NOT_FOUND/);
  });

  test("the token service answers", { tag: "@staging" }, async ({ request }) => {
    test.skip(TARGET === "emulator", "real Firebase only");
    const r = await request.post(`https://securetoken.googleapis.com/v1/token?key=${apiKey}`, { form: { grant_type: "refresh_token", refresh_token: "x" } });
    expect(r.status()).toBe(400);
    expect((await r.json()).error.message).toBe("INVALID_REFRESH_TOKEN");
  });

  test("Google's token-verification keys are reachable (the API needs them to check every sign-in)", { tag: "@staging" }, async ({ request }) => {
    test.skip(TARGET === "emulator", "real Firebase only");
    const r = await request.get("https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com");
    expect(r.status()).toBe(200);
    expect(Object.keys(await r.json()).length).toBeGreaterThan(0);
  });

  test("the project allows its own hosted pages for verification and reset links", { tag: "@staging" }, async ({ request }) => {
    test.skip(TARGET === "emulator", "real Firebase only");
    const r = await request.get(`https://identitytoolkit.googleapis.com/v1/projects?key=${apiKey}`);
    expect(r.status()).toBe(200);
    expect((await r.json()).authorizedDomains).toContain("ftd-2026.firebaseapp.com");
  });

  test("the API refuses a request with no token or a forged one", { tag: "@staging" }, async ({ request }) => {
    expect((await request.get("/api/workspaces")).status()).toBe(401);
    expect((await request.get("/api/workspaces", { headers: { Authorization: "Bearer abc.def.ghi" } })).status()).toBe(401);
    expect((await request.get("/api/alerts", { headers: { Authorization: "Bearer " } })).status()).toBe(401);
  });

  test("a real sign-in token is accepted and the account has its permissions", { tag: "@staging" }, async ({ request }) => {
    let token: string;
    if (TARGET === "staging") {
      const r = await request.post(`${idtBase}/v1/accounts:signInWithPassword?key=${apiKey}`, {
        data: { email: process.env.E2E_EMAIL, password: process.env.E2E_PASSWORD, returnSecureToken: true },
      });
      expect(r.status(), "the dedicated staging test account signs in").toBe(200);
      token = (await r.json()).idToken;
    } else {
      const a = await emu.verifiedAccount("health");
      token = await emu.idTokenFor(a.email, a.password);
    }
    const me = await request.get("/api/users/me/permissions", { headers: { Authorization: `Bearer ${token}` } });
    expect(me.status()).toBe(200);
    expect((await me.json()).permissions.length).toBeGreaterThanOrEqual(9);
  });
});

test.describe("Postgres, as the API sees it", () => {
  test("health endpoint is ok and no SEC data is being read from the wrong store", { tag: "@staging" }, async ({ request }) => {
    const r = await request.get("/api/health");
    expect(r.status()).toBe(200);
    expect(await r.json()).toMatchObject({ status: "ok", db_access_detected: false });
  });

  test("dashboard counts are real numbers from the database", { tag: "@staging" }, async ({ request }) => {
    const s = await (await request.get("/api/dashboard/stats")).json();
    expect(s.tickers_count).toBeGreaterThanOrEqual(TARGET === "staging" ? 400 : 3);
    for (const k of ["articles_count", "news_articles_count", "sec_filings_count", "vectorized_sec_count"]) expect(s[k], k).toBeGreaterThanOrEqual(0);
    expect(s.articles_count).toBe(s.news_articles_count + s.sec_filings_count);
    expect(s.news_articles_count).toBeGreaterThan(0);
  });

  test("tracked tickers: names, prices and recent quotes", { tag: "@staging" }, async ({ request }) => {
    const rows: any[] = await (await request.get("/api/tickers/tracked?limit=500")).json();
    expect(rows.length).toBeGreaterThanOrEqual(TARGET === "staging" ? 400 : 3);
    expect(rows.filter(r => !r.name).length).toBe(0);
    const priced = rows.filter(r => typeof r.current_price === "number" && r.current_price > 0);
    expect(priced.length / rows.length).toBeGreaterThanOrEqual(0.95);
    const cutoff = Date.now() - 10 * 864e5;
    const fresh = rows.filter(r => r.price_as_of && Date.parse(r.price_as_of) > cutoff);
    expect(fresh.length / rows.length, "share of tickers with a quote from the last 10 days").toBeGreaterThanOrEqual(TARGET === "staging" ? 0.9 : 0.5);
  });

  test.fixme("a burst of simultaneous requests all succeed (the API's database pool holds only 5 connections)", async ({ request }) => {
    // Known defect, reproduced on staging: app/db.py raises "connection pool exhausted" instead of waiting.
    const codes = (await Promise.all(Array.from({ length: 40 }, () => request.get("/api/tickers/tracked?limit=3")))).map(r => r.status());
    expect(codes.filter(c => c !== 200)).toEqual([]);
  });
});
