# LAYER TWO — CONTROLLED POSTGRESQL DATA ACCESS AND BACKEND APPLICATION INTERFACE 

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Two after completion of Major Layer One. The agent must follow these instructions literally unless the developer explicitly changes them. 

## **GLOBAL OPERATING RULES** 

Major Layer One is complete. Layer Two is a new architectural phase. The purpose of this phase is to establish and verify a controlled backend path between the existing FastAPI application and the existing PostgreSQL application database. The desired architectural direction is FastAPI API boundary, application operation, database access layer, PostgreSQL, database result, and application response. The database must remain behind the backend boundary. React must not communicate with PostgreSQL. FastAPI routes must not become repositories containing raw SQL and ad hoc connection management. The existing architecture is authoritative wherever it already provides a correct implementation. 

The agent must begin by creating or using a dedicated Layer Two working branch derived from the correct completed Layer One revision. The agent must never push directly to main under any circumstance. The agent must not rewrite or force-push shared history. The agent must preserve the successful Layer One CI/CD behavior unless a concrete Layer Two requirement makes a change unavoidable. Any such change must be isolated, explained, tested, and kept within the scope of Layer Two. 

The implementation must remain deliberately narrow. The initial concrete domain is the existing application-user data because it provides a real relational domain against which the database boundary can be proven. SEC data, GNews data, Finnhub data, ticker data, financial content, lakehouse content, RAG, vector storage, dashboard behavior, frontend integration, recommendation systems, and production optimization are not Layer Two work. The agent must not implement or prepare those systems as part of this layer. 

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required boundary. Do not refactor for aesthetics, personal preference, framework fashion, or theoretical future requirements. 

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source 

navigation, test runner, terminal, Git tooling, and existing project documentation. Database work must use the project's existing database driver, ORM, migration mechanism, configuration system, and test conventions if they exist. Do not introduce a competing ORM, migration system, HTTP framework, test framework, dependency-injection framework, statemanagement system, or database abstraction merely because another tool is familiar. 

Error handling is part of implementation, not an afterthought. Every database boundary must account for unavailable database connections, invalid input, missing records, constraint violations, transaction failures, unexpected database exceptions, and cleanup failures according to the project's existing conventions. Database-specific exceptions must not leak arbitrary internal details to API consumers. Failures must leave transactions and sessions in a known state. Where the correct behavior is uncertain, stop and report rather than guessing. 

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier. 

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode production credentials, expose PostgreSQL publicly, modify production ftd_lakehouse, delete existing application behavior to simplify implementation, or create mock database behavior in place of required integration verification. If a test cannot run because infrastructure is unavailable, the agent must report the infrastructure boundary rather than disguising it as a passing test. 

The developer is the authority for infrastructure, credentials, database selection, migrations with destructive consequences, branch strategy, and architectural deviations. The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan. Whenever an operation could mutate a real database, the agent must first establish that the target is the isolated development/test application database. If that cannot be proven, the operation must not proceed. 

## **SUBLAYER 2.1 — ESTABLISH THE DATABASE ACCESS BOUNDARY** 

### **Instruction** 

The objective of Sublayer 2.1 is to establish a single explicit and reusable mechanism through which backend application code obtains PostgreSQL access. The agent must first inspect the existing repository for database configuration, engine or connection creation, session handling, ORM models, dependency functions, environment-variable loading, migration configuration, and existing database tests. The investigation must be narrow and purposeful: determine what 

already exists, determine what is missing from the intended boundary, and avoid unrelated repository exploration. 

The resulting architecture must separate database connection/session lifecycle from API route logic. A FastAPI route or endpoint must not create a new PostgreSQL connection manually for each operation if the project already has a session/dependency mechanism. Database credentials must come from the established environment or secret mechanism. They must never be hardcoded into source files, workflow files, frontend bundles, documentation intended for public repositories, or test fixtures that are committed to Git. 

The agent must preserve the existing database technology if it is already working. If SQLAlchemy is already the established mechanism, use the existing SQLAlchemy configuration. If another supported database-access mechanism is already established, use that mechanism. Do not migrate technologies during this sublayer. The goal is a clean boundary, not a technology replacement. 

### **Tools to use and why** 

Use IDE file search and symbol navigation first to locate database configuration, session creation, model definitions, application initialization, dependency injection, and tests. Use the terminal to inspect dependency declarations and run the existing backend test suite before changing code so that a baseline is recorded. Use Git diff and status continuously so that unrelated changes are not accidentally incorporated. Use the existing migration tool only if the repository already uses one and only when a schema change is demonstrably required. 

