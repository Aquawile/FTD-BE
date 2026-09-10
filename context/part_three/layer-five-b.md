# LAYER FIVE-B — MOCK DATA CLEANUP & UI ARTIFACT REMOVAL (PHASE B)

**Agent implementation specification.** This document is the Phase B continuation of Major Layer Five after completion of Major Layer Five Phase A. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Four is complete. Layer Five Phase A established the infrastructure. Layer Five Phase B executes the actual mock data removal and UI cleanup while preserving all source code needed to reproduce or reference the mock behavior. The distinction between "rendered elements shown to the user" and "source code that defines mock data" is critical and must be enforced at all times.

The agent must not delete any mock data constants, helper functions, type definitions, or reproduction source code. Only the code that actively renders or displays mock data to the user must be removed or replaced with conditional rendering that falls back to live data or empty states.

The agent must first inspect the `App.tsx` file and any related component files to identify every mock data constant, every rendered mock element, and every unused UI artifact (unused components, unused imports, dead code paths). The investigation must be comprehensive: no mock element or dead artifact may be overlooked.

The agent must not invent missing architecture. If a mock element is conditionally rendered and already falls back to live data, it must not be removed — only the unconditional mock rendering path must be removed.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Build verification must use the existing Vite build pipeline.

Error handling is part of implementation, not an afterthought. Removing mock elements must not leave broken conditional rendering, undefined references, or runtime errors. Every removal must be verified by building and testing the application.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete source code that reproduces mock behavior, or leave the application in a broken state after cleanup.

The developer is the authority for what constitutes "safe to remove" vs. "must preserve." The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 5.1-B — REMOVE RENDERED MOCK ELEMENTS WHILE PRESERVING SOURCE CODE (PHASE B)**

### **Instruction**

The objective of Sublayer 5.1-B is to complete the removal of all remaining rendered mock data elements from the user-facing UI while preserving the source code constants and helper functions that define them. This phase focuses on the remaining pages not addressed in Phase A: SearchPage, TickerDashboard, TickerTimelinePage, TickerFilingsPage, TickerComparisonPage, CommunityPage, ChatPage, AdminMappingPage, and any other pages still rendering mock data.

The agent must first inspect the `App.tsx` file and any related component files to identify every mock data constant and every location where it is rendered. The investigation must be narrow and purposeful: identify the exact tables, columns, and relationships; identify existing API patterns; and document the mock data being replaced.

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before creating a new API endpoint, inspect whether an existing endpoint already serves the required data. Before creating a new database query, inspect whether an existing query or model method satisfies the requirement.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Backend work must use the project's existing database driver, ORM, and API patterns.

Error handling is part of implementation, not an afterthought. Database connection failures, empty result sets, and API errors must be handled gracefully in both the backend and frontend. The dashboard must not crash or display misleading data when the backend is unavailable.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete existing application behavior to simplify implementation, or create mock database behavior in place of required integration verification.

The developer is the authority for data presentation decisions, API contract approval, and dashboard layout. The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 5.1-B.1 — SEARCH PAGE MOCK REMOVAL**

### **Instruction**

The objective of this sublayer is to replace the hardcoded `TICKERS` mock array and the SearchPage search results with live data from the backend. The agent must first inspect the Postgres schema for a tickers or tracked-symbols table, and inspect the existing `SearchPage` and `TickerDashboard` components to understand how ticker data is currently consumed.

The "Top Hype/Evidence Divergence" section on the DashboardPage displays the first 5 items from `TICKERS.slice(0, 5)` with mock hype/evidence scores, prices, and sparkline data. The hype score and sparkline data must remain mocked for this phase — only the ticker symbol, company name, and price should be replaced with live data. The evidence score may remain mocked or be replaced if a real value exists in the database.

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

## **SUBLAYER 5.1-B.2 — TICKER DASHBOARD MOCK REMOVAL**

### **Instruction**

