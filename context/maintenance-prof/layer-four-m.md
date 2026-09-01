# LAYER FOUR — GITHUB ACTIONS CI/CD PIPELINE

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Four after completion of Major Layer Three. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Three is complete. Layer Four is a new architectural phase. The purpose of this phase is to establish a deliberate, gated, and automated CI/CD pipeline using GitHub Actions that takes repository changes through validation, testing, and environment-specific deployment. The desired architectural direction is: code push → CI validation (lint, type-check, unit tests, integration tests) → gate → environment determination (development vs staging branch) → deploy to correct target VM with isolated database → verify deployment health and version metadata. The pipeline must enforce that broken tests block deployment — no deployment proceeds if validation fails.

The agent must begin by creating or using a dedicated Layer Four working branch derived from the correct completed Layer Three revision. The agent must never push directly to main under any circumstance. The agent must not rewrite or force-push shared history. The agent must preserve the successful Layer Three branch-to-environment mapping unless a concrete Layer Four requirement makes a change unavoidable. Any such change must be isolated, explained, tested, and kept within the scope of Layer Four.

The implementation must remain deliberately narrow. The concrete domain is the existing GitHub Actions workflows (.github/workflows/ci.yml and .github/workflows/deploy.yml) and the application components they deploy: FastAPI backend, React frontend, Cloud Functions (start-price-vm, gnews-ingest), and VM scripts (prices). SEC data, GNews data, Finnhub data, ticker data, financial content, lakehouse content, RAG, vector storage, dashboard behavior, frontend integration, recommendation systems, and production optimization are not Layer Four work. The agent must not implement or prepare those systems as part of this layer.

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required pipeline gates. Do not refactor for aesthetics, personal preference, framework fashion, or theoretical future requirements.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. CI/CD work must use the project's existing GitHub Actions patterns, gcloud CLI commands, Workload Identity authentication, and IAP tunneling. Do not introduce a competing CI/CD platform, deployment framework, or environment management system merely because another tool is familiar.

Error handling is part of implementation, not an afterthought. Every pipeline stage must account for authentication failures, dependency installation failures, test failures, build failures, VM unreachable, SSH/IAP tunnel failures, health check timeouts, and version metadata verification failures. Pipeline failures must not leak arbitrary internal details to consumers. Failed deployments must leave environments in a known state. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode production credentials, expose any environment publicly, modify production databases, delete existing deployment behavior to simplify implementation, or create mock deployment behavior in place of required integration verification. If a pipeline stage cannot run because infrastructure is unavailable, the agent must report the infrastructure boundary rather than disguising it as a passing stage.

The developer is the authority for infrastructure provisioning, credential approval, environment selection, branch strategy, and architectural deviations. The IDE agent is responsible for repository inspection, workflow implementation, test construction, execution, and diagnosis within the approved plan. Whenever an operation could mutate a real environment, the agent must first establish that the target is the correct isolated environment for the branch being deployed. If that cannot be proven, the operation must not proceed.

## **SUBLAYER 4.1 — AUDIT EXISTING CI/CD AND ESTABLISH BASELINE**

### **Instruction**

The objective of Sublayer 4.1 is to perform a complete audit of the existing GitHub Actions CI/CD implementation before making any changes. The agent must first inspect both workflow files (.github/workflows/ci.yml and .github/workflows/deploy.yml) in their entirety, understand the current trigger conditions, job structure, steps, permissions, secrets usage, and deployment targets. The investigation must be narrow and purposeful: determine what currently works, what gaps exist between the current state and the required gated pipeline model, and avoid unrelated repository exploration.

The resulting audit must document: current CI trigger branches, current CI validation steps (Python tests, Node build, artifact upload), current deploy trigger branches, current deploy job structure (single job vs multiple jobs), current deployment targets (ftd-test VM, Cloud Functions, data-ingest-vm), current secret usage (FTD_TEST_PG_PASSWORD, Workload Identity), current health verification (HTTP health check only), current version metadata recording (echo only, no persistent file), and any gaps against the Layer Four requirements (gated deployment, environment-specific jobs, version endpoint verification, branch-to-environment enforcement).

The agent must preserve the existing CI/CD technology if it is already working. The current workflows use github-actions/checkout, actions/setup-python, actions/setup-node, google-github-actions/auth, google-github-actions/setup-gcloud, and gcloud CLI commands. This pattern must be extended rather than replaced. Do not migrate to Jenkins, GitLab CI, CircleCI, or any other CI/CD platform during this sublayer. The goal is a clean audit and baseline, not a technology replacement.

### **Tools to use and why**