Use the project's configured Python interpreter or virtual environment rather than a system interpreter when running backend tests. Use the existing test runner and project commands from the repository documentation. Do not install packages globally. If a dependency is missing, determine whether it is already declared in the project's dependency manifest before adding anything. 

### **Implementation** 

Implement the smallest missing database-access boundary. Centralize engine or connection configuration where appropriate, establish predictable session lifecycle, and provide the dependency or repository mechanism that application code will use. Ensure sessions are released after requests and that failed operations do not leave sessions in an unusable state. If transactions are managed by a higher-level convention already present in the repository, preserve that convention rather than introducing a second transaction model. 

The agent must test successful connection acquisition, normal session cleanup, unavailabledatabase behavior where practical, and failure cleanup. Tests should distinguish between pure unit behavior and real database integration behavior. A mock may be used for unit testing session-management logic, but a mock must never be represented as proof that PostgreSQL itself works. 

### **Error handling** 

Connection failures must be caught at the correct architectural boundary and translated into the application's established error behavior. Do not expose hostnames, passwords, stack traces, SQL statements, or internal database topology to an external API consumer. Session cleanup must occur even when an operation raises. Transaction state must be rolled back when the established transaction model requires rollback after failure. If the correct error mapping cannot be established from existing conventions, stop rather than inventing a new error contract. 

### **Developer responsibilities** 

The developer must identify and approve the isolated development/test PostgreSQL database before any mutating integration test is executed. The developer must provide or approve required credentials through the appropriate secret or environment mechanism. The developer must manually confirm that production ftd_lakehouse is not the target. 

### **IDE agent responsibilities** 

The IDE agent may inspect the repository, implement the database boundary, create or update tests, run tests, and document findings. It may not independently select a production database, expose credentials, or perform destructive database operations. 

### **Hard stop** 

Under no circumstances may the agent expose PostgreSQL directly to the internet or frontend, commit credentials, modify ftd_lakehouse, replace the existing database technology, create unrelated schemas, implement content retrieval, or continue into the service/business-logic architecture. If the database boundary cannot be established through the existing architecture, stop and report. 

## **SUBLAYER 2.2 — ESTABLISH THE APPLICATION-USER CRUD CONTRACT** 

### **Instruction** 

The objective of Sublayer 2.2 is to prove that the database boundary established in 2.1 can perform real application-user persistence operations without placing persistence logic inside FastAPI routes. The agent must inspect the existing application-user schema, model, constraints, identifiers, and Firebase relationship before implementing anything. Existing fields and constraints are authoritative. Do not invent fields because a future UI might want them. 

CRUD is being used as a controlled verification mechanism. It must not become an excuse to build an administrative user-management product. Implement only operations that are justified by the existing application architecture. The database access layer should contain the persistence operation; the API layer, if an API operation is required for verification, should call the established lower-level mechanism rather than embedding SQL. 

### **Tools to use and why** 

Use IDE symbol search to locate the existing user model and any current user-related database operations. Use the database migration files or schema documentation to confirm actual columns and constraints. Use the existing ORM or SQL mechanism for queries. Use the existing backend test framework for unit and integration tests. Use Git diff to ensure only user-domain changes are being made. 

Use the isolated test/application database for mutating integration tests. Before running create, update, or delete tests, verify the configured database target. Prefer test fixtures or transaction rollback mechanisms already used by the repository. Do not create ad hoc shell scripts that mutate production databases. 

### **Implementation** 

Implement user create, retrieve, update, and delete behavior only to the extent required by the existing application. Retrieval must correctly handle an existing user and a missing user. Creation must respect database constraints and must not create duplicate identities where the existing schema forbids them. Update must preserve identifiers and immutable identity relationships unless the existing domain explicitly permits changing them. Delete must follow the existing domain's semantics and must not cascade into unrelated application domains without an explicit existing rule. 

Keep database-specific logic in the database access boundary. If the operation requires application-level validation, keep that validation out of raw persistence code when the repository's architecture provides a service or domain layer for it. Do not prematurely implement the complete Layer Three service architecture; Layer Two's responsibility is the persistence boundary. 

### **Error handling** 

Handle missing records explicitly rather than returning arbitrary null values that callers cannot distinguish from database failure. Handle uniqueness and foreign-key violations according to the application's established error model. Roll back failed transactions where appropriate. Do not swallow exceptions with broad except clauses that make failures look successful. Do not return success after a database mutation whose commit failed. 

### **Developer responsibilities** 

The developer must approve the exact test database and any data-reset strategy. The developer must review any migration or schema change before it is applied. Destructive testing must be isolated and reversible. 

