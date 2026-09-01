# LAYER THREE — DASHBOARD REAL DATA INTEGRATION: ARTICLE COUNT & CORE METRICS

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Three after completion of Major Layer Two. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Two is complete. Layer Three is a new architectural phase. The purpose of this phase is to replace the mock "Articles Analyzed" count and other primary dashboard statistics with live data from the PostgreSQL database via the existing FastAPI backend. The desired architectural direction is: React component calls FastAPI endpoint, FastAPI queries Postgres, Postgres returns count, FastAPI returns JSON, React renders real number.

The agent must not modify any Postgres tables, schemas, or data. All data access must go through existing or newly created FastAPI routes. The agent must not call external data providers (GNews, SEC, Finnhub) directly from React. All provider access is backend-only and already wired in the FastAPI service.

The agent must first inspect the existing Postgres schema, the current FastAPI routes, and the `DashboardPage` component to determine what data is already available and what gaps exist. The investigation must be narrow and purposeful: identify the articles table, the count query pattern, existing API endpoints that serve dashboard data, and the exact mock data constants being replaced.

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before creating a new API endpoint, inspect whether an existing endpoint already serves the required data. Before creating a new database query, inspect whether an existing query or model method satisfies the requirement.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Backend work must use the project's existing database driver, ORM, and API patterns.

Error handling is part of implementation, not an afterthought. Database connection failures, empty result sets, and API errors must be handled gracefully in both the backend and frontend. The dashboard must not crash or display misleading data when the backend is unavailable.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete existing application behavior to simplify implementation, or create mock database behavior in place of required integration verification.

The developer is the authority for data presentation decisions, API contract approval, and dashboard layout. The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 3.1 — AUDIT POSTGRES SCHEMA AND EXISTING API ENDPOINTS**

### **Instruction**

The objective of Sublayer 3.1 is to thoroughly inspect the existing PostgreSQL schema and the current FastAPI backend to determine what data is available for the dashboard and what API infrastructure already exists. The agent must first locate and read the database schema documentation, model definitions, and existing API routes.

The agent must identify:
1. The exact table(s) that store article records, including column names, types, and constraints.
2. Any existing count queries or aggregation functions already defined in the backend.
3. Existing FastAPI endpoints that serve dashboard-related data (even if they currently return mock data).
4. The exact mock data constants in `App.tsx` that represent the "Articles Analyzed" count and other core metrics.
5. The data update mechanism: how does data get into Postgres, how often, and what is the expected freshness?

The agent must read existing project documentation to understand the data providers (GNews, SEC, Finnhub) and their free-tier limitations. The agent must not make assumptions about data frequency or completeness.

### **Tools to use and why**

Use IDE file search to locate database models, schema files, migration files, and FastAPI route definitions. Use the terminal to inspect the running FastAPI service's available endpoints and to query the Postgres database directly for table structures and record counts. Use the existing test framework to understand data access patterns. Use Git history to find documentation about data ingestion schedules.

### **Implementation**

1. **Inspect Postgres schema:**
   - Connect to the staging PostgreSQL database using the existing credentials.
   - Run `\dt` to list all tables.
   - Run `\d+ <articles_table>` to inspect the articles table structure.
   - Query `SELECT COUNT(*) FROM <articles_table>` to get the current article count.
   - Document the exact table name, primary key, and relevant columns.

2. **Inspect FastAPI backend:**
   - Locate the FastAPI route definitions in the `app/` directory.
   - Identify any existing endpoints that serve dashboard data.
   - Identify the database query patterns used (raw SQL, ORM, etc.).
   - Document the existing API response format for dashboard endpoints.

3. **Inspect mock data:**
   - Locate the `DashboardPage` component in `App.tsx`.
   - Identify the `Articles Analyzed` stat card and its mock value (`2.4M`).
   - Identify all other stat cards with mock values: `Tickers Tracked`, `Active Alerts`, `Avg Evidence Score`.
   - Document the exact mock data source and how it is rendered.