Use IDE file search and symbol navigation first to locate the workflow files, any referenced scripts (scripts/start_app.sh), environment variable references, and secret references. Use the terminal to inspect the current workflow runs via gh CLI (gh run list, gh run view) to understand recent execution history and failure patterns. Use Git log to understand the commit history that triggered deployments. Use the existing test runner (pytest) and build commands (npm ci, npm run build) to establish a baseline of what passes locally. Use Git diff to ensure no unintended changes are made during the audit phase.

Use the project's existing GitHub CLI authentication (gh) and gcloud CLI patterns. Do not install additional CI/CD tools. If a dependency is missing from the audit toolkit, determine whether it is already declared in the project's dependency manifest before adding anything.

### **Implementation**

Produce an audit document (can be a markdown file in the repository or reported directly to the developer) that contains:

1. **Current CI workflow analysis**: Trigger configuration, job steps, pass/fail criteria, artifact handling, gaps against required validation gates.
2. **Current Deploy workflow analysis**: Trigger configuration, job structure (single job), conditional deployment logic (commit message keywords), target environments, secret injection, health check implementation, version recording mechanism.
3. **Gap analysis**: Missing gated deployment (CI must pass before deploy), missing environment-specific jobs (development vs staging), missing version metadata persistence, missing version endpoint verification, branch-to-environment mapping enforcement.
4. **Baseline test results**: Run the existing test suite locally and record pass/fail counts. Run the frontend build locally and record success/failure.

The agent must not modify any workflow files during this sublayer. The audit is read-only inspection and documentation.

### **Error handling**

If workflow files cannot be located, report the missing files immediately. If gh CLI cannot access workflow runs, report the authentication/permission boundary. If local test runner fails due to missing dependencies, report the environment boundary. Do not guess at workflow behavior — only report what is observed in the files and execution history.

### **Developer responsibilities**

The developer must review the audit findings and approve the gap analysis before any workflow modifications begin. The developer must confirm the target environments (development VM, staging VM) and their corresponding databases are correctly provisioned and accessible.

### **IDE agent responsibilities**

The IDE agent may read workflow files, execute gh CLI commands to inspect run history, run local tests and builds, and produce the audit report. The agent must not modify workflow files, create new workflow files, or change any CI/CD configuration during this sublayer.

### **Hard stop**

Under no circumstances may the agent modify .github/workflows/ci.yml or .github/workflows/deploy.yml during this sublayer. The agent must not create new workflow files. The agent must not change trigger conditions, job structure, or deployment logic. If the audit cannot be completed because files are missing or inaccessible, stop and report.

## **SUBLAYER 4.2 — RESTRUCTURE CI WORKFLOW WITH GATED VALIDATION**

### **Instruction**

The objective of Sublayer 4.2 is to restructure the CI workflow (.github/workflows/ci.yml) into a proper gated validation pipeline that must pass before any deployment can proceed. The agent must first inspect the current CI workflow structure, then modify it to include explicit validation stages: lint/type-check (if tooling exists), unit tests (no database required), integration tests (database required, run against isolated test database), and frontend build. Each stage must be a separate job or step that can fail independently and block the pipeline. The workflow must trigger on pushes to both rawdataingestion (development) and staging branches, and on pull requests to those branches.

The resulting CI workflow must enforce that all validation passes before marking the workflow as successful. The deploy workflow (modified in 4.3) will gate on this CI workflow's success for the same commit SHA. No deployment should proceed if any CI stage fails. The CI workflow must not deploy anything — it only validates. The CI workflow must produce a clear pass/fail signal that the deploy workflow can consume.

The agent must preserve the existing validation tools if they are already working. The current workflow runs pytest for backend tests and npm ci/npm run build for frontend. If the repository has linting (ruff, flake8, mypy) or type-checking configured, those must be added as separate steps. If not, the agent must not introduce new tooling — only use what exists. The frontend build artifact upload must be retained for potential reuse by deploy.

### **Tools to use and why**

Use IDE file search to locate any linting or type-checking configuration (pyproject.toml, ruff.toml, mypy.ini, .flake8, package.json scripts). Use the terminal to run candidate lint/type-check commands locally to verify they work before adding to CI. Use the existing test runner (pytest) and build commands (npm) as the authoritative validation steps. Use GitHub Actions job dependencies (needs:) to create explicit stage gates if splitting into multiple jobs, or sequential steps with continue-on-error: false if keeping single job.

Use the project's existing Python version (3.11 per current CI) and Node version (20 per current CI). Do not upgrade versions unless the developer explicitly approves. Use the existing requirements-dev.txt for Python test dependencies. Use the existing package-lock.json for frontend dependency caching.

### **Implementation**

