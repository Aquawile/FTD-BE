// Direct database access for seeding and for expectations in the emulator target (PG* env vars).
import pg from "pg";

let pool: pg.Pool | undefined;
const db = () => (pool ??= new pg.Pool({ max: 2 }));

export async function one<T = any>(sql: string, args: unknown[] = []): Promise<T> {
  return (await db().query(sql, args)).rows[0] as T;
}
export async function many<T = any>(sql: string, args: unknown[] = []): Promise<T[]> {
  return (await db().query(sql, args)).rows as T[];
}

export const userIdByEmail = async (email: string) =>
  (await one<{ id: number }>("SELECT id FROM users WHERE lower(email) = lower($1)", [email]))?.id;

export type SeedAlert = { ticker: string; message: string; severity?: "high" | "medium" | "low"; read?: boolean; type?: string };

export async function seedAlerts(email: string, alerts: SeedAlert[]) {
  const userId = await userIdByEmail(email);
  if (!userId) throw new Error(`no application user for ${email}: sign in first`);
  for (const a of alerts) {
    await db().query(
      "INSERT INTO alerts (user_id, ticker, type, message, severity, read) VALUES ($1, $2, $3, $4, $5, $6)",
      [userId, a.ticker, a.type ?? "price", a.message, a.severity ?? "medium", a.read ?? false],
    );
  }
}

export async function closeDb() {
  await pool?.end();
  pool = undefined;
}