The objective of this sublayer is to replace the hardcoded `TICKERS` mock array and the "Top Hype/Evidence Divergence" section on the `DashboardPage` with live data from the backend. The agent must first inspect the Postgres schema for a tickers or tracked-symbols table, and inspect the existing `TickerDashboard` and `SearchPage` components to understand how ticker data is currently consumed.

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

## **SUBLAYER 5.1-B.3 — TICKER DETAIL PAGES MOCK REMOVAL**

### **Instruction**

The objective of this sublayer is to replace mock data on the TickerDashboard, TickerTimelinePage, TickerFilingsPage, TickerComparisonPage, and TickerCommunityPage with live data from the backend. The agent must first inspect the Postgres schema for the relevant tables, and inspect the existing components to understand how data is currently consumed.

### **Implementation**

1. **TickerDashboard (overview/news/evidence/community/filings/timeline tabs):**
   - Replace `NEWS_ARTICLES` with live data from `/api/tickers/{ticker}/news`
   - Replace `TIMELINE_EVENTS` with live data from `/api/tickers/{ticker}/timeline`
   - Replace `TICKERS` fallback with live data from `/api/tickers/{ticker}/filings`
   - Keep hype score and sparkline data mocked
   - Replace evidence breakdown with live data from `/api/tickers/{ticker}/evidence`

2. **TickerTimelinePage:**
   - Replace `TIMELINE_EVENTS` with live data from `/api/tickers/{ticker}/timeline`

2. **TickerFilingsPage:**
   - Replace mock filings array with live data from `/api/tickers/{ticker}/filings`

3. **TickerComparisonPage:**
   - Replace mock tickers with live data from `/api/tickers/tracked`

4. **CommunityPage:**
   - Replace `CHAT_HISTORY` with empty state (defer to AI layer)

### **Error handling**

If the user has no tracked tickers, display an empty state message rather than a broken UI. If the API returns an unexpected shape, handle missing fields gracefully. If the database query fails, display an error state without crashing the dashboard.

### **Developer responsibilities**

The developer must approve the ticker data source and confirm whether tracked tickers are user-specific or global. The developer must verify the dashboard layout remains correct with live ticker data.

### **IDE agent responsibilities**

The IDE agent may create backend endpoints, update frontend fetching logic, and add loading/error states. It may not modify the ticker database schema, delete the `TICKERS` constant, or implement the hype score.

### **Hard stop**

Under no circumstances may the agent modify the Postgres tickers table schema, delete the `TICKERS` mock constant, implement the hype score, or continue into workspace integration before the ticker data is verified working. If the ticker data source is ambiguous, stop and report.

## **SUBLAYER 5.1-B.4 — WORKSPACES PAGE MOCK REMOVAL**

### **Instruction**

The objective of this sublayer is to replace the hardcoded `WORKSPACES` mock array and the "My Workspaces" section on the `DashboardPage` with live data from the backend. The agent must first inspect the Postgres schema for a workspaces table and the `WorkspacesPage` component to understand how workspace data is currently consumed.

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

4. **Preserve mock source code:**
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

## **SUBLAYER 5.1-B.5 — ALERTS PAGE MOCK REMOVAL**

### **Instruction**

The objective of this sublayer is to replace the hardcoded `ALERTS_DATA` mock array and the "Recent Alerts" panel on the `DashboardPage` with live data from the backend. The agent must first inspect the Postgres schema for an alerts table and the `AlertsPage` component to understand how alert data is currently consumed.

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

4. **Preserve mock source code:**
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

## **SUBLAYER 5.1-B.6 — CHAT PAGE AND ADMIN MOCK REMOVAL**

### **Instruction**

The objective of this sublayer is to address remaining mock data on the ChatPage and AdminMappingPage. Chat history (`CHAT_HISTORY`) should be replaced with an empty state (AI integration deferred). Admin mapping queue (`MAPPING_QUEUE`) should remain as-is since admin pages are out of scope for Layer Five.