Modify .github/workflows/ci.yml to:

1. **Trigger on both rawdataingestion and staging branches** (push and pull_request) — matching the branch-to-environment mapping from Layer Three.
2. **Structure as sequential validation stages** (either separate jobs with needs: or sequential steps with fail-fast):
   - Stage 1: Lint/Type-check (if tooling exists — ruff, mypy, or equivalent; skip with clear log message if not configured)
   - Stage 2: Unit tests (pytest tests/ -v -k "not postgres" or equivalent marker to exclude DB tests)
   - Stage 3: Integration tests (pytest tests/ -v -k "postgres" — requires test database credentials via repository secrets; must be skipped gracefully with clear message if secrets unavailable)
   - Stage 4: Frontend build (npm ci && npm run build in context/figma_prototype)
3. **Fail-fast behavior**: Any stage failure must fail the workflow immediately. No stage runs if a prior stage failed.
4. **Artifact upload**: Retain frontend build artifact upload for potential deploy reuse.
5. **Clear logging**: Each stage must log its start, pass/fail, and duration.

The workflow must not contain any deployment logic. It must only validate and signal success/failure.

### **Error handling**

Lint/type-check failures must be reported with file/line context. Unit test failures must show test names and assertions. Integration test failures must distinguish between test logic failures and database connectivity failures (if database unavailable, log as infrastructure skip, not test failure). Frontend build failures must show npm error output. If integration test database secrets are not configured in the repository, the stage must be skipped with a clear "integration tests skipped: test database credentials not configured" message — not a failure.

### **Developer responsibilities**

The developer must provide or approve the test database credentials for CI integration tests (if they should run in CI). The developer must approve any linting/type-checking tools to be added. The developer must review the modified CI workflow before it is committed.

### **IDE agent responsibilities**

The IDE agent may modify .github/workflows/ci.yml, run local validation commands to verify they work, and test the workflow by pushing to the working branch. The agent must not modify the deploy workflow during this sublayer. The agent must verify the CI workflow passes on the working branch before proceeding.

### **Hard stop**

Under no circumstances may the agent add deployment logic to the CI workflow. The agent must not remove the frontend build artifact upload. The agent must not hardcode database credentials in the workflow. If linting/type-checking tooling is not configured in the repository, the agent must not install or configure it — only log that it is skipped.

## **SUBLAYER 4.3 — RESTRUCTURE DEPLOY WORKFLOW WITH ENVIRONMENT-SPECIFIC JOBS**

### **Instruction**

The objective of Sublayer 4.3 is to restructure the deploy workflow (.github/workflows/deploy.yml) into environment-specific jobs that are gated by CI success and triggered by branch-to-environment mapping. The agent must first inspect the current deploy workflow structure (single job with conditional steps), then split it into two mutually exclusive deployment jobs: deploy-development (targets ftd-test VM with ftd_lakehouse_api_test database, triggers on rawdataingestion branch) and deploy-staging (targets ftd-staging VM with ftd_lakehouse_staging database, triggers on staging branch). Both jobs must gate on the CI workflow passing for the same commit SHA. The manual workflow_dispatch must require an explicit target_environment input (development or staging) — no arbitrary deployments.

The resulting deploy workflow must enforce that the branch alone determines the target environment. A push to rawdataingestion triggers only deploy-development. A push to staging triggers only deploy-staging. No commit message keyword conditions, no conditional logic within a shared job. Each job must be fully independent with its own steps, VM target, database credentials, and version metadata recording.

The agent must preserve the existing deployment technology if it is already working. The current pattern uses gcloud compute ssh with IAP tunneling, gcloud compute scp for file sync, VM process management via start_app.sh, and direct gcloud functions deploy for Cloud Functions. This pattern must be extended to the staging environment rather than replaced. Do not migrate to Cloud Deploy, Cloud Run, Kubernetes, or any other deployment platform during this sublayer. The goal is a clean branch-gated deployment structure, not a technology replacement.

### **Tools to use and why**