4. **Document data flow:**
   - Read project documentation to understand the data ingestion pipeline.
   - Identify how GNews, SEC, and Finnhub data enters Postgres.
   - Document the update frequency and free-tier limitations.
   - Note any data gaps or expected staleness.

### **Error handling**

If the database schema cannot be inspected (connection failure, credentials missing), stop and report the infrastructure blocker. If the articles table does not exist or has a different structure than expected, stop and report the discrepancy. If no documentation exists about data providers, note this as a gap to be addressed in Layer Six.

### **Developer responsibilities**

The developer must approve the identified database schema and confirm that the articles table is the correct data source for the dashboard count. The developer must provide database access credentials if they are not already available in the project configuration.

### **IDE agent responsibilities**

The IDE agent may inspect the database, query table structures, document the schema, and map existing API endpoints. It may not modify the database, create new tables, or alter existing data.

### **Hard stop**

Under no circumstances may the agent modify the Postgres schema, create new database objects, delete or alter existing data, or continue into API implementation before the schema audit is complete and documented. If the data source for "Articles Analyzed" is ambiguous, stop and report.

## **SUBLAYER 3.2 — CREATE OR EXTEND FASTAPI DASHBOARD ENDPOINTS**

### **Instruction**

The objective of Sublayer 3.2 is to create or extend FastAPI endpoints that serve the real dashboard metrics to the React frontend. The agent must first determine whether existing endpoints can be extended or if new endpoints must be created. The investigation from Sublayer 3.1 provides the basis for this decision.

The new or extended endpoints must serve at minimum:
1. `GET /api/dashboard/stats` — Returns the current article count, ticker count, active alert count, and average evidence score.
2. `GET /api/dashboard/articles-count` — Returns the total articles analyzed count with optional time-window parameters.

All endpoints must query PostgreSQL using the existing database access layer. Raw SQL queries must follow the project's existing conventions. The endpoints must handle empty result sets, database connection failures, and query errors gracefully. Error responses must follow the project's existing error format and must not expose internal database details.

### **Tools to use and why**

Use IDE file search to locate the existing FastAPI route definitions and database query patterns. Use the existing ORM or SQL mechanism to construct queries. Use the existing test framework to create unit and integration tests. Use the terminal to test the new endpoints against the staging database.

### **Implementation**

1. **Create or extend dashboard endpoints:**
   - If an existing `dashboard` router exists, extend it. If not, create a new router following the project's conventions.
   - Implement `GET /api/dashboard/stats` that queries:
     - `SELECT COUNT(*) FROM articles` (or equivalent) for article count.
     - `SELECT COUNT(*) FROM tickers` (or equivalent) for ticker count.
     - `SELECT COUNT(*) FROM alerts WHERE active = true` (or equivalent) for active alerts.
     - A weighted average or mean of evidence scores from the appropriate table.
   - Implement `GET /api/dashboard/articles-count` that returns the total article count with metadata (timestamp, source breakdown if available).

2. **Handle edge cases:**
   - Return `0` for counts when tables are empty, not an error.
   - Return a structured error response when the database is unavailable.
   - Include a `last_updated` timestamp in the response so the frontend can display data freshness.

3. **Follow existing conventions:**
   - Use the same response format as existing API endpoints.
   - Use the same authentication pattern (if any) as existing endpoints.
   - Use the same error handling pattern as existing endpoints.

### **Error handling**

Database connection failures must return a 503 Service Unavailable with a generic error message. Query errors must return a 500 with a generic message. The error response must not include SQL statements, table names, or internal topology. The frontend must be able to distinguish between "no data" (empty result) and "service error" (failed query).

### **Developer responsibilities**

The developer must approve the new endpoint paths and response schemas. The developer must verify that the query logic correctly reflects the intended metrics.

### **IDE agent responsibilities**

The IDE agent may create new FastAPI endpoints, implement database queries, add response models, and write tests. It may not modify the database schema, alter existing endpoints, or change the API authentication mechanism.

### **Hard stop**

