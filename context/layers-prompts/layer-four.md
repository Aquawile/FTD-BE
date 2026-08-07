# SUBLAYER 4.2 — Authenticated User API Operations

The objective of this sublayer is to take the authenticated user functionality that was already completed and verified in Layer Three and expose those existing operations through the FastAPI HTTP boundary. **This is an implementation task, not an architecture-discovery task.** Sub-Layer 4.1 has already established the Layer Four FastAPI structure, routing conventions, application entrypoint, authentication dependency integration point, and existing project patterns. Treat the implementation produced and verified in 4.1 as authoritative. Do not restart architectural investigation, reconsider the framework, search for alternative authentication approaches, or redesign the existing route structure unless a concrete error proves that the existing implementation cannot support this sublayer.

Before making changes, inspect only the directly relevant existing files needed to connect the already-established FastAPI layer to the already-established Layer Three user service. At minimum, use the existing FastAPI application/router structure from 4.1, the Layer One authentication dependency that 4.1 already integrated or exposed, the Layer Three user service implementation, and the existing Pydantic models directly related to users. Do not scan the entire repository looking for alternative implementations. If the necessary implementation pattern is already visible in those files, use it immediately. **Do not spend additional reasoning cycles searching for a "better" pattern once a consistent existing pattern has been identified.**

The architectural flow for this sublayer is fixed and should be implemented exactly as follows: **HTTP request → FastAPI route → existing Layer One authentication dependency → authenticated PostgreSQL application-user context → existing Layer Three user service operation → Pydantic/application response → HTTP response.** The FastAPI route is an adapter between HTTP and the existing application service. It must not become a second implementation of the service layer.

Use the existing Layer Three user service functions as the sole source of application behavior. Do not rewrite SQL, database connection logic, CRUD operations, permission aggregation, user synchronization, or other database behavior inside FastAPI. If a Layer Three function already performs the required operation, call that function. Do not create a second function that performs the same database operation merely because the operation is now being exposed through HTTP.

Use the authentication dependency that already exists from Layer One and was established during the previous layers. Do not manually decode Firebase tokens inside the route. Do not create a second Firebase validation mechanism. Do not manually reconstruct authentication context from the `Authorization` header if the existing dependency already performs that work. The route should consume the authenticated application-user context provided by the existing authentication mechanism and pass the appropriate identifier or user object into the existing Layer Three service function.

The important identity chain is already established and must remain intact: Firebase authenticates the external identity, Layer One resolves that identity to the PostgreSQL application user, and the service layer operates on the PostgreSQL application identity. Do not treat the Firebase UID itself as a replacement for the PostgreSQL user model. Do not introduce new identity translation logic into the HTTP handler.

Use the Pydantic request and response models that already exist in the repository for the user domain. Inspect the existing user models directly and reuse them when they represent the required HTTP payload. If one genuinely does not exist for a specific operation, create only the smallest missing Pydantic model in the same model organization already used by the project. Do not introduce a new schema library, serialization framework, validation framework, or parallel model hierarchy.

Expose only the user operations that the Layer Three service already supports and that were verified during Layer Three. The purpose of this sublayer is to create an HTTP boundary over existing functionality, not to expand the application's domain. Do not create endpoints for permissions as independent public resources, financial data, content, dashboards, searches, workspaces, AI functionality, pipeline data, or any other future application capability. Do not create generic CRUD endpoints that dynamically expose PostgreSQL tables.

For each endpoint, keep the implementation thin. FastAPI should handle HTTP concerns such as path/query/body parsing, dependency injection, request validation, and response serialization. The existing service layer should perform application operations. PostgreSQL access should remain below the service boundary. If a service operation internally performs a relational join or aggregation, leave that operation where it already exists. **Never move SQL joins or database queries into the FastAPI route simply because the endpoint needs combined data.**

The endpoint responses must contain application-level representations rather than database implementation details. Do not return psycopg2 cursors, raw cursor objects, connection objects, tuples that depend on database ordering, or arbitrary internal database structures. Use the existing application/Pydantic response models so FastAPI can validate and serialize the result consistently.

Use conventional HTTP semantics for the operations that already exist. A successful retrieval should use the appropriate successful retrieval response. Successful creation should communicate that a resource was created using the project's existing conventions. Updates and deletion should translate the existing service outcome into an appropriate HTTP result. Do not introduce elaborate response envelopes, custom status conventions, or additional HTTP abstractions unless the existing codebase already uses them.

Authentication failures must remain separate from application-level identity and authorization failures. A missing or malformed credential should be handled by the existing Layer One authentication dependency. A valid Firebase identity that cannot be mapped to a PostgreSQL application user is a different failure and should use the existing application behavior established in the previous layers. Do not create a new authorization framework in this sublayer. Do not add roles, permission systems, workspace ownership, resource-level authorization, Firebase custom claims, or other access-control mechanisms that were not already established by the previous layers.

The implementation should be deliberately small. If an existing Layer Three function can be called directly from a FastAPI route, do that rather than creating another intermediate abstraction. If an existing authentication dependency can be attached through `Depends(...)`, use it rather than writing equivalent authentication code. If an existing Pydantic model already matches the response, reuse it rather than defining another model. The goal is to connect existing components, not increase the number of components.

## Implementation Procedure

Start by reading the relevant output and implementation from Sub-Layer 4.1 and identify the existing FastAPI application object, router organization, and route-registration pattern. Then inspect only the Layer Three user service module and the Layer One authentication dependency/model interfaces required by those routes. Identify the exact existing service functions that correspond to the user operations being exposed. Once those functions and interfaces are identified, stop investigating alternatives and implement the routes using those exact components.

