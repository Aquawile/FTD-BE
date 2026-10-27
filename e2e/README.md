# FTD browser tests (Playwright)

Real browser, real user clicks, against a real stack. No test needs a real inbox or real Firebase accounts.

## Two targets

| Target | Command | What it uses |
|---|---|---|
| `emulator` (default, CI) | `npm test` | Firebase Auth emulator (sign-up, verification and reset "emails" are read from it), a throwaway Postgres built by `tests/schema/setup_test_db.sh` + `seed/e2e_seed.sql`, the real API and the real built web app. Every test runs. |
| `staging` | `E2E_TARGET=staging E2E_BASE_URL=... E2E_EMAIL=... E2E_PASSWORD=... npm run test:staging` | A deployed site and one dedicated test account. Only tests tagged `@staging` run. They read, apart from creating and archiving one workspace. |

The staging account must be verified, must not be a real person's, and its credentials live in CI secrets, never in the repo.

## Run it locally (emulator target)

1. Postgres running locally with the test database: `PGUSER=postgres PGPASSWORD=... bash tests/schema/setup_test_db.sh && psql -d ftd_lakehouse_test -f e2e/seed/e2e_seed.sql`
2. Auth emulator: `cd e2e && npx firebase-tools emulators:start --only auth --project ftd-2026`
3. API: `FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 FIREBASE_PROJECT_ID=ftd-2026 FIREBASE_AUTH_ENABLED=true PGDATABASE=ftd_lakehouse_test PGUSER=ftd_app PGPASSWORD=... uvicorn app.main:app --port 8080`
4. Web app: `cd context/figma_prototype && VITE_FIREBASE_AUTH_EMULATOR_URL=http://127.0.0.1:9099 npx vite build && cd ../../e2e && npm run serve`
5. `cd e2e && npm ci && npx playwright install chromium && npm test`

CI does all of this in the `e2e` job of `.github/workflows/ci.yml`.

## Safety rails

- The browser fixture blocks and fails on any request to the real `identitytoolkit` / `securetoken` hosts in emulator mode, so a mis-built app can never create real accounts.
- Every test fails on uncaught page errors and `console.error` (tests that break things on purpose opt out with an `allow-errors` annotation).
- Each test makes its own account, so tests do not depend on each other or on run order.

## Known defects the suite documents

- `workspaces.spec.ts`: the 50-ticker cap shown in the UI is not enforced by the API (`test.fixme`).