### **Implementation**

1. **ChatPage:**
   - Replace `CHAT_HISTORY` rendering with empty state: "No chat history yet. AI assistant coming soon."
   - Preserve `CHAT_HISTORY` constant as fallback.

2. **AdminMappingPage:**
   - Leave `MAPPING_QUEUE` as-is (admin pages out of scope)

### **Error handling**

If the user has no chat history, display empty state with helpful message.

### **Developer responsibilities**

The developer must approve the chat data source and confirm the user-chat relationship.

### **IDE agent responsibilities**

The IDE agent may create backend endpoints, update frontend fetching logic, and add loading/error states. It may not modify the chat database schema, delete the `CHAT_HISTORY` constant, or implement chat backend logic.

### **Hard stop**

Under no circumstances may the agent modify the Postgres chat history table schema, delete the `CHAT_HISTORY` mock constant, implement chat backend logic, or continue into mock data cleanup before chat data is verified working. If the chat data source is ambiguous, stop and report.

## **SUBLAYER 5.2-B — REMOVE UNUSED SHADCN/UI COMPONENTS AND DEAD CODE**

### **Instruction**

The objective of Sublayer 5.2-B is to remove unused shadcn/ui component files and dead code paths from the frontend codebase after the mock data removal in Phase B. The agent must first inspect the `src/app/components/ui/` directory and the `src/app/components/figma/` directory to identify all unused files.

### **Implementation**

1. **Audit shadcn/ui components:**
   - List all files in `src/app/components/ui/`.
   - For each file, search the codebase for imports of that component.
   - Delete files that have zero imports.
   - Update `package.json` if any dependencies become unused after component removal (only if the agent has approval to modify package.json).

2. **Remove unused figma components:**
   - Delete `src/app/components/figma/ImageWithFallback.tsx` if it has zero imports.
   - Search for any other files in `src/app/components/figma/` that are unused.

3. **Clean up App.tsx imports:**
   - Remove any import statements for components that no longer exist.
   - Remove any unused local variable declarations or helper functions that are not referenced in the active rendering path.
   - Do not remove mock data constants (handled in Sublayer 5.1).

4. **Verify build:**
   - Run `npm run build` to verify the application compiles and runs without errors.
   - Verify the Cloudflare Tunnel serves the updated build correctly.

### **Error handling**

If deleting a component file causes a build error due to an unexpected import, restore the file and report the hidden dependency. If removing an import statement causes a runtime error, restore the import and report. If the build succeeds but the application crashes in the browser, inspect the console for missing component errors.

### **Developer responsibilities**

The developer must approve the removal of each component file and confirm that no hidden dependencies exist. The developer must verify the application functions correctly after cleanup.

### **IDE agent responsibilities**

The IDE agent may delete unused component files, remove unused imports, and clean up dead code paths. It may not modify the project's `package.json` dependencies without explicit approval, remove files that are dynamically imported or referenced in configuration, or alter the build configuration.

### **Hard stop**

Under no circumstances may the agent delete files that are dynamically imported, referenced in configuration files, or used by build tooling. The agent must verify zero imports before deleting any file. If a file appears unused but is referenced in an unexpected way (e.g., via a string-based import, a plugin system, or a test file), stop and report. If the build fails after cleanup, stop and report the error rather than silently restoring files.

## **SUBLAYER 5.3-B — CLEAN UP PLACEHOLDER DATA REMNANTS AND UNUSED STATE**

### **Instruction**

The objective of Sublayer 5.3-B is to remove any remaining placeholder data remnants and unused state variables from the application after the mock element removal in Sublayer 5.1-B. The agent must first inspect `App.tsx` for any remaining placeholder text in input fields, unused `useState` declarations, unused `useEffect` hooks, and any other dead state that serves no purpose in the live application.

The cleanup must be surgical: only state and placeholders that are genuinely unused must be removed. State that is used for conditional rendering, form handling, or UI toggles must be preserved even if its current value is a placeholder.

