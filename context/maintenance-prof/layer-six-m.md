# LAYER SIX — REGRESSION TEST SYSTEM AND CI/CD INTEGRATION

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Six after completion of Major Layer Five. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Five is complete. Layer Six is a new architectural phase. The purpose of this phase is to transform the existing test suite from a development-time verification tool into a permanent, automated regression protection system that participates in the CI/CD pipeline. The desired architectural direction is: code change → unit tests (fast, no infrastructure) → integration tests (real database, isolated) → deployment → post-deployment verification. The test suite must become an automated answer to "did this new change break something that previously worked?"

The agent must begin by creating or using a dedicated Layer Six working branch derived from the correct completed Layer Five revision. The agent must never push directly to main under any circumstance. The agent must not rewrite or force-push shared history. The agent must preserve the successful Layer Five CI/CD behavior unless a concrete Layer Six requirement makes a change unavoidable. Any such change must be isolated, explained, tested, and kept within the scope of Layer Six.

The implementation must remain deliberately narrow. The concrete domain is the existing test suite in `tests/` and the CI/CD workflows (`.github/workflows/ci.yml` and `.github/workflows/deploy.yml`). The agent must not implement new application features, new API endpoints, new database schemas, or new infrastructure. The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required regression protection.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Test work must use the project's existing test framework (pytest), database driver (psycopg2), and test conventions. Do not introduce a competing test framework, test runner, or database abstraction merely because another tool is familiar.

Error handling is part of implementation, not an afterthought. Every test boundary must account for unavailable database connections, invalid input, missing records, constraint violations, transaction failures, unexpected database exceptions, and cleanup failures according to the project's existing conventions. Test failures must not leak arbitrary internal details to consumers. Failed tests must leave test databases in a known state. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode production credentials, expose any environment publicly, modify production databases, delete existing test behavior to simplify implementation, or create mock test behavior in place of required integration verification. If a test cannot run because infrastructure is unavailable, the agent must report the infrastructure boundary rather than disguising it as a passing test.

The developer is the authority for infrastructure provisioning, credential approval, environment selection, branch strategy, and architectural deviations. The IDE agent is responsible for repository inspection, test restructuring, CI/CD integration, execution, and diagnosis within the approved plan. Whenever an operation could mutate a real database, the agent must first establish that the target is the isolated test database. If that cannot be proven, the operation must not proceed.

## **SUBLAYER 6.1 — CATEGORIZE AND STRUCTURE THE TEST SUITE**

### **Instruction**

The objective of Sublayer 6.1 is to inventory, categorize, and restructure the existing test suite into a clear hierarchy that reflects infrastructure requirements and regression intent. The agent must first inspect the entire `tests/` directory, every test file, every test class, and every test function to understand what currently exists. The investigation must be narrow and purposeful: determine which tests are pure unit tests (no external dependencies), which are integration tests requiring a real PostgreSQL database, which are API contract tests requiring a running FastAPI application, and which are deployment verification tests requiring a deployed environment. The investigation must avoid unrelated repository exploration.

The resulting structure must separate tests into distinct categories with explicit markers or directory organization that makes their infrastructure requirements unambiguous. The categories are: **Unit Tests** (no external dependencies, run in milliseconds, suitable for every CI run), **Database Integration Tests** (require isolated PostgreSQL test database, test repository/service layer against real schema), **API Contract Tests** (require running FastAPI application, test router endpoints with real HTTP requests), and **Post-Deployment Verification Tests** (require fully deployed environment with version endpoint, test end-to-end paths). Each test file and test class must be assigned to exactly one category.

The agent must preserve the existing test framework (pytest) and test conventions. Do not migrate to a different test framework or introduce new testing abstractions. The goal is categorization, not rewriting. Existing test logic must remain functionally unchanged — only organization and metadata change.

### **Tools to use and why**

Use IDE file search and symbol navigation first to locate all test files, test classes, test functions, pytest markers, fixtures, and configuration. Use the terminal to run `pytest --collect-only` to enumerate every test item and its current structure. Use `grep` to find existing pytest markers (`@pytest.mark.*`), fixtures, and configuration in `conftest.py` or `pytest.ini`. Use Git diff to ensure only categorization changes are made.

Use the project's existing Python interpreter and virtual environment. Do not install packages globally. If a dependency is missing, determine whether it is already declared in the project's dependency manifest before adding anything.

### **Implementation**

Restructure the test suite by adding explicit pytest markers to every test class and test function that indicate their category:

- `@pytest.mark.unit` — pure unit tests, no external dependencies
- `@pytest.mark.db_integration` — requires PostgreSQL database (uses `ftd_lakehouse_test` or `ftd_lakehouse_api_test`)
- `@pytest.mark.api_contract` — requires running FastAPI application (TestClient or HTTP)
- `@pytest.mark.post_deploy` — requires fully deployed environment (version endpoint, IAP tunnel)

If the repository does not already have a `pytest.ini` or `conftest.py` defining these markers, create one. The markers must be registered so that `pytest --markers` lists them with descriptions.

Organize test files (or test classes within files) so that each category is visually and logically distinct. If a single file contains tests of multiple categories, use class-level markers to separate them. Do not move test functions between files unless the existing organization is actively misleading.

Update the CI workflow (`.github/workflows/ci.yml`) to run each category as a separate stage with appropriate infrastructure:
- Stage 1: Unit tests (`-m unit`) — runs on every push, no infrastructure
- Stage 2: Database integration tests (`-m db_integration`) — runs with test database credentials
- Stage 3: API contract tests (`-m api_contract`) — runs with FastAPI TestClient (no deployed VM needed)
- Stage 4: (Optional in CI) Post-deployment tests — run only in deploy workflow verification job

### **Error handling**

Tests that require unavailable infrastructure (e.g., database credentials not configured) must skip with a clear message, not fail. Use pytest's `skipif` with a condition that checks for required environment variables. The skip message must indicate exactly what is missing (e.g., "skipped: PGHOST not set"). Tests must not silently pass when infrastructure is missing.

If a test's category cannot be determined from its code, the agent must stop and report the ambiguity rather than guessing.

### **Developer responsibilities**

The developer must approve the final categorization before it is committed. The developer must provide or approve test database credentials for CI integration tests. The developer must review the modified CI workflow.

### **IDE agent responsibilities**

The IDE agent may inspect the test suite, add markers, create/update `pytest.ini` or `conftest.py`, update the CI workflow, and run tests to verify categorization works. The agent must not change test logic, add new tests, or modify assertions.

### **Hard stop**

Under no circumstances may the agent change test logic, weaken assertions, delete tests, combine categories into a single marker, or run integration tests without proper infrastructure. If the test suite cannot be cleanly categorized, stop and report.

## **SUBLAYER 6.2 — CI/CD PIPELINE INTEGRATION FOR REGRESSION TESTING**

### **Instruction**

The objective of Sublayer 6.2 is to integrate the categorized test suite into the CI/CD pipeline as mandatory regression gates. The agent must first inspect the current CI workflow (`.github/workflows/ci.yml`) and deploy workflow (`.github/workflows/deploy.yml`) to understand the existing stage structure, trigger conditions, and gate mechanisms. The investigation must be narrow and purposeful: determine how to add test stages as mandatory prerequisites for deployment without breaking existing functionality.

The resulting pipeline must enforce that no deployment proceeds if any regression test fails. The CI workflow must run unit tests, database integration tests, and API contract tests as separate, sequential stages. Each stage must be a distinct job (or job step with explicit fail-fast) that blocks the pipeline on failure. The deploy workflow must continue to poll the CI workflow for the same commit SHA and only proceed when all stages report success. The existing CI polling mechanism in the deploy workflow must be preserved and must wait for all test stages, not just a single job.

The agent must preserve the existing workflow technology and patterns. Do not introduce new CI/CD platforms, custom runners, or complex workflow orchestration. The existing GitHub Actions patterns (jobs, steps, `needs:`, `if:` conditions, `gh run list` polling) are authoritative.

### **Tools to use and why**

Use the existing `.github/workflows/ci.yml` and `.github/workflows/deploy.yml` as the authoritative reference for workflow structure, job dependencies, and polling patterns. Use the GitHub Actions workflow syntax reference for job-level `needs:` dependencies, matrix strategies, and conditional execution. Use the terminal to validate YAML syntax and test workflows by pushing to the working branch. Use `gh run list` and `gh run view` to inspect workflow execution.

Use the project's existing pytest markers and test conventions. Do not introduce new test discovery mechanisms or custom test runners.

### **Implementation**

Modify `.github/workflows/ci.yml` to split the single `validate` job into four sequential jobs with explicit `needs:` dependencies:

1. **`unit-tests`** job: runs `pytest -m unit -v`, no external dependencies, always runs
2. **`db-integration-tests`** job: `needs: unit-tests`, runs `pytest -m db_integration -v`, requires test database credentials via repository secrets (`CI_PGHOST`, `CI_PGPASSWORD`, etc.), skips gracefully with clear message if secrets unavailable
3. **`api-contract-tests`** job: `needs: db-integration-tests`, runs `pytest -m api_contract -v`, uses FastAPI TestClient (no deployed VM needed)
4. **`ci-complete`** job: `needs: [unit-tests, db-integration-tests, api-contract-tests]`, trivial success step that serves as the single completion target for deploy workflow polling

