# LAYER FIVE — DEPLOY AND VALIDATE THE STAGING VM ARCHITECTURE

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Five after completion of Major Layer Four. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Four is complete. Layer Five is a new architectural phase. The purpose of this phase is to deploy and validate a complete multi-VM staging environment that mirrors the intended production architecture: a Web VM (React frontend), a Backend VM (FastAPI application), and a Database VM (PostgreSQL) — each on dedicated infrastructure, connected via private VPC, with the CI/CD pipeline correctly routing artifacts to their respective targets. The desired architectural direction is: GitHub Actions → Web VM (static assets), Backend VM (application code), Database VM (migrations only) → verified inter-VM connectivity and service health.

The agent must begin by creating or using a dedicated Layer Five working branch derived from the correct completed Layer Four revision. The agent must never push directly to main under any circumstance. The agent must not rewrite or force-push shared history. The agent must preserve the successful Layer Four CI/CD behavior unless a concrete Layer Five requirement makes a change unavoidable. Any such change must be isolated, explained, tested, and kept within the scope of Layer Five.

The implementation must remain deliberately narrow. The concrete domain is the staging environment infrastructure provisioning, the deploy workflow extension to target multiple VMs, the database migration strategy for staging, and the end-to-end verification of the multi-VM architecture. The agent must not implement or prepare production infrastructure, blue-green deployments, canary releases, load balancing, auto-scaling, or any operational sophistication beyond the staging environment. The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required multi-VM deployment.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Infrastructure work must use the project's existing GCP provisioning scripts, `gcloud` command patterns, and Workload Identity authentication. Do not introduce a competing infrastructure-as-code tool, deployment framework, configuration management system, or service mesh merely because another tool is familiar.

Error handling is part of implementation, not an afterthought. Every deployment boundary must account for VM provisioning failures, SSH/IAP connectivity issues, database migration failures, service startup timeouts, inter-VM network connectivity failures, environment variable mismatches, and permission errors. Deployment-specific failures must not leak arbitrary internal details to consumers. Failed deployments must leave environments in a known state. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode production credentials, expose any environment publicly, modify production databases, delete existing deployment behavior to simplify implementation, or create mock deployment behavior in place of required integration verification. If a deployment cannot run because infrastructure is unavailable, the agent must report the infrastructure boundary rather than disguising it as a passing deployment.

The developer is the authority for infrastructure provisioning, credential approval, environment selection, branch strategy, and architectural deviations. The IDE agent is responsible for repository inspection, workflow implementation, test construction, execution, and diagnosis within the approved plan. Whenever an operation could mutate a real environment, the agent must first establish that the target is the correct isolated environment for the branch being deployed. If that cannot be proven, the operation must not proceed.

## **SUBLAYER 5.1 — PROVISION STAGING WEB VM AND BACKEND VM**

### **Instruction**

The objective of Sublayer 5.1 is to provision two dedicated staging VMs that separate the frontend serving layer from the application logic layer: a Web VM (`ftd-staging-web`) to serve the React static assets, and a Backend VM (`ftd-staging-api`) to run the FastAPI application. The agent must first inspect the existing `ftd-test` VM specification and the current deploy workflow to understand what capabilities each VM must have. The investigation must be narrow and purposeful: determine the exact machine type, disk size, OS image, network tags, service account, IAP tunnel configuration, firewall rules, and startup procedures for the current monolithic `ftd-test`, then split those responsibilities across two new VMs.

The resulting architecture must separate concerns cleanly: the Web VM serves only static files (React build output) via a lightweight HTTP server (nginx or Python http.server), accepts traffic on port 80/443 (or localhost if behind IAP), and forwards API requests to the Backend VM via internal VPC connectivity. The Backend VM runs the FastAPI application bound to `127.0.0.1:8000`, connects to the PostgreSQL database on the Database VM via internal IP, and exposes no public ports. Both VMs must be accessible only via IAP/SSH tunneling — no public SSH, no public HTTP. The Web VM must have the `http-server` and `https-server` network tags for IAP access; the Backend VM must have the same tags for IAP SSH but no HTTP tags.

