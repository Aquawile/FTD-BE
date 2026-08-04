now that you have that configured and secure, as well as having context for where the webapp is currently at, here are your next steps. follow them very strictly, and you are required to stop your response and report back to me for approval of moving into the next sublayer once you finish the current sublayer you are on.

I will structure this as a **Layer One implementation specification prompt for an IDE agent**. I am intentionally stopping at Firebase + PostgreSQL user identity because that is the correct architectural boundary from our discussion. The goal of this layer is **not** to create the full application backend, service layer, content APIs, or frontend integration. The purpose is to establish a reliable identity foundation that future layers can depend on.

---

# LAYER ONE IMPLEMENTATION PROMPT: USER IDENTITY FOUNDATION WITH FIREBASE AUTHENTICATION AND POSTGRESQL USER MODEL

You are implementing Layer One of the backend architecture. The objective of this layer is to create a complete and reliable user identity foundation that separates authentication responsibilities from application data ownership. This layer establishes the relationship between Firebase Authentication and our PostgreSQL database, where Firebase is responsible for verifying user identity and managing authentication credentials, while PostgreSQL becomes the source of truth for application-specific user records and future user-related relationships.

Do not implement any frontend functionality, application service layer, content access layer, financial data endpoints, CRUD operations for non-user resources, workspace functionality, search functionality, or any logic involving SEC, Finnhub, GNews, or existing pipeline data. Those belong to future layers and must remain untouched. The only goal of this layer is to ensure that a user can be created, authenticated, verified, synchronized with PostgreSQL, and safely represented inside our application database.

Before making any changes, inspect the existing authentication architecture, PostgreSQL schema, environment configuration, deployment structure, and current backend framework. Do not assume file locations, existing patterns, or naming conventions. Identify the existing authentication code, database connection layer, migration system, ORM usage if applicable, and current API structure before implementing anything. Preserve existing functionality and do not replace existing authentication logic without understanding how it currently works.

---

# SUBLAYER 1.1: Firebase Authentication Integration and Configuration

The first objective is to establish Firebase as the identity provider responsible only for authentication operations. Firebase should manage user credentials, email verification status, secure password handling, and identity tokens. Firebase should not become the application's primary user database. The PostgreSQL database must remain responsible for storing application-level user information.

Use Firebase Authentication as the authentication provider. Configure Firebase Admin SDK within the backend environment so that the backend can securely verify Firebase-issued identity tokens. Do not expose Firebase service credentials or private keys to the client. Store all Firebase configuration values using the existing secure environment variable and secret management practices already used in the project.

The implementation should include Firebase project configuration, backend initialization, secure credential loading, and a reusable Firebase authentication module. This module should have a single responsibility: validating that a Firebase identity token is authentic and extracting the Firebase UID and verified identity information from it.

The Firebase integration should not directly perform application authorization decisions. Do not place application permissions, roles, workspace ownership, or business-specific access rules inside Firebase custom claims unless explicitly required later. Authorization belongs to our PostgreSQL-backed application model.

The completion criteria for this sublayer are that the backend can successfully communicate with Firebase, validate a Firebase token, extract the Firebase UID, and reject invalid or expired tokens with appropriate errors.

At the end of this sublayer, stop implementation. Do not proceed into PostgreSQL user synchronization until Firebase token validation has been manually tested.

Testing requirements for this sublayer are to use Firebase testing tools and API clients such as Postman. Generate a valid Firebase authentication token, send it to a temporary protected test route, verify successful validation, then test expired, malformed, and missing tokens to verify expected authentication failures.

---

# SUBLAYER 1.2: PostgreSQL User Domain Model Creation

The second objective is creating our own application user model inside PostgreSQL. This table represents the application's understanding of a user and should not duplicate Firebase responsibilities. It exists because the application requires information that Firebase does not own.

Create or modify the PostgreSQL user schema so that a Firebase identity can be mapped to an internal application user. The database should store the Firebase UID as the external identity reference. The PostgreSQL user table should become the source of truth for application-level identity.

The table design should support future expansion but should remain limited to identity responsibilities only. Do not add future application features such as saved searches, workspaces, dashboards, financial preferences, or AI-related metadata. Those belong to later layers.

The user model should contain the information required to identify and manage an application user. This includes the internal database identifier, Firebase UID reference, email address, account status, creation timestamp, update timestamp, and any fields required to determine whether the account is active. Avoid storing duplicate authentication secrets because Firebase manages credentials.

Implement this using the existing database migration system. Do not manually modify production tables without migrations. Every schema change must be reproducible.

Use the existing PostgreSQL connection pattern and ORM/database tooling already present in the codebase. Do not introduce a new ORM, migration framework, or database abstraction layer.