The deploy workflow's `Verify CI passed` step in each job must continue to poll for the `ci-complete` job's success for the same commit SHA. The polling logic must not change.

Each test job must have `continue-on-error: false` (fail-fast). The `ci-complete` job must only succeed if all dependencies succeeded.

### **Error handling**

If database integration tests skip due to missing credentials, the job must still report success (with clear log output) so the pipeline can proceed to API contract tests. The CI must not fail due to missing optional infrastructure. However, if credentials ARE provided and tests fail, the pipeline must fail.

If a test job fails, the pipeline must stop immediately — no subsequent jobs run. The deploy workflow polling must detect the failure and report it clearly.

### **Developer responsibilities**

The developer must review the modified CI workflow before it is committed. The developer must provide or approve test database credentials for CI integration tests. The developer must verify that the deploy workflow polling correctly waits for the new `ci-complete` job.

### **IDE agent responsibilities**

The IDE agent may modify `.github/workflows/ci.yml`, test the workflow by pushing to the working branch, and verify that the deploy workflow polling works correctly. The agent must not modify the deploy workflow's polling logic.

### **Hard stop**

Under no circumstances may the agent remove the CI gate from the deploy workflow, combine test stages into a single job, allow deployments to proceed when any test stage fails, or change the deploy workflow's polling mechanism. If the pipeline cannot be structured with explicit job dependencies, stop and report.

## **SUBLAYER 6.3 — TEST DATABASE MANAGEMENT AND ISOLATION**

### **Instruction**

The objective of Sublayer 6.3 is to establish a reliable, isolated test database strategy that ensures integration tests never interfere with development, staging, or production databases. The agent must first inspect the current test database usage patterns: which databases are used by which tests, how test data is created and cleaned up, whether tests run in parallel or sequence, and whether the current approach leaves the test database in a consistent state. The investigation must be narrow and purposeful: determine the current isolation mechanism (if any) and identify gaps.

The resulting strategy must guarantee that:
- Integration tests run against a dedicated test database (`ftd_lakehouse_test` for unit-style integration tests, `ftd_lakehouse_api_test` for API contract tests) that is NEVER the production database (`ftd_lakehouse`) or staging database (`ftd_lakehouse_staging`)
- Each test run starts from a known schema state (migrations applied, baseline seed data present)
- Test data created during a test run is cleaned up after the run (transaction rollback, explicit cleanup, or database reset)
- Parallel test execution does not cause cross-test contamination
- The test database can be reset to a clean state programmatically for CI runs

The agent must preserve the existing database technology and migration mechanism. Do not introduce a new database management tool, ORM migration system, or test database framework. The existing SQL migration files and psycopg2 connection pattern are authoritative.

### **Tools to use and why**

Use the existing migration files (`app/auth/migrations/001-005_create_auth_tables.sql`) and the migration application script (`scripts/apply_staging_migrations.sh` pattern) as the authoritative reference for schema management. Use the existing `app/db.py` connection pool and `get_connection()` context manager for database interactions. Use `psycopg2` directly for administrative operations (database creation, truncation, schema inspection). Use the terminal to verify database state before and after test runs.

Use the project's existing database connection patterns. Do not introduce a new database abstraction layer, test fixture framework, or ORM for test data management.

### **Implementation**

Create a test database management script (e.g., `scripts/manage_test_databases.sh`) that provides the following operations:

1. **`create-test-dbs`**: Creates `ftd_lakehouse_test` and `ftd_lakehouse_api_test` on `ftd-postgres-vm` with owner `ftd_app`, applies all migrations (001-005), seeds baseline permissions data
2. **`reset-test-dbs`**: Truncates all data tables (preserving schema), re-seeds baseline permissions data, resets sequences
3. **`drop-test-dbs`**: Drops the test databases (for cleanup)

The script must use `sudo -u postgres psql` on `ftd-postgres-vm` via IAP tunnel, following the same pattern as `scripts/apply_staging_migrations.sh`.

Modify the test suite to use a pytest fixture (session-scoped) that:
- Before test session: calls `reset-test-dbs` to ensure clean state
- After test session: calls `reset-test-dbs` to leave database clean for next run
- Provides a function-scoped fixture that wraps each test in a transaction and rolls back after the test (for tests that need transaction isolation)

