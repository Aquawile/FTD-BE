import type { User as FirebaseUser } from "firebase/auth";

// Accounts created on or after this moment must verify their email before using the app.
// Accounts that already existed are not asked to. The API enforces the same rule (403 email_not_verified).
const VERIFICATION_REQUIRED_FROM = Date.parse("2026-10-26T21:30:00Z");

export function needsEmailVerification(user: FirebaseUser | null): boolean {
  if (!user || user.emailVerified) return false;
  const created = Date.parse(user.metadata?.creationTime ?? "");
  return Number.isFinite(created) && created >= VERIFICATION_REQUIRED_FROM;
}