The agent must use the existing provisioning script pattern (`scripts/provision_staging_vm.sh`) as the authoritative template. Do not write new provisioning logic from scratch. Parameterize the existing script or create staging-specific variants for `ftd-staging-web` and `ftd-staging-api`. The provisioning must be idempotent — running it multiple times must not create duplicate resources or fail catastrophically. Each VM must be created in `us-west2-a` with the same machine type as `ftd-test` (e2-medium), same Debian 12 OS, same service account (`767713105-compute@developer.gserviceaccount.com`), same IAP SSH firewall rule membership, and same scopes.

### **Tools to use and why**

Use the existing `scripts/provision_staging_vm.sh` as the primary reference for VM creation parameters. Use `gcloud compute instances describe` on `ftd-test` to capture the exact specification. Use `gcloud compute firewall-rules list` and `gcloud compute instances get-iam-policy` to capture the network and IAM configuration. Use the terminal to execute the provisioning commands and verify the resulting VM state. Use the existing `start_app.sh` deployment verification pattern to confirm each VM can receive and run its assigned component.

Use the project's existing GCP authentication (Workload Identity for CI, `gcloud` CLI for manual operations). Do not introduce Terraform, Pulumi, or any other infrastructure-as-code tool. The provisioning must be achievable via the existing `gcloud` command patterns used by the project.

### **Implementation**

Create a parameterized provisioning script (e.g., `scripts/provision_staging_vms.sh`) that creates both VMs:

1. **Web VM (`ftd-staging-web`)**:
   - Machine type: e2-medium, zone: us-west2-a, Debian 12, 30GB boot disk
   - Service account: `767713105-compute@developer.gserviceaccount.com`
   - Scopes: devstorage.read_only, logging.write, monitoring.write, service.management.readonly, servicecontrol, trace.append
   - Network tags: `http-server,https-server` (for IAP SSH access)
   - Install: nginx (or Python http.server), Python 3.13, git, curl
   - Directory structure: `/home/isabellabutera/frontend/dist/`
   - Startup script: serves static files on port 8080, proxies `/api/*` to `ftd-staging-api:8000` via internal IP

2. **Backend VM (`ftd-staging-api`)**:
   - Machine type: e2-medium, zone: us-west2-a, Debian 12, 30GB boot disk
   - Service account: same as above
   - Scopes: same plus secretmanager (for database credentials)
   - Network tags: `http-server,https-server` (for IAP SSH access only)
   - Install: Python 3.13, venv, git, curl, postgresql-client
   - Directory structure: `/home/isabellabutera/app/`, `/home/isabellabutera/app/app/`
   - Startup script: `start_app.sh` (same pattern as `ftd-test`, with staging database env vars)

Both VMs must be verified for:
- SSH accessibility via IAP (`gcloud compute ssh --tunnel-through-iap`)
- Internal VPC connectivity between Web VM → Backend VM (port 8000)
- Internal VPC connectivity from Backend VM → Database VM (port 5432 on `10.168.0.3`)
- Correct environment variables set in their respective startup scripts

### **Error handling**

Provisioning failures must be caught at each step and reported with specific context (which `gcloud` command failed, what resource was being created, what the error message was). If a VM creation succeeds but SSH/IAP verification fails, the script must not leave a running VM that cannot be accessed — it must either retry with exponential backoff or clean up and report the failure. If inter-VM connectivity fails (Web VM cannot reach Backend VM, or Backend VM cannot reach Database VM), the provisioning must fail fast with a clear network diagnostics message rather than proceeding with a broken configuration. Firewall rule attachment failures must be reported as network configuration errors.

### **Developer responsibilities**