Use the existing deploy.yml as the authoritative reference for deployment steps, timing, and verification patterns. Use the GitHub Actions workflow syntax reference for job-level if conditions, environment declarations, and secret interpolation. Use the terminal to validate the workflow YAML syntax and to test the workflow by pushing to the respective branches. Use the existing health check pattern (curl -s http://127.0.0.1:8000/health) and version endpoint pattern (curl -s http://127.0.0.1:8000/version) as verification standards.

Use the project's existing secret management pattern (GitHub Actions secrets for credentials, injected at runtime). Do not hardcode any credentials, IPs, or passwords in the workflow file. Use the existing gcloud command patterns for SSH, SCP, and command execution via IAP tunnel. Use the existing Workload Identity authentication (google-github-actions/auth@v2 with the configured provider and service account).

### **Implementation**

Modify .github/workflows/deploy.yml to contain two deployment jobs under the deploy job graph:

1. **deploy-development job**:
   - `if: github.ref == 'refs/heads/rawdataingestion' || (github.event_name == 'workflow_dispatch' && github.event.inputs.target_environment == 'development')`
   - `environment: development` (for GitHub Environments UI)
   - `needs: ci` (gate on CI workflow success — requires workflow_call or matching workflow name)
   - Targets ftd-test VM
   - Sets PGDATABASE=ftd_lakehouse_api_test
   - Uses FTD_TEST_PG_PASSWORD secret
   - Writes version.json with environment: "development"

2. **deploy-staging job**:
   - `if: github.ref == 'refs/heads/staging' || (github.event_name == 'workflow_dispatch' && github.event.inputs.target_environment == 'staging')`
   - `environment: staging` (for GitHub Environments UI)
   - `needs: ci` (gate on CI workflow success)
   - Targets ftd-staging VM
   - Sets PGDATABASE=ftd_lakehouse_staging
   - Uses FTD_STAGING_PG_PASSWORD secret
   - Writes version.json with environment: "staging"

Both jobs must use the same step sequence, parameterized via job-level environment variables. The version.json must be written to a known path on the VM (/home/isabellabutera/version.json) and the FastAPI application must serve it at /version. The health check must verify both /health and /version endpoints, with /version confirming the deployed commit SHA matches the workflow's github.sha.

The workflow_dispatch trigger must include a required input `target_environment` with type choice (development, staging). The existing commit-message-keyword conditions (start-price-vm, gnews, prices, app, backend, frontend, deploy) must be removed from the application deployment jobs — those component deployments can remain as separate jobs or be moved to a separate workflow if they are independent of branch-to-environment mapping.

### **Error handling**

Workflow failures must be specific to the failing job and environment. A failure in deploy-development must not block or mask a concurrent deploy-staging run (though they should be mutually exclusive by branch). Health check failures must include the target environment name in the error message. SSH readiness timeout must include the VM name. Credential injection failures must identify which environment's secrets were missing. The workflow must fail fast on any step failure — no continuation past a failed step.

If the version.json write fails, the deployment must be considered failed even if the health check passes, because traceability is a hard requirement. The version endpoint verification must confirm the response contains the expected commit SHA and environment label.

### **Developer responsibilities**

The developer must review the modified workflow file before it is committed. The developer must create the staging-specific GitHub Actions secrets (FTD_STAGING_PG_PASSWORD) and verify they are accessible to the workflow. The developer must approve the branch names used in the if conditions. The developer must verify that the /version endpoint returns the correct metadata after a test deployment to each environment.

### **IDE agent responsibilities**

The IDE agent may modify the workflow file, implement the /version endpoint enhancement if not already complete, create the version.json writing step, and test the workflow by triggering deployments from both branches. The agent may not create GitHub Actions secrets, modify branch protection rules, or change the workflow's authentication mechanism. The agent must verify that a push to the development branch deploys only to ftd-test and a push to the staging branch deploys only to ftd-staging.

### **Hard stop**

Under no circumstances may the agent merge the two deployment jobs into a single job with conditional logic. The agent must not implement the version recording as a separate post-deployment step. The agent must not allow workflow_dispatch to deploy to an environment without specifying which one. The agent must not deploy to staging from the development branch or vice versa. The agent must not share the same version.json path between environments without environment identification. If the workflow cannot be cleanly split into two branch-gated jobs, stop and report.

## **SUBLAYER 4.4 — END-TO-END PIPELINE VERIFICATION AND TRACEABILITY**

### **Instruction**

The objective of Sublayer 4.4 is to prove that the complete CI/CD pipeline functions correctly and provides the required traceability. The verification must demonstrate that: a push to the development branch triggers CI, CI passes, then deploy-development runs and deploys to ftd-test with correct revision metadata; a push to the staging branch triggers CI, CI passes, then deploy-staging runs and deploys to ftd-staging with correct revision metadata; the /version endpoint on each environment returns the commit SHA, branch name, commit message, timestamp, and environment label that match the triggering push; no cross-deployment occurs (development branch never deploys to staging, staging branch never deploys to development); a failed CI run blocks deployment (push with failing tests does not trigger deploy); the deployment history is queryable via GitHub Actions UI and /version endpoint without manual VM inspection.

The verification must distinguish between automated CI/CD deployments and any manual interventions. The test must exercise the actual GitHub Actions workflows, not simulated or mocked deployments. The test must use the actual VMs, actual databases, and actual network paths.

### **Tools to use and why**

Use the existing GitHub Actions infrastructure to trigger real deployments by pushing test commits to the development and staging branches. Use the gh CLI to monitor workflow runs, inspect logs, and verify job outcomes. Use curl via IAP tunnels to query the /version and /health endpoints on both environments after deployment. Use the terminal to verify the version.json file exists on each VM with the correct content. Use Git commands to verify the commit history matches the deployed revisions.

Use the project's existing IAP tunnel patterns for accessing the application endpoints. Do not create new access methods. Use the existing test databases — the staging deployment must target ftd_lakehouse_staging and the development deployment must target ftd_lakehouse_api_test.

### **Implementation**

Create a verification procedure that:

1. Records the current state of both environments (current /version output, current commit on each branch).
2. Makes a small, identifiable change to the development branch that passes all CI tests (e.g., a version bump or a comment in a non-functional file).
3. Pushes the change to the development branch and monitors the CI workflow to completion (success).
4. Monitors the deploy workflow: verifies CI passed gate, deploy-development job runs, deploy-staging job is skipped.
5. Queries /version on ftd-test via IAP tunnel and confirms the response matches the pushed commit SHA, branch, and message, with environment: "development".
6. Queries /version on ftd-staging and confirms it still shows the previous staging revision (unchanged).
7. Repeats steps 2-6 for the staging branch, verifying CI passes, deploy-staging runs, deploy-development skipped, and ftd-staging shows the new revision while ftd-test remains unchanged.
8. Tests the failure gate: introduces a breaking change (e.g., syntax error in a test file) to a feature branch, opens a PR to rawdataingestion, verifies CI fails, and verifies no deployment is triggered.
9. Verifies that the version.json file on each VM contains the expected metadata and is readable by the application.
10. Verifies that GitHub Actions workflow history shows the complete chain: commit → CI run → deploy run → success.

### **Error handling**

Verification failures must be reported with specific evidence: which environment was expected to update, which actually updated, what the /version endpoint returned vs. what was expected, what the workflow logs show. If the /version endpoint is unavailable or returns stale data, the verification must fail — this is a traceability failure, not a transient issue. If the workflow succeeds but the wrong environment is updated, this is a critical mapping failure that must be reported immediately. If CI fails but deployment still proceeds, this is a gate failure that must be reported immediately.

Infrastructure failures during verification (VM unreachable, database unavailable, IAP tunnel broken) must be reported as infrastructure blockers, not as verification failures. The agent must not retry indefinitely or modify the verification criteria to pass.

### **Developer responsibilities**

The developer must approve the verification procedure before execution. The developer must be available to resolve infrastructure blockers (VM issues, network issues, credential issues) that prevent verification. The developer must review the final verification report and approve Layer Four completion.

### **IDE agent responsibilities**

The IDE agent may execute the verification procedure, collect the evidence, and produce the verification report. The agent may not make changes to the workflows, VMs, or application code during verification — any issue discovered must be reported, not fixed inline. The agent must stop after producing the verification report.

### **Hard stop**

Under no circumstances may the agent consider Layer Four complete without successful verification of both branch-to-environment mappings, the CI gate, and the failure gate. The agent must not modify the verification criteria to accommodate failures. The agent must not use manual deployment steps to fake a successful verification. The agent must not skip the failure gate test (broken CI blocks deploy). If the verification cannot be completed due to infrastructure issues, stop and report the blocker.

## **FINAL LAYER FOUR DEFINITION OF DONE**

Layer Four is complete only when the repository has a clear, enforced, and verified CI/CD pipeline: the CI workflow runs on pushes to both rawdataingestion and staging branches, validates code through lint/type-check (if configured), unit tests, integration tests (where database credentials exist), and frontend build, and fails fast on any stage failure; the deploy workflow is gated by CI success, splits into two mutually exclusive branch-gated jobs (deploy-development for rawdataingestion → ftd-test/ftd_lakehouse_api_test, deploy-staging for staging → ftd-staging/ftd_lakehouse_staging), each job writes version.json atomically during deployment, the /version endpoint on each environment serves this metadata accurately; a developer can answer "what commit is running on staging?" and "what caused that version to get deployed?" by querying the /version endpoint or inspecting the GitHub Actions workflow history — without manual VM investigation; a broken CI run blocks deployment; the complete chain (commit → CI → deploy → verified) is visible in GitHub Actions history.

The resulting architecture must make Git history the source of truth for environment state, with CI as the quality gate. The completion of Layer Four does not authorize work on Layer Five. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.