The completion criteria for this sublayer are that a PostgreSQL user table exists, migrations execute successfully, the table accurately represents application identity, and Firebase identities can be mapped to database users.

At the end of this sublayer, stop implementation. Manually inspect the created table, verify constraints, and confirm that no authentication responsibilities were incorrectly moved into PostgreSQL.

---

# SUBLAYER 1.3: Firebase-to-PostgreSQL User Synchronization

The third objective is creating the connection between Firebase authentication and our internal user model. When a user authenticates through Firebase, the backend should be capable of creating or retrieving the corresponding PostgreSQL user record.

Implement a synchronization process where a verified Firebase identity maps to exactly one PostgreSQL user record. The backend should use the Firebase UID as the stable external identifier. Do not use email as the primary relationship key because email addresses can change and are not guaranteed to represent identity permanently.

The synchronization logic should follow this pattern: Firebase verifies identity, backend receives Firebase UID, backend checks PostgreSQL for an existing user record, backend creates the record if it does not exist, and backend retrieves the existing record if it already exists.

This synchronization logic should be isolated into its own backend module or service. Do not place database creation logic directly inside authentication middleware. Authentication middleware should verify identity, while user synchronization logic should manage persistence.

Handle duplicate registration attempts safely. The system should not create duplicate PostgreSQL users when the same Firebase identity authenticates multiple times.

Implement appropriate database constraints to prevent duplicate Firebase UID records. Use transactions where necessary to prevent race conditions during simultaneous account creation.

The completion criteria for this sublayer are that a Firebase-authenticated user can successfully create a PostgreSQL user record, repeated authentication retrieves the existing user instead of creating duplicates, and invalid Firebase identities cannot create database users.

Testing requirements include creating a test Firebase account, authenticating successfully, verifying the PostgreSQL record creation, authenticating again, verifying no duplicate user exists, and testing invalid authentication scenarios.

Stop implementation after this sublayer. Do not build user-facing endpoints yet.

---

# SUBLAYER 1.4: User Authentication Middleware and Protected User Retrieval

The fourth objective is connecting authenticated identity to backend request handling. The backend should be able to understand who is making a request before any future application logic is executed.

Implement authentication middleware or dependency injection using the existing backend architecture. This layer should validate Firebase tokens, retrieve the corresponding PostgreSQL user, and provide that authenticated user context to future backend routes.

Do not implement authorization rules beyond confirming the user exists and is authenticated. Permissions, roles, and resource ownership logic belong to later application layers.

The middleware should provide consistent behavior for missing tokens, invalid tokens, expired tokens, unverified users if applicable, and users that exist in Firebase but not PostgreSQL.

Implement standardized error responses. Authentication failures should not expose sensitive information. Errors should clearly distinguish between unauthenticated requests and internal server failures.

The completion criteria for this sublayer are that future backend endpoints can depend on a single authentication mechanism that reliably identifies the current user.

Testing requirements are to create protected test routes only for validating authentication. These routes should return authenticated user information from PostgreSQL. Test valid authentication, missing credentials, invalid credentials, expired tokens, and deleted PostgreSQL users.

Stop implementation after this point.

---

# SUBLAYER 1.5: Logging, Error Handling, and Validation Foundation

The final objective of Layer One is establishing observability around the authentication system. Every authentication-related operation should produce enough information for debugging without exposing sensitive user data.

Implement structured logging for authentication events, including successful authentication attempts, failed authentication attempts, user synchronization events, and unexpected failures. Logs should contain identifiers useful for tracing requests, such as Firebase UID or internal user ID where appropriate, but must never contain passwords, tokens, or secrets.

Implement centralized error handling for authentication failures. The backend should consistently return appropriate HTTP responses for invalid credentials, missing authentication, expired tokens, database failures, and unexpected exceptions.

Do not create full application logging infrastructure yet. Only implement what is necessary to make the identity layer observable and debuggable.

The completion criteria for this sublayer are that authentication failures can be diagnosed through logs, errors are returned consistently, and the identity system can be tested without relying on frontend behavior.

---

# LAYER ONE FINAL VALIDATION REQUIREMENT

Layer One is considered complete only when the following workflow succeeds entirely:

A new user can register through Firebase Authentication. The user receives email verification. After verification, the backend can validate the Firebase identity token. The backend creates or retrieves the corresponding PostgreSQL user record. A protected backend test endpoint can identify the authenticated user from PostgreSQL. Invalid authentication attempts fail correctly. Logs provide enough context to debug failures.

After this milestone is complete, stop all implementation.

Do not begin the application service layer, PostgreSQL content querying, CRUD endpoints for financial data, Postman collections for application resources, frontend integration, or any client-facing functionality until Layer One has been manually reviewed and approved. The purpose of this stopping point is to guarantee that the identity foundation is stable before additional application architecture is built on top of it.