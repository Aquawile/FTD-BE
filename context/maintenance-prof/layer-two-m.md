# Layer Two — Application Data Access and Service Architecture

## Objectives and Goals

Layer Two exists to answer a deceptively simple question: how does an authenticated HTTP request safely and predictably interact with your PostgreSQL database without the frontend ever needing to understand your relational schema? Layer One established who the user is through Firebase authentication and PostgreSQL user records. Layer Two builds the machinery that turns that authenticated identity into meaningful database operations.

The central architectural goal is establishing a clean separation between four concerns: HTTP handling, application/service behavior, database access, and database structure. Your FastAPI endpoints receive requests and return responses. The service layer expresses what an operation actually means in application terms. The database access layer executes raw SQL against PostgreSQL. And PostgreSQL itself remains an internal data store, never directly exposed to clients.

The target architecture flows like this: a client sends a request to FastAPI, Layer One establishes the authenticated identity, the service layer orchestrates the application operation, the database access layer executes the query, PostgreSQL returns relational results, the service layer transforms those into application-level results, and FastAPI serializes the response. The client never sees table names, foreign keys, or join conditions.

The eventual preferred strategy for related information is backend-side aggregation. When a client needs information spanning multiple tables, the backend performs the SQL joins and returns a coherent application response rather than forcing the client to make separate requests and reconstruct relationships themselves. This does not mean avoiding joins — joins are how relational databases work efficiently. The concern is where that complexity lives and who has to understand it.

---

## Sublayer 2.1: Service Layer Architecture and Database Access Boundary

The first sublayer establishes the structural foundation. Before implementing any operations, you need one clear path through which application code reaches the database. The goal is not to build every operation immediately but to ensure the architecture exists for implementing them cleanly.

We created a dedicated service directory with explicit purpose statements for every operation. Each service function documents what it accomplishes in application terms before any code is written. For example, the purpose is "retrieve the application User corresponding to the authenticated Firebase identity" rather than "execute a SELECT query." This distinction matters because it keeps the service layer focused on application meaning rather than database mechanics.

The authentication middleware was deliberately simplified. It validates tokens and attaches identity information to the request — either a Firebase UID or an internal user ID depending on the authentication method. But it does not retrieve full User objects or permissions. That retrieval happens in the service layer, consumed by FastAPI dependencies that endpoints request. This separation means the middleware handles only authentication (proving who you are), while the service layer handles application logic (what that identity means for the operation).

Database session lifecycle remained controlled and predictable. We reused the existing connection pool mechanism with context managers that guarantee connections are returned to the pool even when operations fail. No route creates its own connection or invents its own session management. The existing connection dependency pattern is the single mechanism for database access.

The demonstration operation was retrieving the authenticated user. The service layer receives a Firebase UID, queries the database through the repository layer, and returns a typed User object. The database access layer knows how to query PostgreSQL; the service layer orchestrates the call and returns the typed domain object.

---

## Sublayer 2.2: User CRUD Operations and Database Contract

With the architecture established, the second sublayer implements actual CRUD operations against the User domain. Each operation is defined by what it accomplishes in application terms, not by what SQL it executes.

Creation represents registering an application user, not creating a Firebase credential. Firebase owns authentication credentials; PostgreSQL owns the application user record. The service validates email format and normalizes it, validates password length, and hashes the password before persistence. PostgreSQL's UNIQUE constraint on email serves as the final integrity boundary — the service catches the resulting integrity error and translates it into an application-level conflict exception.

Retrieval supports obtaining the authenticated user's application record and retrieving a user by internal identifier. Both operations explicitly handle the missing-record case by raising a not-found exception rather than returning null. This is important because callers cannot distinguish a null result from a database failure without explicit handling.

Updating modifies only application-owned fields — email and active status. The Firebase UID, internal identifiers, and password hash are not modifiable through this operation. This enforces the boundary between Firebase identity (which Firebase owns) and application data (which the application owns).

