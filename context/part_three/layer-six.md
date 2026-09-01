# LAYER SIX — DATA PROVIDER CONTEXT, CONSTRAINTS & FREE-TIER BEHAVIOR

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Six after completion of Major Layer Five. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Five is complete. Layer Six is a new architectural phase. The purpose of this phase is to document the data provider configuration, rate limits, free-tier constraints, safe data-fetching patterns, caching rules, and data staleness expectations for the application. This layer does not modify any code — it produces a reference document that guides all future data integration work.

The agent must first inspect the existing backend code to understand how GNews, SEC EDGAR, and Finnhub are currently configured and accessed. The agent must then research the current free-tier limits for each provider and document them. The agent must also inspect the existing data ingestion pipeline to understand update frequency and data flow.

The agent must not invent provider configurations, rate limits, or behavioral constraints that are not grounded in actual documentation or existing code. All documented limits must be sourced from provider documentation or observable behavior in the codebase.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, terminal, Git tooling, and existing project documentation. Provider research must use web search to find current free-tier documentation.

Error handling is part of documentation, not implementation. The reference document must clearly state what happens when rate limits are hit, when providers are unavailable, and when data becomes stale.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented research route is tightly bounded. If provider documentation is unavailable or contradictory, the agent may spend no more than five minutes investigating. If the issue is not resolved within five minutes, all documentation operations must stop and the agent must report the exact obstacle, what was inspected, what evidence was obtained, and what human decision is required.

The agent must not invent missing architecture, fabricate rate limits, or document constraints that do not exist. If a provider's free-tier limits cannot be determined, the agent must clearly state this as a gap rather than guessing.

The developer is the authority for provider selection, rate limit tolerance, and data freshness requirements. The IDE agent is responsible for research, documentation, and reporting within the approved scope.

## **SUBLAYER 6.1 — DOCUMENT PROVIDER CONFIGURATION AND FREE-TIER LIMITS**

### **Instruction**

The objective of Sublayer 6.1 is to document the exact configuration, authentication, and free-tier limits for each data provider used by the application: GNews, SEC EDGAR, and Finnhub. The agent must first inspect the backend code to find where each provider is configured, then research the current free-tier limits from official provider documentation.

For each provider, the document must include:
1. Provider name and purpose in the application.
2. Configuration location in the codebase (file path, environment variable names).
3. Authentication method (API key, OAuth, none).
4. Free-tier rate limits (requests per day/minute, any burst limits).
5. Free-tier data limits (articles per request, date range restrictions, result caps).
6. Any known behavioral constraints (caching requirements, attribution requirements, content restrictions).

### **Tools to use and why**

Use IDE file search to locate provider configuration in the backend code. Use web search to find current free-tier documentation for each provider. Use the terminal to inspect environment variables and configuration files. Use the existing data ingestion scripts to understand how providers are called.

### **Implementation**

1. **Inspect backend provider configuration:**
   - Search the `app/` directory for GNews, SEC, and Finnhub imports and configuration.
   - Document the exact file paths where each provider is accessed.
   - Document the environment variable names used for API keys.
   - Document the request patterns (endpoints, parameters, response handling).

2. **Research free-tier limits:**
   - Search the web for current GNews free-tier limits (requests per day, articles per request, etc.).
   - Search the web for current SEC EDGAR free-tier limits (rate limits, data formats, restrictions).
   - Search the web for current Finnhub free-tier limits (requests per minute/day, data types available).
   - Document the source URL and date for each limit found.

3. **Document configuration:**
   - Create a structured reference for each provider with all required fields.
   - Include code snippets showing how the provider is configured in the backend.
   - Include example request/response patterns.

### **Error handling**

If provider documentation is unavailable or contradictory, document the conflicting information and flag it for developer review. If a provider's configuration cannot be found in the codebase, document this as a gap. If a provider is not currently used but is planned, document this as a future consideration.

### **Developer responsibilities**

The developer must approve the provider list and confirm that all planned providers are documented. The developer must review the documented rate limits and confirm they align with the application's expected usage.

### **IDE agent responsibilities**

The IDE agent may inspect provider configuration, research free-tier limits, and produce the reference document. It may not modify provider configuration, change API keys, or implement new provider integrations.

### **Hard stop**

Under no circumstances may the agent fabricate rate limits, modify provider configuration, or continue into caching rules documentation before all provider limits are documented with sourced evidence. If a provider's limits cannot be determined, stop and report the gap.

## **SUBLAYER 6.2 — ESTABLISH SAFE DATA-FETCHING PATTERNS AND CACHING RULES**

### **Instruction**

The objective of Sublayer 6.2 is to document the safe data-fetching patterns and caching rules that all future frontend data integration must follow. The agent must first inspect the existing backend caching mechanisms, the existing API response patterns, and the existing frontend data-fetching code to establish baseline conventions.

The document must cover:
1. Backend caching strategy: what is cached, for how long, and how cache invalidation works.
2. Frontend caching rules: how long the React app may cache API responses, how to handle stale data, when to force a refresh.
3. Rate limit handling: how the backend and frontend must behave when a provider rate limit is hit.
4. Error response standards: the exact error format returned by the backend for provider failures, database failures, and validation failures.
5. Retry behavior: whether failed requests may be retried, with what backoff, and how many times.

### **Tools to use and why**