Under no circumstances may the agent modify the Postgres schema, create new database tables, delete or alter existing data, expose raw SQL or internal table names in API responses, or continue into frontend integration before the backend endpoints are tested and verified. If the existing database access layer cannot support the required queries, stop and report.

## **SUBLAYER 3.3 — WIRE DASHBOARD STATS TO LIVE API DATA**

### **Instruction**

The objective of Sublayer 3.3 is to replace the mock stat cards in the `DashboardPage` component with live data fetched from the new FastAPI endpoints. The agent must first inspect the `DashboardPage` component to identify the exact stat card rendering code, the mock data sources, and the existing `apiRequest` helper function.

The replacement must follow these rules:
1. The stat cards must fetch data from the backend on component mount and whenever the user navigates to the dashboard.
2. Loading states must be displayed while data is being fetched.
3. Error states must be displayed if the backend is unavailable, using the existing error UI patterns.
4. The data must be formatted for display (commas for large numbers, percentage formatting where appropriate).
5. The "Last 24h" subtext on the Articles Analyzed card must be derived from real data if available, or removed if the data source does not support time-windowed counts.

### **Tools to use and why**

Use IDE file search to locate the `DashboardPage` component, the stat card rendering code, and the `apiRequest` helper. Use the terminal to test the new API endpoints and verify response formats. Use Git diff to ensure only the dashboard data-fetching changes are included.

### **Implementation**

1. **Add state management for dashboard stats:**
   - Add `useState` declarations for `statsData`, `loading`, and `error`.
   - Add a `useEffect` hook that fetches from `/api/dashboard/stats` on mount.
   - Add a refresh mechanism if the existing UI supports manual refresh.

2. **Replace mock data with live data:**
   - Replace the hardcoded `2.4M` articles count with the real count from the API.
   - Replace the hardcoded `13` tickers count with the real count.
   - Replace the hardcoded `5` active alerts with the real count.
   - Replace the hardcoded `68` avg evidence score with the real calculated value.
   - Format numbers appropriately (e.g., `2,456,789` instead of `2.4M` if the real count is not in millions).

3. **Add loading and error states:**
   - Display a spinner or skeleton while `loading` is true.
   - Display an error message if `error` is true, using the existing error UI patterns.
   - Ensure the dashboard remains navigable even when data is loading or errored.

4. **Preserve mock source code:**
   - Do not delete the mock data constants.
   - Comment or clearly mark them as fallback data for development without a backend.
   - Ensure the mock data remains importable or accessible for future reference.

### **Error handling**

If the API request fails, the dashboard must not crash. The error state must be user-friendly and must not expose internal error details. If the API returns unexpected data shapes, the component must handle missing fields gracefully. If the `apiRequest` helper cannot reach the backend (wrong host, port, or path), the component must detect this and show an appropriate error.

### **Developer responsibilities**

The developer must approve the data formatting rules (e.g., when to use `2.4M` vs `2,456,789`). The developer must verify the dashboard layout remains visually consistent after the data is replaced.

### **IDE agent responsibilities**

The IDE agent may add state management, fetch logic, loading/error UI, and data formatting. It may not alter the dashboard layout, change the stat card styling, or modify the `apiRequest` helper beyond using it.

### **Hard stop**

Under no circumstances may the agent delete the mock data constants, modify the FastAPI endpoint behavior, change the dashboard visual layout, or continue into ticker/workspace/alert integration before the article count and core metrics are verified working with live data. If the backend endpoints return data that cannot be cleanly mapped to the existing UI, stop and report.

## **FINAL LAYER THREE DEFINITION OF DONE**

Layer Three is complete only when the dashboard "Articles Analyzed" stat card displays the real count from PostgreSQL via the FastAPI backend, all other core metrics display live data with proper loading and error states, the mock data source code is preserved as fallback, the backend endpoints are tested and verified, and the dashboard remains visually consistent with the existing Figma design. The data must update when the backend data changes (no stale cached values beyond what the browser naturally caches).

The completion of Layer Three does not authorize work on Layer Four. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.

(End of file - total 205 lines)