The developer must approve the VM names, machine types, and zone before provisioning. The developer must verify that the VPC allows internal connectivity between the three VMs (Web → Backend on 8000, Backend → Database on 5432). The developer must approve the Web VM's reverse proxy configuration (nginx vs Python http.server). The developer must provide or approve the staging database credentials for the Backend VM's startup script.

### **IDE agent responsibilities**

The IDE agent may create the provisioning script, execute it to create both VMs, verify the VMs' connectivity and configuration, and document the provisioning steps. The agent may not independently modify firewall rules beyond attaching existing tags, or assign IAM roles beyond what the existing pattern uses. The agent must report the provisioning outcome (success/failure, VM details, any deviations from the `ftd-test` spec) to the developer for approval.

### **Hard stop**

Under no circumstances may the agent modify the existing `ftd-test` VM, expose the Backend VM's port 8000 publicly, share the Web VM's static serving with the Backend VM, create the VMs in a different VPC or zone without explicit approval, implement the provisioning as a manual one-off rather than a repeatable script, or continue into the deployment workflow integration. If the staging VMs cannot be provisioned to match the required architecture, stop and report.

## **SUBLAYER 5.2 — ESTABLISH DATABASE MIGRATION STRATEGY FOR STAGING**

### **Instruction**

The objective of Sublayer 5.2 is to define and implement a safe, repeatable database migration strategy for the staging environment that respects the critical constraint: **deployment does not mean recreating the database**. The staging database (`ftd_lakehouse_staging`) already exists with the foundation schema (migrations 001-005 applied in Layer 3.2). Future deployments must apply only incremental schema changes via the existing migration mechanism, never drop and recreate tables, never wipe existing data unless explicitly approved by the developer for a specific migration.

The agent must first inspect the existing migration system in the repository: the migration files in `app/auth/migrations/`, the naming convention (sequential numbering), the idempotency guarantees (IF NOT EXISTS, DROP IF EXISTS patterns), and how migrations are currently applied (manual `psql` execution via SSH). The investigation must be narrow and purposeful: determine how to automate migration application during staging deployment without risking data loss or schema drift.

The resulting strategy must integrate with the staging deploy workflow: when the `deploy-staging` job runs, it must apply any pending migrations to `ftd_lakehouse_staging` on the Database VM before starting the Backend VM's application. The migration step must be idempotent — running it multiple times with the same migration set must produce the same schema state. Migrations must be applied in sequence order (001, 002, 003...). The migration step must fail fast if any migration fails, and the deployment must not proceed to application startup until migrations succeed. The migration step must NOT run on the development environment unless explicitly triggered (development uses `ftd_lakehouse_api_test` which is managed separately).

The agent must preserve the existing migration files and naming convention. Do not introduce a new migration tool (Alembic, Flyway, etc.) — the existing sequential SQL file pattern is the authoritative mechanism. Do not modify existing migration files. New migrations may be added only if a concrete schema change is required for Layer Five functionality, and must follow the existing naming convention (next sequential number).

### **Tools to use and why**

Use the existing migration files in `app/auth/migrations/` as the authoritative reference for migration format and idempotency patterns. Use `gcloud compute ssh` with `--tunnel-through-iap` to execute migrations on the Database VM via the Backend VM (or directly if IAP tunnel to Database VM is available). Use the existing `psql` command pattern with `sudo -u postgres` for migration application. Use the terminal to verify migration state before and after application (`\dt`, `\d table_name`). Use Git diff to ensure no existing migration files are modified.

Use the project's existing `gcloud` command patterns and IAP tunneling. Do not introduce a new database migration runner or ORM migration system. The migration execution must be achievable via the existing SSH/IAP patterns used by the deploy workflow.

### **Implementation**

Create a migration application script (e.g., `scripts/apply_staging_migrations.sh`) that:

1. Discovers all migration files in `app/auth/migrations/` matching the pattern `NNN_*.sql`
2. Sorts them numerically by prefix
3. For each migration, executes it against `ftd_lakehouse_staging` on the Database VM via `gcloud compute ssh ftd-postgres-vm --tunnel-through-iap --command="sudo -u postgres psql -d ftd_lakehouse_staging -f /tmp/migration_NNN.sql"`
4. Tracks which migrations have been applied (via a migration tracking table in the database, or by checking schema state)
4. Fails fast on any migration error, with clear output showing which migration failed and the PostgreSQL error message