### **IDE agent responsibilities** 

The IDE agent may implement the persistence functions, tests, minimal API wiring required to exercise them, and error mapping. It must not create a frontend CRUD interface or connect React to PostgreSQL. 

### **Hard stop** 

Under no circumstances may the agent create PostgreSQL users directly from React, expose database credentials, bypass the database-access layer, add unrelated schema, modify production data, or build financial/content functionality. If existing user semantics conflict with this plan, stop and report the conflict. 

## **SUBLAYER 2.3 — ESTABLISH CONTROLLED RELATIONAL AGGREGATION** 

### **Instruction** 

The objective of Sublayer 2.3 is to demonstrate controlled retrieval of meaningful relational application data without forcing clients to understand PostgreSQL relationships. The planned approach is backend-side relational aggregation. PostgreSQL joins or equivalent relational operations should occur behind the database boundary, and the resulting data should be represented in an application-appropriate structure by the backend. 

The agent must first identify an actual existing relationship in the application-user domain that requires relational retrieval. Do not invent relationships merely to demonstrate a join. If no legitimate relational use case exists in the current application, the agent must stop and report that 2.3 cannot be responsibly implemented yet rather than manufacturing a schema relationship. 

### **Tools to use and why** 

Use repository schema/model inspection to identify real foreign-key or relational relationships. Use the existing ORM/query mechanism to construct the smallest query that satisfies the real use case. Use database query inspection or logging only in a controlled development/test environment when necessary to verify that the expected relational query is being executed. Use integration tests against the isolated database to verify actual relational behavior. 

### **Implementation** 

Implement one concrete relational retrieval path that demonstrates why aggregation belongs behind the backend boundary. The database access layer should retrieve the necessary relational data, while the application-facing representation should avoid exposing database implementation details unnecessarily. Do not make the frontend reconstruct joins by issuing multiple unrelated requests unless the existing architecture explicitly requires that pattern. 

The implementation should be designed around the actual application requirement rather than around a generic repository abstraction. Do not build a universal query builder, generic data graph, dynamic SQL system, or speculative abstraction. The smallest correct relational operation is preferred. 

### **Error handling** 

The implementation must distinguish a missing related record from a database connectivity failure. Referential-integrity failures must be handled according to the database's constraints 

and application conventions. Query failures must not be silently converted into empty datasets because an empty result and a failed database operation have different meanings. 

### **Developer responsibilities** 

The developer must approve the selected real relational use case and verify that its data exists only in the isolated application/test database. The developer should review the query semantics before any schema relationship is introduced. 

### **IDE agent responsibilities** 

The IDE agent may implement the query, mapping, and tests once a real relationship is confirmed. It may not create speculative relationships or unrelated schemas. 

### **Hard stop** 

Under no circumstances may the agent introduce GraphRAG, vector storage, financial data, content ingestion, lakehouse retrieval, or a new public API merely to demonstrate relational aggregation. If no valid relational use case exists, stop. 

## **SUBLAYER 2.4 — QUERY INTEGRITY, PERFORMANCE, AND TRANSACTION BEHAVIOR** 

### **Instruction** 

The objective of Sublayer 2.4 is to make the database boundary reliable under failure rather than merely successful under ideal conditions. Inspect transaction behavior, session lifecycle, constraint handling, query shape, connection cleanup, and obvious repeated-query inefficiencies. This is not a production performance project. The goal is correctness, predictable resource handling, and avoidance of obvious architectural mistakes. 

The agent must establish what transaction convention the repository already uses. If the application uses request-scoped sessions, unit-of-work patterns, explicit commits, or another existing mechanism, preserve that convention unless a concrete defect is demonstrated. Do not introduce multiple competing transaction-management strategies. 

### **Tools to use and why** 

Use the existing test framework to create failure-path tests. Use database logs or query instrumentation only when needed to establish a concrete behavior. Use the ORM's existing facilities for transaction and session handling. Use Git diff to review changes. Use local profiling or query inspection only when a real inefficiency has been observed. 

### **Implementation** 

Verify that sessions are closed, failed transactions are rolled back, successful transactions are committed exactly when intended, and database errors do not leave application state ambiguous. Verify that a multi-step operation either completes according to its transaction boundary or fails without leaving a partially applied state when atomicity is required. 

Inspect obvious query inefficiencies such as retrieving all columns when only a small set is required or issuing repeated database calls for the same request when one established relational query can satisfy the operation. Do not optimize hypothetical workloads. Do not add indexes, caching, connection pools, or schema changes without evidence that they address an actual current requirement. 

### **Error handling** 