The CI workflow's `db-integration-tests` job must call `reset-test-dbs` before running tests.

### **Error handling**

Database creation/reset failures must fail fast with clear error messages (which SQL failed, what the PostgreSQL error was). The script must not leave databases in a partially created state. If a test fails and leaves the database in a dirty state, the next test run's reset must clean it up.

### **Developer responsibilities**

The developer must approve the test database management script before it is used. The developer must verify that the script targets only the correct test databases and never touches production or staging databases.

### **IDE agent responsibilities**

The IDE agent may create the management script, add pytest fixtures, modify the CI workflow to call the reset script, and test the isolation by running integration tests multiple times. The agent must not modify production or staging databases.

### **Hard stop**

Under no circumstances may the agent run test management operations against `ftd_lakehouse` (production) or `ftd_lakehouse_staging` (staging). If the test database strategy cannot be implemented without risking production data, stop and report.

## **SUBLAYER 6.4 — POST-DEPLOYMENT VERIFICATION TESTS**

### **Instruction**

The objective of Sublayer 6.4 is to formalize the existing deploy workflow verification steps as a structured, repeatable post-deployment test suite that runs against the actual deployed environment. The agent must first inspect the current `deploy-staging-verify` job in `.github/workflows/deploy.yml` and the manual verification procedures used during Layer Five to understand what checks are currently performed. The investigation must be narrow and purposeful: extract the verification logic into a structured test suite that can be run independently and provides clear pass/fail signals.

The resulting verification test suite must run against the fully deployed staging environment (or development environment when triggered) and verify:
- Web VM serves React frontend and health endpoint
- Web VM correctly proxies `/api/*` requests to Backend VM
- Backend VM serves `/health` and `/version` endpoints
- `/version` endpoint returns metadata matching the deployed commit SHA
- `version.json` file on both VMs contains correct metadata
- No cross-deployment to the other environment
- Database connectivity from Backend VM to Database VM
- Authentication flow works end-to-end (Firebase token → API → database user)

The agent must preserve the existing verification patterns. Do not introduce a new testing framework for post-deployment checks. The existing `curl` + `jq` pattern via `gcloud compute ssh` is authoritative. The checks must be structured as executable scripts or pytest tests that can run in the deploy workflow's verification job and also be run manually by developers.

### **Tools to use and why**

Use the existing `deploy-staging-verify` job steps as the authoritative reference for what checks to formalize. Use `gcloud compute ssh` with `--tunnel-through-iap` for VM access. Use `curl` for HTTP endpoint checks. Use `jq` for JSON parsing where needed. Use the existing IAP tunnel patterns for accessing deployed endpoints. Do not introduce a new HTTP testing framework, service mesh, or monitoring tool.

### **Implementation**

Create a post-deployment verification script (e.g., `scripts/verify_deployment.sh`) that takes the target environment as an argument (`development` or `staging`) and the expected commit SHA. The script must:

1. Determine target VMs based on environment (`ftd-test` for development; `ftd-staging-web` + `ftd-staging-api` for staging)
2. Run all verification checks via `gcloud compute ssh` with `--tunnel-through-iap`
3. Output structured results (JSON or clear pass/fail per check)
4. Exit with code 0 if all checks pass, non-zero if any check fails

The checks must include:
- Frontend served: `curl http://<web-vm>:8080/` returns HTML
- Web health: `curl http://<web-vm>:8080/health` returns "healthy"
- API proxy health: `curl http://<web-vm>:8080/api/health` returns `{"status":"ok"}`
- API version via proxy: `curl http://<web-vm>:8080/api/version` contains expected commit SHA
- Backend health: `curl http://<api-vm>:8000/health` returns `{"status":"ok"}`
- Backend version: `curl http://<api-vm>:8000/version` contains expected commit SHA
- Version metadata files: `cat /home/isabellabutera/version.json` on both VMs matches
- Cross-deployment check: other environment's version unchanged
- Database connectivity: Backend VM can query PostgreSQL

Integrate this script into the deploy workflow's verification job, replacing the inline `curl` steps with a call to the script. The script must be committed to the repository and deployed to the runner (or run from the runner directly).

### **Error handling**

Each check must output a clear pass/fail message with the actual vs expected values. The script must fail fast on the first failed check (or continue and report all failures, then exit non-zero). Network failures (VM unreachable, IAP tunnel broken) must be reported as infrastructure errors, not test failures.

### **Developer responsibilities**

The developer must approve the verification script before it is used. The developer must verify that the script correctly identifies failures when they occur.

### **IDE agent responsibilities**