Integrate this script into the `deploy-staging` job in `.github/workflows/deploy.yml`:
- Add a step "Apply staging database migrations" before "Starting FastAPI"
- The step runs the migration script via the Backend VM (which has connectivity to Database VM) or directly via IAP tunnel to Database VM
- The step must complete successfully before the health check step runs

The migration script must be idempotent: it should check if a migration has already been applied (e.g., by querying a `schema_migrations` table or checking for the existence of tables/columns the migration creates) before attempting to apply it. If already applied, it logs "Migration NNN already applied, skipping" and continues.

### **Error handling**

Migration failures must be caught and reported with the specific migration file name, the PostgreSQL error message, and the SQL statement that failed. The deployment must not proceed to application startup if any migration fails. If a migration partially applies (some statements succeed, one fails), the script must not attempt to roll back automatically — it must fail and require human intervention to assess the schema state. The developer must be notified of the exact failure point.

If the migration tracking table does not exist, the script must create it as part of the first migration run (or as a bootstrap step). The tracking table must record: migration_id (NNN), applied_at (timestamp), success (boolean).

### **Developer responsibilities**

The developer must approve the migration application strategy before it is integrated into the deploy workflow. The developer must review any new migration files before they are added to the repository. The developer must verify that the staging database (`ftd_lakehouse_staging`) is the correct target and that the production database (`ftd_lakehouse`) is never touched by this automation. The developer must approve any manual intervention required for failed migrations.

### **IDE agent responsibilities**

The IDE agent may create the migration application script, integrate it into the deploy workflow, test it against the staging database, and document the migration process. The agent may not modify existing migration files, create new migrations without explicit developer approval, or run migrations against the production database. The agent must verify that migrations apply cleanly to a fresh staging database and to an already-migrated staging database (idempotency).

### **Hard stop**

Under no circumstances may the agent drop or recreate the staging database, apply migrations to the production database (`ftd_lakehouse`), introduce a new migration tool or framework, modify existing migration files, skip the migration step in the deploy workflow, or proceed to application startup if migrations fail. If the migration strategy cannot be implemented safely with the existing migration files, stop and report.

## **SUBLAYER 5.3 — EXTEND DEPLOY WORKFLOW FOR MULTI-VM STAGING**

### **Instruction**

The objective of Sublayer 5.3 is to extend the GitHub Actions deploy workflow (`.github/workflows/deploy.yml`) to correctly deploy to the three-VM staging architecture: Web VM (`ftd-staging-web`), Backend VM (`ftd-staging-api`), and Database VM (`ftd-postgres-vm` for migrations). The agent must first inspect the current `deploy-staging` job structure, which targets a single `ftd-staging` VM, and understand how to split the deployment steps across the three VMs while preserving the CI gate, version metadata recording, and health verification.

The resulting workflow must route artifacts correctly:
- React build artifacts (`context/figma_prototype/dist/`) → Web VM (`/home/isabellabutera/frontend/dist/`)
- Backend code (`app/`, `requirements.txt`) → Backend VM (`/home/isabellabutera/app/app/`, `/home/isabellabutera/requirements.txt`)
- Migration scripts (`app/auth/migrations/`) → applied to Database VM via migration script run from Backend VM or CI runner
- Startup scripts (`scripts/start_app.sh`, Web VM startup script) → respective VMs

The `deploy-staging` job must be restructured into a sequence of steps (or multiple jobs with `needs:`) that execute in the correct order:
1. Apply staging database migrations (Database VM)
2. Deploy backend code and start FastAPI (Backend VM)
3. Deploy frontend build and start static server (Web VM)
4. Verify end-to-end health: Web VM serves frontend, proxies API to Backend VM, Backend VM connects to Database VM

