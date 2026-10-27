// Thin client for the Firebase Auth emulator: create users, read the "emails" it would have sent
// (oob codes), and act on them, so no test needs a real inbox.
const HOST = process.env.FIREBASE_AUTH_EMULATOR_HOST ?? "127.0.0.1:9099";
export const PROJECT = process.env.E2E_FIREBASE_PROJECT ?? "ftd-2026";
const base = `http://${HOST}`;
const idt = `${base}/identitytoolkit.googleapis.com/v1`;
const owner = { Authorization: "Bearer owner", "Content-Type": "application/json" };

async function call(url: string, init: RequestInit & { json?: unknown } = {}) {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init.headers ?? {}) }, body: init.json !== undefined ? JSON.stringify(init.json) : init.body });
  const text = await res.text();
  let body: any = text;
  try { body = JSON.parse(text); } catch { /* html or empty */ }
  if (!res.ok) throw new Error(`${init.method ?? "GET"} ${url} -> ${res.status} ${text.slice(0, 200)}`);
  return body;
}

export type Account = { email: string; password: string; uid: string };

let counter = 0;
export const uniqueEmail = (prefix = "user") => `e2e.${prefix}.${Date.now()}.${process.pid}.${counter++}@example.test`;

/** Create an account the way the sign-up form does. Unverified until its email link is used. */
export async function signUp(email: string, password: string): Promise<Account> {
  const r = await call(`${idt}/accounts:signUp?key=fake`, { method: "POST", json: { email, password, returnSecureToken: true } });
  return { email, password, uid: r.localId };
}

export async function setEmailVerified(uid: string, verified = true) {
  await call(`${idt}/projects/${PROJECT}/accounts:update`, { method: "POST", headers: owner, json: { localId: uid, emailVerified: verified } });
}

/** A ready-to-use verified account. */
export async function verifiedAccount(prefix = "user", password = "Passw0rd!x"): Promise<Account> {
  const a = await signUp(uniqueEmail(prefix), password);
  await setEmailVerified(a.uid, true);
  return a;
}

export async function idTokenFor(email: string, password: string): Promise<string> {
  const r = await call(`${idt}/accounts:signInWithPassword?key=fake`, { method: "POST", json: { email, password, returnSecureToken: true } });
  return r.idToken;
}

export type Oob = { email: string; requestType: string; oobCode: string; oobLink: string };

export async function oobCodes(email?: string): Promise<Oob[]> {
  const r = await call(`${base}/emulator/v1/projects/${PROJECT}/oobCodes`);
  const all: Oob[] = r.oobCodes ?? [];
  return email ? all.filter(o => o.email.toLowerCase() === email.toLowerCase()) : all;
}

export async function latestOob(email: string, requestType: "VERIFY_EMAIL" | "PASSWORD_RESET"): Promise<Oob | undefined> {
  return (await oobCodes(email)).filter(o => o.requestType === requestType).pop();
}

/** Open the link a verification email would contain. */
export async function followLink(oobLink: string) {
  await fetch(oobLink, { redirect: "manual" });
}

export async function resetPassword(oobCode: string, newPassword: string) {
  await call(`${idt}/accounts:resetPassword?key=fake`, { method: "POST", json: { oobCode, newPassword } });
}

/** A Firebase user created in the past, still unverified: how accounts from before the verification rule look. */
export async function importLegacyUser(uid: string, email: string, password: string, createdAt: Date) {
  if (await accountExists(email)) return;
  await call(`${idt}/projects/${PROJECT}/accounts:batchCreate`, {
    method: "POST", headers: owner,
    json: { users: [{ localId: uid, email, emailVerified: false, createdAt: String(createdAt.getTime()), passwordHash: `fakeHash:salt=fakeSalt:password=${password}`, salt: "fakeSalt" }] },
  });
}

export async function clearAccounts() {
  await call(`${base}/emulator/v1/projects/${PROJECT}/accounts`, { method: "DELETE" });
}

async function accountExists(email: string): Promise<boolean> {
  const r = await call(`${idt}/accounts:lookup?key=fake`, { method: "POST", headers: owner, json: { email: [email] } }).catch(() => ({}));
  return Array.isArray(r.users) && r.users.length > 0;
}
