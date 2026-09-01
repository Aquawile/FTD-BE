# LAYER FOUR — DASHBOARD REAL DATA INTEGRATION: TICKERS, WORKSPACES & ALERTS

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Four after completion of Major Layer Three. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Three is complete. Layer Four is a new architectural phase. The purpose of this phase is to replace the remaining mock data elements on the dashboard — specifically the top movers ticker rows, the "My Workspaces" section, and the "Recent Alerts" panel — with live data from the PostgreSQL database via the existing FastAPI backend. The hype score and stock price chart remain out of scope and must not be touched.

The agent must not modify any Postgres tables, schemas, or data. All data access must go through existing or newly created FastAPI routes. The agent must not call external data providers (GNews, SEC, Finnhub) directly from React. All provider access is backend-only and already wired in the FastAPI service.

The agent must first inspect the existing Postgres schema for tickers, workspaces, and alerts tables, the current FastAPI routes, and the `DashboardPage`, `TickerDashboard`, `WorkspacesPage`, and `AlertsPage` components to determine what data is available and what gaps exist. The investigation must be narrow and purposeful: identify the exact tables, columns, and relationships; identify existing API patterns; and document the mock data being replaced.

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before creating a new API endpoint, inspect whether an existing endpoint already serves the required data. Before creating a new database query, inspect whether an existing query or model method satisfies the requirement.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Backend work must use the project's existing database driver, ORM, and API patterns.

Error handling is part of implementation, not an afterthought. Database connection failures, empty result sets, and API errors must be handled gracefully in both the backend and frontend. The dashboard must not crash or display misleading data when the backend is unavailable.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete existing application behavior to simplify implementation, or create mock database behavior in place of required integration verification.

The developer is the authority for data presentation decisions, API contract approval, and dashboard layout. The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 4.1 — REPLACE MOCK TICKER DATA WITH LIVE TRACKED TICKERS**

### **Instruction**

The objective of Sublayer 4.1 is to replace the hardcoded `TICKERS` mock array and the "Top Hype/Evidence Divergence" section on the `DashboardPage` with live data from the backend. The agent must first inspect the Postgres schema for a tickers or tracked-symbols table, and inspect the existing `TickerDashboard` and `SearchPage` components to understand how ticker data is currently consumed.

The "Top Hype/Evidence Divergence" section displays the first 5 items from `TICKERS.slice(0, 5)` with mock hype/evidence scores, prices, and sparkline data. The hype score and sparkline data must remain mocked for this phase — only the ticker symbol, company name, and price should be replaced with live data. The evidence score may remain mocked or be replaced if a real value exists in the database.

### **Tools to use and why**

Use IDE file search to locate the ticker model, existing ticker-related API routes, and the `TICKERS` constant. Use the terminal to query the staging database for ticker records and to test new API endpoints. Use the existing `SearchPage` fetch pattern as a reference for how the frontend currently retrieves ticker data.

### **Implementation**

1. **Inspect the ticker data source:**
   - Query Postgres for the tickers table structure and current records.
   - Identify which columns contain symbol, company name, price, and evidence score.
   - Determine how tickers are associated with users (personal watchlist vs. global tracked tickers).

2. **Create or extend ticker API endpoint:**
   - If an existing endpoint serves tracked tickers, extend it.
   - If not, create `GET /api/tickers/tracked` that returns the user's tracked tickers with symbol, name, price, and evidence score.
   - The endpoint must return an empty array when the user has no tracked tickers, not an error.

3. **Update DashboardPage:**
   - Replace `TICKERS.slice(0, 5)` with a fetch from `/api/tickers/tracked`.
   - Keep the hype score rendering as mock data for now.
   - Replace the price display with the live price from the API.
   - Keep the sparkline data as randomized mock data.
   - Add loading and error states for the ticker fetch.

4. **Preserve mock source code:**
   - Do not delete the `TICKERS` constant.
   - Mark it as fallback/development mock data.

### **Error handling**

If the user has no tracked tickers, display an empty state message rather than a broken UI. If the API returns an unexpected shape, handle missing fields gracefully. If the database query fails, display an error state without crashing the dashboard.

### **Developer responsibilities**

The developer must approve the ticker data source and confirm whether tracked tickers are user-specific or global. The developer must verify the dashboard layout remains correct with live ticker data.

### **IDE agent responsibilities**

The IDE agent may create backend endpoints, update frontend fetching logic, and add loading/error states. It may not modify the ticker database schema, delete the `TICKERS` constant, or implement the hype score.

### **Hard stop**

Under no circumstances may the agent modify the Postgres tickers table schema, delete the `TICKERS` mock constant, implement the hype score, or continue into workspace integration before the ticker data is verified working. If the ticker data source is ambiguous, stop and report.

## **SUBLAYER 4.2 — REPLACE MOCK WORKSPACES WITH LIVE WORKSPACE DATA**

### **Instruction**

The objective of Sublayer 4.2 is to replace the hardcoded `WORKSPACES` mock array and the "My Workspaces" section on the `DashboardPage` with live data from the backend. The agent must first inspect the Postgres schema for a workspaces table and the `WorkspacesPage` component to understand how workspace data is currently consumed.

The "My Workspaces" section on the dashboard displays the first 3 items from `WORKSPACES` as cards. These must be replaced with the user's actual workspaces fetched from the backend. The workspace detail view (`WorkspaceDetailPage`) should also be updated to use live data if it currently relies on mock data.

### **Tools to use and why**

Use IDE file search to locate the workspace model, existing workspace-related API routes, and the `WORKSPACES` constant. Use the terminal to query the staging database for workspace records and to test new API endpoints. Use the existing `WorkspacesPage` as a reference for workspace data structure.