Each VM deployment must write its own `version.json` (or the workflow writes a combined version metadata accessible to both VMs). The health verification must check: Web VM serves `index.html` on port 8080, Web VM proxies `/api/health` to Backend VM's `/health`, Backend VM `/health` returns `{"status":"ok"}`, Backend VM `/version` returns correct metadata.

The `workflow_dispatch` input `target_environment: staging` must continue to work, triggering this full multi-VM deployment sequence.

### **Tools to use and why**

Use the existing `.github/workflows/deploy.yml` as the authoritative reference for deployment steps, timing, and verification patterns. Use the GitHub Actions workflow syntax reference for multi-job dependencies (`needs:`), step-level `if` conditions, and environment variable interpolation. Use the terminal to validate the workflow YAML syntax and to test the workflow by pushing to the `staging` branch. Use the existing health check pattern (`curl -s http://127.0.0.1:8000/health`) and the new Web VM health check pattern (`curl -s http://127.0.0.1:8080/` and `curl -s http://127.0.0.1:8080/api/health`).

Use the project's existing secret management pattern (GitHub Actions secrets for credentials, injected at runtime). Do not hardcode any credentials, IPs, or passwords in the workflow file. Use the existing `gcloud` command patterns for SSH, SCP, and command execution via IAP tunnel. Use the existing Workload Identity authentication.

### **Implementation**

Modify `.github/workflows/deploy.yml` to restructure the `deploy-staging` job (or split into multiple jobs):

1. **Job: `deploy-staging-migrations`** (runs first, no VM startup needed):
   - Runs on CI runner (or Backend VM via SSH)
   - Executes `scripts/apply_staging_migrations.sh` against `ftd_lakehouse_staging` on `ftd-postgres-vm`
   - Fails fast on migration error

2. **Job: `deploy-staging-backend`** (depends on `deploy-staging-migrations`):
   - Starts `ftd-staging-api` VM
   - Waits for SSH readiness via IAP
   - Syncs backend code, requirements.txt, startup script
   - Installs Python dependencies
   - Writes `version.json` to Backend VM
   - Starts FastAPI via `start_app.sh`
   - Verifies `/health` and `/version` endpoints on Backend VM

3. **Job: `deploy-staging-web`** (depends on `deploy-staging-backend`):
   - Starts `ftd-staging-web` VM
   - Waits for SSH readiness via IAP
   - Syncs React build (`dist/`) to Web VM
   - Deploys Web VM startup script (nginx config or Python http.server with proxy)
   - Starts static server
   - Verifies Web VM serves frontend and proxies `/api/*` to Backend VM

4. **Job: `deploy-staging-verify`** (depends on both backend and web):
   - Runs end-to-end health checks:
     - `curl http://ftd-staging-web:8080/` → returns HTML
     - `curl http://ftd-staging-web:8080/api/health` → returns `{"status":"ok"}` (proxied to Backend VM)
     - `curl http://ftd-staging-api:8000/version` → returns correct commit metadata

All jobs must use the same `if:` condition as current `deploy-staging` (branch `staging` or `workflow_dispatch` with `target_environment: staging`). All jobs must have `environment: staging` for GitHub Environments UI. The `needs: ci` gate must be preserved at the first job level.

### **Error handling**

Workflow failures must be specific to the failing job and VM. A failure in `deploy-staging-migrations` must block all downstream jobs. A failure in `deploy-staging-backend` must block `deploy-staging-web` and `deploy-staging-verify`. Health check failures must include the target VM name and endpoint in the error message. SSH readiness timeout must include the VM name. Credential injection failures must identify which environment's secrets were missing. The workflow must fail fast on any step failure — no continuation past a failed step.

If the Web VM cannot proxy to the Backend VM, the verification job must fail with a clear network connectivity error. If the Backend VM cannot connect to the Database VM, the backend deployment job must fail during health check with a clear database connectivity error.