Deletion follows soft-delete semantics. The PostgreSQL row is not removed; instead, the active status is set to false. This preserves the Firebase identity independence — deactivating the application account does not affect the Firebase authentication credentials. PostgreSQL's transaction mechanism ensures the update either commits entirely or rolls back.

Response models explicitly exclude sensitive fields. The password hash never leaves the backend. The Firebase UID is visible to the client (it is the connection between Firebase identity and application record) but cannot be modified through the API. This creates the first meaningful boundary between PostgreSQL's internal representation and the external API contract.

---

## Sublayer 2.3: Relational Query and Aggregation Pattern

This sublayer establishes how the backend handles information spanning multiple tables without forcing clients to understand the relational structure. The key principle: the SQL join happens inside PostgreSQL as part of a deliberate backend query, while the frontend receives a useful application-level object.

We implemented a representative aggregation that combines a user with their granted permissions. The repository layer performs a single LEFT JOIN between the users table and the permissions index, using ARRAY_AGG to collect permission names into a single array. This is one deliberate relational query that selects only the required columns.

The service layer orchestrates this query and transforms the raw database row into a typed response model. The result is a UserPermissionsResponse containing the user identity and their permissions collection in a single coherent object. The client receives this as a JSON response without ever knowing that permissions live in a separate table joined through a foreign key.

We verified that appropriate indexes exist on the join columns. PostgreSQL does not automatically create indexes on referencing columns for foreign keys, so we confirmed the user_permissions_index table has indexes on user_id and a composite index on (user_id, permission_name). This ensures the join query executes efficiently without full table scans.

The query avoids N+1 behavior. Rather than querying for the user first then issuing separate queries for each permission, a single query retrieves everything. This is the pattern that scales: when application operations require related data, perform the relational work inside the backend boundary.

---

## Sublayer 2.4: Query Performance, Integrity, and Transaction Boundary

This sublayer ensures the architecture behaves correctly under failure, not merely functions under ideal conditions. The goal is not performance optimization but establishing basic discipline for PostgreSQL operations.

We verified that read operations do not produce accidental N+1 query patterns. The relational aggregation in 2.3 uses a single deliberate query rather than lazy traversal of relationships. When the service layer needs related data, it requests it explicitly rather than relying on implicit lazy loading.

Write operations use appropriate transaction boundaries. The repository layer manages transactions explicitly — beginning a transaction, executing the operation, committing on success, and rolling back on failure. Failed writes do not leave partial state. The service layer catches database-specific exceptions and translates them into application-level errors without exposing internal details.

We inspected the foreign-key relationships involved in User operations and verified appropriate indexes exist. The users table has a primary key on id, a unique constraint on email, and an index on firebase_uid for the Firebase lookup path. The permissions junction table has indexes supporting both the user-to-permissions lookup and the reverse lookup.

Error messages remain useful to developers while avoiding disclosure of secrets or internal topology. A not-found error includes the identifier that was not found (useful for debugging) but does not include connection strings, hostnames, or SQL statements.

---

## Sublayer 2.5: End-to-End API Contract and Manual Backend Validation

The final sublayer proves the architecture works from the perspective of an API client without requiring a frontend. We used HTTP clients to exercise the actual API endpoints and verify the complete authenticated path.

Testing covered successful and intentionally unsuccessful requests. Authentication failures return appropriate status codes. Malformed request data is caught by Pydantic validation before reaching the service layer. Nonexistent resources return not-found responses. Constraint violations are translated into conflict responses. Valid creation, retrieval, update, and deletion all behave correctly.

For every operation, we identified which architectural boundary handles each concern. HTTP validation errors occur at the FastAPI boundary. Authentication failures occur at the middleware boundary. Not-found conditions occur at the service layer. Database constraint violations are caught at the repository layer and translated into service exceptions. This layering means a failed request can be diagnosed by understanding which boundary failed rather than simply seeing a generic error.