The IDE agent may create the verification script, integrate it into the deploy workflow, and test it by triggering deployments. The agent must not change the verification criteria or weaken checks.

### **Hard stop**

Under no circumstances may the agent skip any of the required verification checks, modify the script to always pass, or run verification against the wrong environment. If the verification script cannot be structured to run reliably, stop and report.

## **SUBLAYER 6.5 — REGRESSION TEST EXECUTION AND REPORTING**

### **Instruction**

The objective of Sublayer 6.5 is to establish the operational procedures for running, monitoring, and acting on regression test results. The agent must first inspect how test results are currently surfaced (GitHub Actions UI, logs, artifacts) and how failures are communicated. The investigation must be narrow and purposeful: determine what reporting and alerting mechanisms exist and what gaps remain.

The resulting system must ensure that:
- Every test run (CI or post-deployment) produces a clear, machine-readable summary of results
- Failed tests block the pipeline and are visible in GitHub Actions UI with actionable context (which test, what assertion failed, what the expected vs actual values were)
- Test execution time is tracked and reported (to detect performance regressions)
- Flaky tests are identified and quarantined (not silently ignored)
- A developer can answer "did this PR break anything?" by looking at the PR's check status without digging into logs

The agent must preserve the existing GitHub Actions reporting mechanisms. Do not introduce external reporting tools, custom dashboards, or notification systems. The existing GitHub Actions annotations, job summaries, and artifact uploads are authoritative.

### **Tools to use and why**

Use the existing GitHub Actions features: job summaries (`$GITHUB_STEP_SUMMARY`), annotations (`::error::`), artifact uploads (`actions/upload-artifact`), and the `gh` CLI for programmatic access. Use pytest's built-in `--junitxml` output for structured test results. Use the terminal to verify that reports are generated correctly.

### **Implementation**

1. **CI Test Reporting**: Modify each test job in `.github/workflows/ci.yml` to:
   - Generate JUnit XML output: `pytest ... --junitxml=test-results.xml`
   - Upload `test-results.xml` as an artifact with retention
   - Generate a job summary with pass/fail counts and duration
   - Use `::error::` annotations for failed tests so they appear inline in the PR checks

2. **Post-Deployment Verification Reporting**: Modify the verification script to:
   - Output structured JSON results to a file
   - Upload the results as a deploy workflow artifact
   - Write a job summary with pass/fail status for each check

3. **Flaky Test Detection**: Add a mechanism (can be manual initially) to track tests that fail intermittently. Document known flaky tests in a `FLAKY_TESTS.md` file with the test name, failure pattern, and mitigation.

3. **PR Check Integration**: Ensure the CI workflow posts a consolidated status check on PRs that reflects all test stages. The `ci-complete` job's success/failure must be the required status check for branch protection (if enabled).

### **Error handling**

Reporting failures must not mask test failures. If artifact upload fails, log a warning but continue. If JUnit XML generation fails, fall back to text output. The pipeline must never report success when tests actually failed.

### **Developer responsibilities**

The developer must review the reporting configuration. The developer must configure branch protection rules (if desired) to require the `ci-complete` status check.

### **IDE agent responsibilities**

The IDE agent may modify workflows to add reporting, create the flaky test tracking file, and test the reporting by triggering test runs. The agent must not change test logic or weaken assertions.

### **Hard stop**

Under no circumstances may the agent suppress test failures in reporting, mark failed tests as skipped to achieve green status, or remove the CI gate from deployment. If reporting cannot be implemented without hiding failures, stop and report.

## **FINAL LAYER SIX DEFINITION OF DONE**

Layer Six is complete only when the repository has a complete, automated regression test system integrated into the CI/CD pipeline: the test suite is categorized into unit, database integration, API contract, and post-deployment verification tests with explicit pytest markers; the CI workflow runs all categories as mandatory sequential stages with explicit job dependencies, failing fast on any regression; the deploy workflow polls for the complete CI success (all test stages) before deploying; test databases are managed by a dedicated script that ensures isolation, clean state, and no risk to production/staging data; post-deployment verification runs as a structured script against the actual deployed environment and produces structured results; every test run produces clear, actionable reporting in GitHub Actions UI with annotations and summaries; a developer can answer "did this change break anything?" by looking at the PR's check status without digging into logs; a broken test at any stage blocks deployment; the complete chain (commit → unit tests → db integration tests → api contract tests → deploy → post-deploy verification) is visible in GitHub Actions history.

The resulting architecture makes the test suite a permanent, automated regression shield that protects the application against unintended changes. The completion of Layer Six does not authorize work on Layer Seven. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.