### **Developer responsibilities**

The developer must review the modified workflow file before it is committed. The developer must verify that the Web VM's proxy configuration correctly forwards `/api/*` to the Backend VM's internal IP. The developer must approve the job ordering and dependencies. The developer must verify that the end-to-end health checks pass after a test deployment.

### **IDE agent responsibilities**

The IDE agent may modify the workflow file, create the Web VM startup script (nginx config or Python proxy server), create the migration application script, and test the workflow by triggering deployments from the `staging` branch. The agent may not create GitHub Actions secrets, modify branch protection rules, or change the workflow's authentication mechanism. The agent must verify that a push to the `staging` branch deploys correctly to all three VMs and passes end-to-end verification.

### **Hard stop**

Under no circumstances may the agent merge the multi-VM deployment into a single job with conditional logic, deploy backend code to the Web VM or frontend assets to the Backend VM, skip the migration step, skip the end-to-end verification step, allow `workflow_dispatch` to deploy to staging without specifying the correct environment, or continue into the verification layer. If the workflow cannot be cleanly structured for multi-VM deployment, stop and report.

## **SUBLAYER 5.4 — END-TO-END MULTI-VM STAGING VERIFICATION**

### **Instruction**

The objective of Sublayer 5.4 is to prove that the complete multi-VM staging architecture functions correctly and provides the required traceability and reliability. The verification must demonstrate that: a push to the `staging` branch triggers CI, CI passes, then the full multi-VM deploy sequence runs (migrations → backend → web → verify); the Web VM serves the React frontend on port 8080; the Web VM correctly proxies `/api/*` requests to the Backend VM on port 8000 via internal VPC connectivity; the Backend VM runs FastAPI, connects to the staging database on the Database VM, and serves `/health` and `/version` endpoints; the `/version` endpoint on the Backend VM (and proxied through Web VM) returns the commit SHA, branch name, commit message, timestamp, and environment label that match the triggering push; no cross-deployment occurs (staging branch never deploys to development VMs); a failed CI run blocks the entire staging deployment; the deployment history is queryable via GitHub Actions UI and `/version` endpoint without manual VM investigation.

The verification must distinguish between automated CI/CD deployments and any manual interventions. The test must exercise the actual GitHub Actions workflows, not simulated or mocked deployments. The test must use the actual VMs, actual databases, and actual network paths.

### **Tools to use and why**

Use the existing GitHub Actions infrastructure to trigger real deployments by pushing test commits to the `staging` branch. Use the `gh` CLI to monitor workflow runs, inspect logs, and verify job outcomes. Use `curl` via IAP tunnels to query the Web VM (port 8080) and Backend VM (port 8000) endpoints after deployment. Use the terminal to verify the `version.json` file exists on both VMs with the correct content. Use `gcloud compute ssh` to verify internal connectivity between VMs (Web VM → Backend VM on 8000, Backend VM → Database VM on 5432). Use Git commands to verify the commit history matches the deployed revisions.

Use the project's existing IAP tunnel patterns for accessing the application endpoints. Do not create new access methods. Use the existing staging database (`ftd_lakehouse_staging`) on `ftd-postgres-vm`.

### **Implementation**

Create a verification procedure that:

1. Records the current state of the staging environment (current `/version` output via Web VM proxy, current commit on `staging` branch).
2. Makes a small, identifiable change to the `staging` branch (e.g., a version bump or a comment in a non-functional file).
3. Pushes the change to the `staging` branch and monitors the CI workflow to completion (success).
4. Monitors the deploy workflow: verifies CI passed gate, `deploy-staging-migrations` runs, `deploy-staging-backend` runs, `deploy-staging-web` runs, `deploy-staging-verify` runs.
5. Queries the Web VM via IAP tunnel:
   - `curl http://ftd-staging-web:8080/` → returns HTML (React frontend)
   - `curl http://ftd-staging-web:8080/api/health` → returns `{"status":"ok"}` (proxied to Backend VM)
   - `curl http://ftd-staging-web:8080/api/version` → returns version metadata matching pushed commit
