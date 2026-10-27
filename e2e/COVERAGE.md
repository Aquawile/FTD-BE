# What the browser suite covers

Each test runs in Chromium, Firefox and WebKit (Safari engine). There is no phone layout by design, so phones are not tested. Plus Firebase and database health tests, and a database integrity check before and after the run. "#" is the function number from the manual test matrix (78 user-side functions).
Not yet run: this list was written before the first run, so the first CI run will likely need selector fixes.

Tagged **[S]** = also runs against staging with the dedicated test account (10 tests, read-only apart from one workspace created and archived).

## Covered

| # | Function | Test |
|---|---|---|
| 1, 2, 4 | Show/hide password, remember-me checkbox, empty form blocked | auth › show/hide password… |
| 3 | Remember me: stays signed in on the browser; unticked: tab only | auth › remember me keeps the session… |
| 5, 16, 17 | Sign in, survive reload, sign out, sign back in | auth › sign in, survive a reload… **[S]** |
| 5 | Keyboard-only sign-in (Tab, Enter) | auth › keyboard only |
| 6 | Wrong password message | auth › wrong password… |
| 7 | Forgot / create-account / back links | auth › links between… |
| 8 | Forgot password end to end: email recorded, new password works, old fails | auth › reset link is sent… |
| 8 | Send button needs a plausible email | auth › the send button needs… |
| 9 | Create-account form rules and blocking | auth › password rules guide the form… |
| 10, 11, 12, 13, 14 | Real sign-up form, held on verify page, "I verified" re-check message, API 403, reload still held, resend, link then button gets in | auth › a new account is held… |
| 15 | Account from before the rule gets straight in | auth › an account created before… |
| 17 | Back to sign in from verify signs out | auth › Back to sign in from the verify page… |
| 18, 20 | Sidebar buttons and Settings button | navigation › each sidebar button… **[S]** |
| 19 | Collapse / expand with real clicks | navigation › collapse and expand… |
| 76 | Sidebar from the keyboard | navigation › a sidebar button works from the keyboard |
| 21 | Top search to Research | navigation › top search… **[S]** |
| 24, 25 | Account menu, Profile, Sign Out, Escape closes | navigation › account menu… |
| 22, 23 | Bell: empty, badge, list, Mark all read, Escape; click-through | navigation › bell…, › clicking an alert… |
| 75 | Refresh on an inner page stays signed in | navigation › an inner page refresh… |
| 26, 27, 28 | Stats tiles, Top Movers sorted by largest move, row opens ticker | dashboard › stats, Top Movers… **[S]** |
| 29 | View all / All alerts / Manage links | dashboard › View all, All alerts… |
| 30 | Recent Alerts and My Workspaces panels | dashboard › Recent Alerts… |
| 31 | All tracked tickers with company names | research › lists every tracked ticker… **[S]** |
| 32 | Search by symbol/name, no results, clear | research › search by symbol… |
| 33 | Sort by biggest move | research › sort by biggest daily move… |
| 34 | Row opens ticker; dead chips/Filter button gone | research › a ticker row…, › the dead sector chips… |
| 35 | Header, key financials, chart tooltip follows cursor | ticker › header, key financials… **[S]** |
| 36 | Overview / News tabs | ticker › Overview and News tabs switch |
| 37, 38 | Presets 30 days, 90 days, 1 year, All: counts match the database | ticker › date presets… **[S]** |
| 38 | Custom date range | ticker › custom date range |
| 39, 40 | Next, Prev, Oldest, Newest | ticker › pagination |
| — | Every article shows whatever its attribution label (the news fix) | ticker › every article of the ticker is shown… |
| — | Ticker with few articles lists all | ticker › a ticker with a few articles… |
| 41 | View article link target | ticker › View article links… |
| 42 | Set Alert prefilled | ticker › Set Alert opens… |
| 43, 44 | Add to Workspace: choose one; create-one shortcut | ticker › Add to Workspace… (2 tests) |
| 45 | Old-quote ticker shows its date | ticker › a ticker whose quote is old… |
| 47 | Alerts empty state | alerts › empty state **[S]** |
| 48, 49 | Add price above, price below, news, filing; persist after reload | alerts › add all four kinds… |
| 50 | Form blocks incomplete input; Cancel | alerts › the form blocks incomplete input |
| — | Ticker dropdown alphabetical | alerts › the ticker list is alphabetical |
| 51, 52 | Pause / resume, persist | alerts › pause and resume survive a reload |
| 53 | Severity and unread filters | alerts › severity and unread filters |
| 54 | Opening Alerts clears the badge; Mark all read | alerts › opening the Alerts page…, › Mark all read |
| 55 | A price alert fires after the sync step, shows in the bell, clears when opened | alerts › a price alert fires after the data sync… |
| 56, 66 | Create by button; date shown plainly; archive from the card | workspaces › by button… **[S]** |
| 56 | Create by Enter; blank name blocked | workspaces › by pressing Enter… |
| 57 | Dialog closes with X, Cancel, Escape, outside click | workspaces › the dialog closes… |
| 58, 59, 60, 61 | Open, add by company name, change shown to 2 decimals, card opens ticker, remove | workspaces › add a ticker by company name… |
| — | Add-ticker list alphabetical, searchable by name | workspaces › the add-ticker list… |
| 62, 63, 64, 67 | Rename, description, filing-alert switch, card three-dot button, persisted after reload | workspaces › rename, describe, toggle… |
| 65 | Archive: Escape cancels, confirm hides for good | workspaces › archive… |
| 69 | Profile shows account email, not editable | settings › shows the account email… **[S]** |
| 70 | Save first/last name, avatar and menu update, persists | settings › saving a name… |
| 71 | Profile photo chosen and kept | settings › a profile photo… |
| 72, 73 | Security tab, reset email requested | settings › Security… |
| 76 | Accessibility scan of every page and dialog (axe, WCAG A and AA, serious/critical; colour contrast excluded) | cross-cutting › accessibility (2 tests) |
| 78 | Stats request fails; slow ticker list; 401 from API | cross-cutting › when things go wrong (3 tests) |

Every test also fails on any uncaught page error or `console.error`, and (emulator target) on any call to the real Firebase hosts.

## Known defects, written down as skipped tests
- API: the database pool holds 5 connections and fails with a 500 instead of waiting, so a burst of simultaneous requests can fail (`cross-cutting.spec.ts`, `test.fixme`). Reproduced on staging: 1 of 40 concurrent requests returned 500.
- Ticker page: the loading skeleton `<div aria-label="Loading price">` has an aria-label without a role (axe: aria-prohibited-attr). The accessibility walk scans the loaded page.
- #68: "Max 50 tickers per workspace" is shown in the page, but the API does not enforce it (`workspaces.spec.ts`, `test.fixme`).

## Not covered by this suite (stay manual)
- Whether Firebase's real mail servers deliver the verification / reset email (sender, spam folder, link). The emulator proves the app asks for the email and handles the link; it cannot prove delivery.
- Firebase console settings: email templates, authorized domains, sign-in providers, quotas, the user list.
- Phones: the app has no phone layout (deliberate), so nothing is tested there.
- Screen-reader behaviour. The axe scan catches missing names and roles, not how it sounds.
- Browser Back / Forward (the app keeps its page in memory, so this is a design question rather than a bug to assert).
- Data-pipeline correctness against the raw files (prices, news loads): checked separately. The database integrity script (`scripts/check_database_health.py`) and nightly freshness check cover the rest.
- #46: there is no screen that shows SEC filings, so there is nothing to click. The filings endpoints are covered by the API tests.