### **Implementation**

1. **Inspect the workspace data source:**
   - Query Postgres for the workspaces table structure and current records.
   - Identify which columns contain workspace name, description, tickers, and ownership.
   - Determine how workspaces are associated with users.

2. **Create or extend workspace API endpoint:**
   - If an existing endpoint serves user workspaces, extend it.
   - If not, create `GET /api/workspaces` that returns the current user's workspaces.
   - The endpoint must return an empty array when the user has no workspaces.

3. **Update DashboardPage:**
   - Replace `WORKSPACES.slice(0, 3)` with a fetch from `/api/workspaces`.
   - Display the first 3 workspaces as cards, matching the existing layout.
   - Add a "View all" link that navigates to the `workspaces` page if there are more than 3.
   - Add loading and error states.

4. **Update WorkspacesPage if needed:**
   - If `WorkspacesPage` still uses mock data, replace it with live API calls.
   - Ensure the workspace creation modal is functional (even if backend calls are mocked for now).

5. **Preserve mock source code:**
   - Do not delete the `WORKSPACES` constant.
   - Mark it as fallback/development mock data.

### **Error handling**

If the user has no workspaces, display an empty state with a prompt to create one. If the API fails, show an error state without crashing. If workspace data is missing expected fields, handle gracefully with fallback text.

### **Developer responsibilities**

The developer must approve the workspace data source and confirm the user-workspace relationship. The developer must verify the workspace card layout remains correct.

### **IDE agent responsibilities**

The IDE agent may create backend endpoints, update frontend fetching logic, and add loading/error states. It may not modify the workspace database schema, delete the `WORKSPACES` constant, or implement workspace creation backend logic.

### **Hard stop**

Under no circumstances may the agent modify the Postgres workspaces table schema, delete the `WORKSPACES` mock constant, implement workspace CRUD backend logic, or continue into alert integration before workspace data is verified working. If the workspace data source is ambiguous, stop and report.

## **SUBLAYER 4.3 — REPLACE MOCK ALERTS WITH LIVE ALERT DATA**

### **Instruction**

The objective of Sublayer 4.3 is to replace the hardcoded `ALERTS_DATA` mock array and the "Recent Alerts" panel on the `DashboardPage` with live data from the backend. The agent must first inspect the Postgres schema for an alerts table and the `AlertsPage` component to understand how alert data is currently consumed.

The "Recent Alerts" section on the dashboard displays the first 3 items from `ALERTS_DATA`. These must be replaced with the user's actual recent alerts fetched from the backend. The alerts must include at minimum: alert title/message, timestamp, and read/unread status. The unread dot indicator must reflect the real unread status.

### **Tools to use and why**

Use IDE file search to locate the alert model, existing alert-related API routes, and the `ALERTS_DATA` constant. Use the terminal to query the staging database for alert records and to test new API endpoints. Use the existing `AlertsPage` as a reference for alert data structure and display patterns.

### **Implementation**

1. **Inspect the alert data source:**
   - Query Postgres for the alerts table structure and current records.
   - Identify which columns contain alert message, timestamp, read status, and user association.
   - Determine the alert creation mechanism (triggered by backend events vs. user-created).

2. **Create or extend alert API endpoint:**
   - If an existing endpoint serves user alerts, extend it.
   - If not, create `GET /api/alerts` that returns the current user's recent alerts.
   - The endpoint should support a `?limit=` parameter for pagination.
   - The endpoint must return an empty array when the user has no alerts.

3. **Update DashboardPage:**
   - Replace `ALERTS_DATA.slice(0, 3)` with a fetch from `/api/alerts?limit=3`.
   - Display alerts with the existing card layout, including the unread dot indicator.
   - Add a "View all" link that navigates to the `alerts` page if there are more than 3.
   - Add loading and error states.

4. **Update AlertsPage if needed:**
   - If `AlertsPage` still uses mock data, replace it with live API calls.
   - Ensure the filter buttons (all/unread/high/medium/low) work with live data.

5. **Preserve mock source code:**
   - Do not delete the `ALERTS_DATA` constant.
   - Mark it as fallback/development mock data.

### **Error handling**

If the user has no alerts, display an empty state message. If the API fails, show an error state without crashing. If alert timestamps are missing, display a relative time fallback (e.g., "Recently") rather than breaking the layout.

### **Developer responsibilities**

The developer must approve the alert data source and confirm the user-alert relationship. The developer must verify the alert card layout remains correct with live data.

### **IDE agent responsibilities**

The IDE agent may create backend endpoints, update frontend fetching logic, and add loading/error states. It may not modify the alert database schema, delete the `ALERTS_DATA` constant, or implement alert creation backend logic.

### **Hard stop**

Under no circumstances may the agent modify the Postgres alerts table schema, delete the `ALERTS_DATA` mock constant, implement alert creation backend logic, or continue into mock data cleanup before alert data is verified working. If the alert data source is ambiguous, stop and report.

## **FINAL LAYER FOUR DEFINITION OF DONE**

Layer Four is complete only when the dashboard "Top Movers" section displays live ticker data (symbol, name, price), the "My Workspaces" section displays live workspace data, and the "Recent Alerts" panel displays live alert data — all fetched from the FastAPI backend which queries PostgreSQL. The mock data source code for `TICKERS`, `WORKSPACES`, and `ALERTS_DATA` must be preserved as fallback. The hype score and sparkline data remain mocked. The dashboard must handle loading, error, and empty states gracefully for all three data types.

The completion of Layer Four does not authorize work on Layer Five. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.

(End of file - total 218 lines)