Next, add the authenticated user routes to the existing FastAPI router structure established in 4.1. Attach the existing authentication dependency to the protected operations. Pass the authenticated PostgreSQL application-user context into the service functions using the service's existing expected arguments. Do not modify the service signatures merely to make the route easier to write unless a concrete incompatibility exists.

Then attach the existing Pydantic response models to the routes where they already represent the returned application data. Allow FastAPI to perform response serialization and validation. If the existing service returns a model or object that already maps correctly to the response model, use that path rather than manually reconstructing the object inside the route.

After implementation, run only the focused tests necessary to establish that the routes import correctly, the FastAPI application starts, authenticated requests reach the intended service functions, and the resulting HTTP response has the expected status and structure. Reuse the existing Layer One authentication test mechanism and isolated PostgreSQL test environment from the previous layers. Do not create a new database, authentication system, testing framework, or HTTP test infrastructure.

If a test fails, diagnose the failure from the actual traceback and make the smallest correction within the scope of this sublayer. Do not respond to a single failure by restarting repository-wide architectural investigation. First determine whether the failure is in route wiring, dependency injection, request validation, service invocation, response validation, or an already-existing lower-layer component. If the failure belongs to Layer One, Layer Two, or Layer Three, do not rewrite that lower layer merely to make 4.2 pass. Stop and report the lower-layer dependency instead.

Do not repeatedly rerun the same failing command without changing anything. If the same command produces the same error twice and the cause is not immediately resolved, stop that diagnostic path, inspect the actual error and directly relevant source, and make one bounded hypothesis before trying again. Do not perform broad exploratory commands merely because the first implementation attempt failed.

If a terminal operation becomes unexpectedly expensive, hangs, produces repeated errors, or begins generating large amounts of output, stop the operation rather than repeatedly rerunning it. Do not perform broad repository searches, dependency discovery, package installation, database inspection, network diagnosis, or unrelated infrastructure investigation unless the current route implementation has a concrete dependency that cannot otherwise be resolved. **Do not ask for permission to perform ordinary focused tests or short commands; only stop for user approval if an operation would modify infrastructure, production data, credentials, firewall configuration, database schema, or another resource outside the intended scope of this sublayer.**

## Testing Requirements

The primary test is the authenticated HTTP path. Establish a valid authenticated test identity using the authentication/testing mechanism already established in Layer One. Send the request through the FastAPI application rather than directly invoking the service function. Confirm that the existing authentication dependency recognizes the Firebase identity, resolves the PostgreSQL application user, and allows the request to reach the appropriate Layer Three service operation.

Test the successful path first. Verify the HTTP status, response structure, and relevant user data. Then verify the existing authentication failure behavior using a missing credential and an invalid credential. Where the existing Layer One test infrastructure already provides an expired-token case, reuse it rather than creating another mechanism for generating expired tokens.

Verify at least one failure condition where a Firebase identity cannot be mapped to an application user if the existing Layer One/Layer Three behavior supports that scenario. The purpose is to establish that the API does not incorrectly treat a Firebase identity as sufficient application identity.

Do not build the comprehensive manual Postman workflow yet. Do not begin testing frontend behavior. The purpose of this sublayer is simply to establish that the HTTP boundary correctly reaches the already-tested application services.

## Scope Guardrails

Do not modify Firebase project configuration, Firebase credentials, Firebase token validation, or Firebase Admin initialization. Those responsibilities belong to Layer One and are already complete.

Do not modify PostgreSQL schemas, migrations, database credentials, database connection infrastructure, repository queries, relational aggregation, permission-index logic, or test-database architecture. Those responsibilities belong to Layers One through Three and must remain unchanged.

Do not rewrite Layer Three service functions to contain HTTP-specific behavior. The service layer must remain independent of FastAPI and must not receive `Request`, `Response`, HTTP headers, HTTP status codes, or FastAPI-specific objects merely to support this sublayer.

Do not add frontend code or client-side API calls. Do not connect the web application's UI to these endpoints yet. Do not implement content delivery, financial data endpoints, search endpoints, dashboard endpoints, workspace endpoints, AI functionality, or pipeline-data endpoints.

Do not introduce a new ORM, database abstraction layer, authentication library, API framework, serialization framework, migration framework, or testing framework. Use the packages and patterns already present in the repository.

Do not introduce authorization logic beyond the existing authentication/application-user boundary. A valid authenticated user is sufficient for the scope of these user operations unless the already-existing Layer Three service explicitly requires an application-level condition.

Do not optimize, refactor, rename, reorganize, or "clean up" unrelated code. If unrelated technical debt is discovered, record it and leave it untouched.

## HARD STOP FOR SUBLAYER 4.2

The sublayer is complete when the existing Layer Three user operations are reachable through the existing FastAPI application, the existing Layer One authentication dependency successfully establishes the PostgreSQL application-user context, successful authenticated HTTP requests return validated application-level responses, and representative authentication failures produce the expected HTTP behavior.

**At that point, stop immediately. Do not proceed into comprehensive Postman testing, frontend integration, client-side API calls, broader API coverage, content endpoints, or any other Layer Four sublayer. Do not continue looking for improvements after the completion criteria have been demonstrated. Report the files changed, the exact routes exposed, the tests executed, their results, and any remaining issue, then wait for the next sublayer instruction.**
