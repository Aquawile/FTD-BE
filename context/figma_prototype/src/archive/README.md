# Archived UI (2026-10-16)

UI that **displayed data not backed by any API endpoint**. It's kept here instead of
deleted, so it can be restored once a real data source exists. Nothing under `src/archive/`
is imported by the app, so Vite leaves it out of the build.

## Whole pages (`archive/pages/`)

| Page | Route id (removed from `App.tsx`) | Why archived |
|---|---|---|
| `TimelinePage` | `ticker-timeline` (sidebar "Timeline") | Mock events + hype bars from `mockData` |
| `FilingsPage` | `ticker-filings` | Hardcoded NVDA filing summaries + evidence scores |
| `CommunityPage` | `ticker-community` | Hardcoded Reddit posts + hype/evidence |
| `ComparisonPage` | `ticker-comparison` | Hardcoded hype/evidence comparison |
| `ChatPage` | `chat` (sidebar "AI Assistant") | Canned AI responses, no inference API |
| `AdminDashboard`, `AdminMappingPage`, `AdminUsersPage`, `AdminSystemPage` | `admin*` (sidebar "Admin") | Hardcoded users, uptime, mapping queue |
| `LegacyLandingPage` | (unrouted) | Mock hype/evidence marketing data |

Archived pages still import `../ui`. That now resolves to `archive/ui/`, which re-exports the
live shared UI plus the archived score components, so the pages still compile.

## Score components (`archive/ui/scores.tsx`)

`ScorePill`, `HypeEvidenceBar`, `getHypeColor`, `getEvidenceColor`. `tickers.hype_score` and
`tickers.evidence_score` are placeholder values (50.00 for every ticker), not computed scores.

## Sections cut from live pages (`archive/snippets/REMOVED_SECTIONS.md`)

Ticker page: score pills, evidence matrix tab, mock article cards, hardcoded "NASDAQ" badge,
Compare/Export buttons. Dashboard: hype/evidence line, random sparklines, AI chat card and
button. Workspace: hardcoded avg hype/evidence/alerts cards. Login: "2.4M+ / 180K+ / 94%" stats
and the admin link. Profile: fake sessions, fake API key tab, evidence preference.
Workspace settings: hype toggles. Search: hype/evidence sort options.

## Restoring

1. `git mv src/archive/pages/X.tsx src/components/pages/X.tsx`
2. Re-export it in `components/pages/index.ts` and re-add its `case` in `app/App.tsx` (and sidebar item in `components/Shell.tsx`)
3. If it uses score components, import them from `../../archive/ui/scores` or move them back to `components/ui`