### **Implementation**

1. **Audit placeholder text:**
   - Search for any remaining placeholder text that could be mistaken for pre-filled values.
   - Ensure all input fields have appropriate `placeholder` attributes that are visually distinct from actual values.
   - Remove any placeholder text stored in state variables.

2. **Audit unused state:**
   - For each `useState` declaration, verify it is referenced in the component's render output or event handlers.
   - Remove state variables that are declared but never read.
   - Remove `useEffect` hooks that have no dependencies and perform no side effects.

3. **Audit unused event handlers:**
   - Search for `onClick`, `onChange`, `onSubmit`, and other event handlers that are defined but never attached to any element.
   - Remove unused handler functions.

4. **Audit conditional rendering paths:**
   - Search for ternary expressions or conditional blocks that always evaluate to the same branch (e.g., `condition ? <A /> : <A />`).
   - Simplify or remove dead conditional paths.

5. **Final verification:**
   - Run the application and verify all interactive elements function correctly.
   - Verify no React warnings appear in the browser console.
   - Verify the Cloudflare Tunnel serves the cleaned application correctly.

### **Error handling**

If removing a state variable causes a runtime error because it was referenced in an unexpected location (e.g., a deeply nested component, a dynamic prop), stop and report. If removing a placeholder text causes a visual regression, restore it and report.

### **Developer responsibilities**

The developer must approve the removal of any state or placeholder text. The developer must verify the application's visual appearance and interactive behavior after cleanup.

### **IDE agent responsibilities**

The IDE agent may remove unused state, unused effect hooks, unused event handlers, and dead conditional paths. It may not remove state that is used for form handling, conditional rendering, or UI toggles. It may not alter the visual design or layout of any component.

### **Hard stop**

Under no circumstances may the agent remove state that is referenced by any rendering logic, delete mock data constants, alter component props or layout, or continue into documentation before all placeholder remnants and unused state are addressed. If a state variable's usage is ambiguous, stop and report.

## **FINAL LAYER FIVE-B DEFINITION OF DONE**

Layer Five Phase B is complete only when:

1. All rendered mock data elements have been replaced with live data, empty states, or loading placeholders across ALL pages (SearchPage, TickerDashboard, TickerTimelinePage, TickerFilingsPage, TickerComparisonPage, CommunityPage, WorkspacesPage, WorkspaceDetailPage, AlertsPage, ChatPage, AdminMappingPage, DashboardPage)
2. The mock data source code for `TICKERS`, `NEWS_ARTICLES`, `TIMELINE_EVENTS`, `WORKSPACES`, `ALERTS_DATA`, `CHAT_HISTORY`, `MAPPING_QUEUE` is preserved in a clearly marked section
2. The hype score and sparkline data remain mocked (as explicitly allowed)
3. The dashboard "Top Movers" section displays live ticker data (symbol, name, price)
4. The "My Workspaces" section displays live workspace data
5. The "Recent Alerts" panel displays live alert data
6. SearchPage uses live data from `/api/tickers/search`
4. TickerDashboard tabs use live data from their respective endpoints
5. WorkspacesPage and WorkspaceDetailPage display live workspace data
6. AlertsPage displays live alert data
6. The mock data source code for `TICKERS`, `WORKSPACES`, `ALERTS_DATA`, `NEWS_ARTICLES`, `TIMELINE_EVENTS`, `CHAT_HISTORY`, `MAPPING_QUEUE` is preserved as fallback
7. The hype score and sparkline data remain mocked
6. The dashboard handles loading, error, and empty states gracefully for all three data types
7. All unused shadcn/ui component files and figma components have been removed
8. All unused imports, state variables, and dead code paths have been cleaned up
9. The application builds without errors
10. The Cloudflare Tunnel serves the cleaned application without runtime errors or React warnings

The completion of Layer Five Phase B does not authorize work on Layer Six. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.

(End of file - total 233 lines)