Use IDE file search to locate caching logic, retry logic, and error handling in the backend. Use the terminal to inspect running service behavior. Use the existing API endpoints as examples of current patterns.

### **Implementation**

1. **Inspect backend caching:**
   - Search the backend code for caching decorators, cache configuration, or in-memory caching.
   - Document what endpoints have caching and for how long.
   - Document cache invalidation triggers (time-based, event-based, manual).

2. **Inspect frontend fetching:**
   - Search the frontend code for `fetch` calls, `apiRequest` usage, and any caching libraries.
   - Document the current pattern for handling loading, error, and success states.
   - Document any existing retry or timeout logic.

3. **Document safe patterns:**
   - Define the standard API response envelope (success, error, data shape).
   - Define the standard error codes and their meanings.
   - Define the maximum acceptable cache duration for each data type.
   - Define the retry policy (max retries, backoff strategy, which errors are retryable).

4. **Document rate limit behavior:**
   - Define what the backend returns when a provider rate limit is hit (429, cached stale data, empty result, etc.).
   - Define what the frontend must do when it receives a rate-limit response (show message, retry after delay, etc.).

### **Error handling**

If no caching mechanism exists, document this as "no caching implemented" rather than inventing one. If no retry logic exists, document this as a gap. If error handling is inconsistent across endpoints, document the inconsistency.

### **Developer responsibilities**

The developer must approve the documented caching rules and confirm they align with the application's data freshness requirements. The developer must approve the retry and error-handling policies.

### **IDE agent responsibilities**

The IDE agent may inspect existing caching and error-handling code, document the patterns, and produce the reference document. It may not implement caching, modify error handling, or change API response formats.

### **Hard stop**

Under no circumstances may the agent implement caching, modify API response formats, or continue into update frequency documentation before the safe fetching patterns are fully documented. If the existing error handling is inconsistent, document the inconsistency and stop rather than imposing a new standard.

## **SUBLAYER 6.3 — DEFINE UPDATE FREQUENCY AND DATA STALENESS HANDLING**

### **Instruction**

The objective of Sublayer 6.3 is to document the expected update frequency for each data type in the application and define how data staleness must be handled by both the backend and frontend. The agent must first inspect the data ingestion pipeline to understand how often each provider's data is fetched and written to Postgres, then document the expected freshness for each dashboard element.

The document must cover:
1. Data ingestion schedule: how often does the backend fetch from GNews, SEC, and Finnhub?
2. Data freshness expectations: how current must each dashboard element be (real-time, hourly, daily)?
3. Staleness thresholds: how old is too old for each data type, and what should the UI show when data is stale?
4. Background refresh: does the frontend poll for updates, and if so, at what interval?
5. User-initiated refresh: can the user manually refresh data, and what happens when they do?

### **Tools to use and why**

Use IDE file search to locate data ingestion scripts, scheduler configuration, and cron jobs. Use the terminal to inspect running processes and logs for ingestion timing. Use the existing deployment documentation to find ingestion schedule information.

### **Implementation**

1. **Inspect data ingestion:**
   - Search the codebase for data ingestion scripts, scheduled tasks, or cron configurations.
   - Document how often each provider is polled and how often data is written to Postgres.
   - Document the trigger mechanism (scheduled, event-driven, manual).

2. **Define freshness expectations:**
   - For each dashboard element (article count, ticker prices, alerts, workspaces), define the maximum acceptable data age.
   - Document the current actual freshness based on the ingestion schedule.
   - Identify any gaps between expected and actual freshness.

3. **Document staleness handling:**
   - Define what the UI must show when data is approaching or exceeding its staleness threshold (e.g., "Updated 2 hours ago" label, warning indicator, refresh button).
   - Define whether the frontend must poll for updates or rely on page navigation for refresh.
   - Define the user-initiated refresh behavior.

4. **Document background refresh policy:**
   - Define whether and how often the frontend auto-refreshes dashboard data.
   - Define the maximum polling interval to avoid overwhelming the backend.
   - Define whether WebSocket or server-sent events are planned for real-time updates.

### **Error handling**

If the ingestion schedule cannot be determined from the codebase, document this as a gap and note that the developer must provide the schedule. If no staleness policy exists, document this as "not defined" rather than inventing one.

### **Developer responsibilities**

The developer must approve the documented freshness expectations and confirm they align with the provider free-tier limits and business requirements. The developer must define the staleness thresholds for each data type.

### **IDE agent responsibilities**

The IDE agent may inspect ingestion scripts and schedules, document the update frequency, and produce the reference document. It may not modify ingestion schedules, implement background refresh, or change data fetching behavior.

### **Hard stop**

Under no circumstances may the agent modify ingestion schedules, implement background refresh polling, or continue into the final layer summary before all update frequency and staleness policies are documented. If the ingestion schedule cannot be determined, stop and report the gap.

## **FINAL LAYER SIX DEFINITION OF DONE**

Layer Six is complete only when the application has a comprehensive reference document covering: (1) all data providers with their exact configuration, authentication, and free-tier limits sourced from official documentation; (2) safe data-fetching patterns and caching rules derived from existing backend and frontend conventions; (3) update frequency, data freshness expectations, and staleness handling policies. The document must be clear enough that any future developer or agent can integrate new data sources without guessing at rate limits, caching behavior, or freshness requirements.

The completion of Layer Six marks the end of Part Three. All subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.

(End of file - total 232 lines)