6. Queries the Backend VM directly via IAP tunnel:
   - `curl http://ftd-staging-api:8000/health` → returns `{"status":"ok"}`
   - `curl http://ftd-staging-api:8000/version` → returns version metadata matching pushed commit
7. Verifies the `version.json` file on both VMs contains the expected metadata and is readable by the application.
8. Verifies that the `staging` branch push did NOT trigger any development environment deployment (check `ftd-test` version unchanged).
9. Tests the failure gate: introduces a breaking change (e.g., syntax error in a test file) to a feature branch, opens a PR to `staging`, verifies CI fails, and verifies no staging deployment is triggered.
10. Verifies that GitHub Actions workflow history shows the complete chain: commit → CI run → migration run → backend deploy → web deploy → verify run → success.

### **Error handling**

Verification failures must be reported with specific evidence: which VM endpoint was expected to respond, which actually responded, what the response was vs. what was expected, what the workflow logs show. If the Web VM proxy to Backend VM fails, the verification must fail — this is an architecture failure, not a transient issue. If the workflow succeeds but the wrong VMs are updated, this is a critical routing failure that must be reported immediately. If CI fails but deployment still proceeds, this is a gate failure that must be reported immediately.

Infrastructure failures during verification (VM unreachable, database unavailable, IAP tunnel broken, inter-VM connectivity broken) must be reported as infrastructure blockers, not as verification failures. The agent must not retry indefinitely or modify the verification criteria to pass.

### **Developer responsibilities**

The developer must approve the verification procedure before execution. The developer must be available to resolve infrastructure blockers (VM issues, network issues, credential issues, proxy configuration issues) that prevent verification. The developer must review the final verification report and approve Layer Five completion.

### **IDE agent responsibilities**

The IDE agent may execute the verification procedure, collect the evidence, and produce the verification report. The agent may not make changes to the workflows, VMs, or application code during verification — any issue discovered must be reported, not fixed inline. The agent must stop after producing the verification report.

### **Hard stop**

Under no circumstances may the agent consider Layer Five complete without successful verification of the full multi-VM staging deployment, the proxy routing, the database connectivity, and the CI gate. The agent must not modify the verification criteria to accommodate failures. The agent must not use manual deployment steps to fake a successful verification. The agent must not skip the failure gate test (broken CI blocks deploy). If the verification cannot be completed due to infrastructure issues, stop and report the blocker.

## **FINAL LAYER FIVE DEFINITION OF DONE**

Layer Five is complete only when the staging environment operates as a true multi-VM architecture: the Web VM (`ftd-staging-web`) serves the React frontend on port 8080 and correctly proxies `/api/*` requests to the Backend VM (`ftd-staging-api`) on port 8000 via internal VPC connectivity; the Backend VM runs FastAPI bound to `127.0.0.1:8000`, connects to the staging database (`ftd_lakehouse_staging`) on the Database VM (`ftd-postgres-vm` internal IP `10.168.0.3`), and serves `/health` and `/version` endpoints with accurate deployment metadata; the CI/CD pipeline deploys the correct artifacts to each VM (migrations to Database VM, backend code to Backend VM, frontend build to Web VM), gates on CI success, applies database migrations safely without recreating the database, and verifies end-to-end health; a developer can answer "what commit is running on staging?" by querying the Web VM's `/api/version` endpoint or the Backend VM's `/version` endpoint, and "what caused that version to get deployed?" by inspecting the GitHub Actions workflow history — without manual VM investigation; a broken CI run blocks the entire staging deployment; the complete chain (commit → CI → migrations → backend deploy → web deploy → verified) is visible in GitHub Actions history.

The resulting architecture must make the staging environment a faithful replica of the intended production architecture (separate web, application, and database tiers), with the CI/CD pipeline as the sole deployment mechanism. The completion of Layer Five does not authorize work on Layer Six. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.