The documented API contract describes each operation in terms of its purpose, HTTP method and path, authentication requirement, expected request body, expected response, and important failure cases. This documentation describes what the API actually does, not what future features might do.

---

## What Errors We Ran Into and How We Fixed Them

During the Layer Two implementation, several issues emerged that required investigation and resolution.

The first challenge was determining where User retrieval should happen. Initially, the authentication middleware attempted to retrieve the full User object from the database during token validation. This created a tight coupling between authentication and database access. The fix was to separate concerns: the middleware validates the token and attaches only the identity identifier (Firebase UID or user ID), while the service layer retrieves the full User object when needed. This means authentication failures (invalid token) are handled separately from application failures (user not found).

Another issue was handling database connection failures gracefully. When the database is unavailable, the original code would propagate raw psycopg2 exceptions to the API layer. We added explicit exception handling in the service layer that catches database failures and translates them into application-level errors. The logging captures the original exception for developer debugging while the API returns an appropriate error response.

The CRUD operations initially had inconsistent error handling. Some operations returned null for missing records while others raised exceptions. We standardized on explicit exception raising for missing records, with the service layer raising domain-specific exceptions (NotFoundError, AlreadyExistsError, ValidationError) that the API layer translates into appropriate HTTP status codes.

Testing revealed that the relational aggregation query needed index verification. Without proper indexes on the join columns, the LEFT JOIN between users and permissions would perform full table scans. We verified the existing indexes were sufficient and documented the indexing strategy for future maintenance.

---

## Why We Chose These Solutions

We deliberately chose to build on existing architecture rather than introduce new frameworks. The project already used raw psycopg2 with a connection pool, so we continued using that mechanism rather than introducing an ORM. This decision was intentional: the existing mechanism works, the team understands it, and introducing an ORM would add complexity without solving a concrete problem.

The service layer pattern was chosen because it creates a clear boundary between HTTP concerns and application concerns. Service functions accept application inputs and return application results. They do not know about HTTP requests, status codes, or response serialization. This means the same service operation could be called from a FastAPI endpoint, a background task, or a test harness without modification.

Soft deletion was chosen over hard deletion to preserve the independence of Firebase identity and application data. If a user deactivates their account, the application record is preserved (with is_active set to false) but the Firebase credentials remain intact. This allows account reactivation without requiring re-registration through Firebase.

Explicit exception raising was chosen over returning null or error codes because it makes error handling impossible to ignore. A function that returns null forces every caller to check for null. A function that raises an exception forces every caller to handle the exception or let it propagate. This makes the code more robust because errors cannot be silently ignored.

The backend-side aggregation pattern was chosen because it keeps relational complexity inside the backend where it belongs. The client receives application-level objects that match its needs rather than raw database rows that require reconstruction. This reduces the number of API calls needed and prevents the client from needing to understand the database schema.

---

## The Architectural Boundary Between Layer Two and Layer Three

Layer One established the identity chain: Firebase identity becomes a Firebase token becomes authentication becomes a PostgreSQL user becomes an authenticated application user.

Layer Two establishes the data access chain: authenticated application user leads to FastAPI endpoint leads to service operation leads to database operation leads to PostgreSQL leads to relational result leads to application response.

Layer Three, which comes next, determines how the eventual financial and content experience should be represented to the client. Layer Two deliberately stops at the service boundary — it proves the machinery works but does not decide what content the client consumes.

The key distinction is that Layer Two does not mean "make all the joins now." It means establish the correct mechanism for doing joins when an application operation actually requires them. The representative aggregation in 2.3 was deliberately small — just one relational query combining users with permissions. The actual complexity of deciding which financial entities should be aggregated for the user belongs to Layer Three.

Layer Two is therefore much more manageable than the entire data-serving system. You are not building the complete content architecture. You are building and proving the machinery through which a legitimate authenticated application request can safely interact with your existing relational PostgreSQL system.