Every intentionally tested failure must result in a deterministic state. The agent must test at least the relevant connection failure, validation failure, constraint failure, missing-record condition, and transaction failure paths that the existing domain can actually produce. Broad exception swallowing is forbidden. Error messages must remain useful to developers while avoiding disclosure of secrets or internal topology to API consumers. 

### **Developer responsibilities** 

The developer must approve any schema-level performance change. The developer must approve changes that could alter transaction semantics across existing application behavior. 

### **IDE agent responsibilities** 

The IDE agent may diagnose and correct concrete transaction, session, or query-integrity defects and add regression tests. It may not perform speculative optimization. 

### **Hard stop** 

Under no circumstances may the agent restructure PostgreSQL for hypothetical scale, add speculative indexes, introduce caching solely because it might be useful later, or expand the data model beyond the current user-domain requirement. If correctness cannot be established, stop rather than optimizing around uncertainty. 

## **SUBLAYER 2.5 — END-TO-END DATABASE BOUNDARY VERIFICATION** 

### **Instruction** 

The objective of Sublayer 2.5 is to prove that the complete backend-to-PostgreSQL path works as one system. The verification must distinguish unit tests, mocked tests, and real integration tests. A mocked database test is not evidence that PostgreSQL connectivity, schema compatibility, constraints, migrations, or SQL behavior are correct. At least the meaningful persistence paths must be exercised against the isolated PostgreSQL application/test database. 

The final verification path should establish API request, FastAPI handling, database access operation, PostgreSQL execution, database result, and application response. The exact API operation used for verification must come from the existing architecture or the minimal API boundary required to exercise the database layer. Do not build a frontend to prove a backend database boundary. 

### **Tools to use and why** 

Use the existing backend test runner for unit and integration tests. Use the configured project environment rather than system-wide packages. Use the isolated PostgreSQL instance for real integration tests. Use GitHub Actions only where the existing Layer One CI infrastructure can safely run the database tests; do not redesign CI/CD as part of this sublayer. Use Git status and diff before completion to confirm that the branch contains only intended Layer Two changes. 

When an integration test fails, inspect the failure at the boundary that actually failed. Do not immediately rewrite code. Determine whether the failure is caused by application logic, schema state, database availability, credentials, network access, migration state, or test assumptions. The agent must report infrastructure failures as infrastructure failures rather than masking them. 

### **Implementation** 

Create a focused end-to-end verification suite that proves successful user persistence and retrieval, relevant failure cases, relational retrieval where implemented, and correct transaction behavior. Tests should establish that the backend cannot accidentally retrieve arbitrary data when the requested application identity or record does not exist. 

Run the existing test suite as a regression check after the Layer Two tests pass. Compare the final result with the baseline established at the beginning of the layer. Any regression must be investigated and resolved or explicitly reported before Layer Two can be declared complete. 

### **Error handling** 

The verification suite must fail loudly when PostgreSQL is unavailable, when the schema is incompatible, when migrations are missing, when credentials are invalid, or when the backend returns an unexpected response. Do not skip integration tests merely because the database is inconvenient to reach. If the environment prevents a required test from running, stop the implementation and report the environmental blocker. 

### **Developer responsibilities** 

The developer must review the final test target and confirm that it is isolated from production. The developer must review the final diff and approve completion before the next major architectural layer begins. 

### **IDE agent responsibilities** 

The IDE agent may run the complete verification suite, diagnose failures, make in-scope corrections, and document the final architecture. It must stop after successful verification rather than continuing into future layers. 

### **Hard stop** 

Under no circumstances may the agent proceed into frontend integration, Firebase integration, content delivery, financial-data APIs, dashboard construction, search, workspace functionality, AI/RAG integration, production optimization, or any subsequent product layer. Once the 

complete Layer Two database path is successfully tested and architectural boundaries are verified, implementation must stop completely. 

## **FINAL LAYER TWO DEFINITION OF DONE** 

Layer Two is complete only when the application has a clean, backend-controlled, tested PostgreSQL access path; the application-user persistence operations use that path; any legitimate relational retrieval occurs behind that boundary; transaction and error behavior are deterministic; and real integration tests against the isolated PostgreSQL environment prove the path works. The resulting architecture must allow later service-layer code to call a stable persistence boundary without knowing connection-management details, while API consumers remain unaware of PostgreSQL implementation details. 

The final conceptual architecture is FastAPI API boundary, application operation, database access layer, PostgreSQL, database result, and application response. The completion of Layer Two does not authorize work on Layer Three. Any subsequent development must be treated as a separate architectural phase and planned independently. 

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture. 