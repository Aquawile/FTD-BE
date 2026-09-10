# LAYER THREE — GIT BRANCH TO ENVIRONMENT WORKFLOW

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Three after completion of Major Layer Two. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Two is complete. Layer Three is a new architectural phase. The purpose of this phase is to establish a deliberate, traceable, and automated relationship between Git branches and deployed environments. The desired architectural direction is: a developer pushes to a specific branch, the corresponding CI/CD pipeline executes, and the resulting deployment lands in the correct environment with full revision metadata recorded. The branch name alone must determine which environment receives the deployment — no manual intervention, no arbitrary workflow dispatch overrides, no ambiguity about what is running where.

The agent must begin by creating or using a dedicated Layer Three working branch derived from the correct completed Layer Two revision. The agent must never push directly to main under any circumstance. The agent must not rewrite or force-push shared history. The agent must preserve the successful Layer Two CI/CD behavior unless a concrete Layer Three requirement makes a change unavoidable. Any such change must be isolated, explained, tested, and kept within the scope of Layer Three.

The implementation must remain deliberately narrow. The concrete domain is the existing GitHub Actions deployment workflow and the two target environments: the development VM (`ftd-test`) and a new staging VM that must be provisioned as part of this layer. The agent must not implement or prepare feature flags, blue-green deployments, canary releases, rollback automation, or any deployment sophistication beyond the branch-to-environment mapping. The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required mapping.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Infrastructure work must use the project's existing GCP provisioning scripts, Terraform if present, or the established `gcloud` command patterns. Do not introduce a competing infrastructure-as-code tool, deployment framework, GitOps controller, or environment management system merely because another tool is familiar.

Error handling is part of implementation, not an afterthought. Every deployment boundary must account for unavailable target environments, failed provisioning, credential mismatches, network connectivity failures, health check timeouts, and rollback scenarios according to the project's existing conventions. Deployment-specific failures must not leak arbitrary internal details to developers or consumers. Failed deployments must leave environments in a known state. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode production credentials, expose any environment publicly, modify production databases, delete existing deployment behavior to simplify implementation, or create mock deployment behavior in place of required integration verification. If a deployment cannot run because infrastructure is unavailable, the agent must report the infrastructure boundary rather than disguising it as a passing deployment.

The developer is the authority for infrastructure provisioning, credential approval, environment selection, branch naming conventions, and architectural deviations. The IDE agent is responsible for repository inspection, workflow implementation, test construction, execution, and diagnosis within the approved plan. Whenever an operation could mutate a real environment, the agent must first establish that the target is the correct isolated environment for the branch being deployed. If that cannot be proven, the operation must not proceed.

## **SUBLAYER 3.1 — ESTABLISH THE BRANCH-TO-ENVIRONMENT MAPPING**

### **Instruction**

The objective of Sublayer 3.1 is to define and codify the exact mapping between Git branches and deployment targets. The agent must first inspect the existing repository for branch naming conventions, the current GitHub Actions workflow structure, the existing deployment jobs, and any environment-specific configuration already present. The investigation must be narrow and purposeful: determine what branches currently exist, what the current `deploy.yml` workflow triggers on, what environments are currently deployed to, and what gaps exist between the current state and the required two-environment model.

The resulting architecture must make the branch the single source of truth for deployment routing. A push to the development branch must trigger the development pipeline and deploy exclusively to the development environment. A push to the staging branch must trigger the staging pipeline and deploy exclusively to the staging environment. No workflow dispatch input, no manual approval gate, no conditional logic based on commit message keywords shall override this mapping. The branch name alone determines the target.

The agent must preserve the existing deployment technology if it is already working. The current `deploy.yml` uses `gcloud compute ssh` with IAP tunneling, `gcloud compute scp` for file sync, and direct VM process management via `start_app.sh`. This pattern must be extended to the staging environment rather than replaced. Do not migrate to Cloud Deploy, Cloud Run, Kubernetes, or any other deployment platform during this sublayer. The goal is a clean branch-to-environment mapping, not a technology replacement.

### **Tools to use and why**

Use IDE file search and symbol navigation first to locate the GitHub Actions workflow file (`.github/workflows/deploy.yml`), any environment configuration files, the existing provisioning scripts for `ftd-test`, and any documentation about branch strategies. Use the terminal to inspect the current workflow triggers, job conditions, and deployment steps. Use Git log and branch listing to understand the current branch topology. Use `gcloud` commands to verify the current VM inventory and their configurations.

Use the project's existing provisioning scripts (`sec/scripts/provision_vm.sh` as a reference pattern) rather than writing new infrastructure code from scratch. Use the existing `gcloud` authentication pattern (Workload Identity) for any new automation. Do not install packages globally. If a dependency is missing, determine whether it is already declared in the project's dependency manifest before adding anything.

### **Implementation**

Implement the branch-to-environment mapping by modifying the GitHub Actions workflow to route deployments based on the triggering branch. The development branch (to be determined from existing conventions — likely `rawdataingestion` or a new dedicated branch) shall map to the existing `ftd-test` VM. The staging branch (to be determined — likely `staging` or `staging-dev`) shall map to a new staging VM that must be provisioned with identical specifications to `ftd-test` but with a distinct name, IP, and environment identifier.

The workflow must contain two mutually exclusive deployment jobs, each gated by a branch filter. The development job triggers only on pushes to the development branch. The staging job triggers only on pushes to the staging branch. Both jobs must use the same deployment steps (stop process, sync code, install dependencies, start process, verify health) but target different VMs with different environment variables where appropriate (database name, environment label, etc.).

Each deployment job must record the deployed revision (commit SHA, branch name, commit message, timestamp) in a persistent, queryable location accessible from the deployed environment — for example, a version endpoint (`/version`) that returns this metadata, or a file written to the VM that the application reads at startup. This recording must happen atomically as part of the deployment job, not as a separate manual step.

### **Error handling**

Branch mapping failures must be caught at the workflow level and translated into clear CI failures. A push to an unrecognized branch must fail the workflow with an explicit message indicating that no deployment mapping exists for that branch, rather than silently succeeding with no deployment. Workflow dispatch manual triggers must be restricted or removed if they bypass the branch mapping. If the target VM for a branch is unavailable, the deployment job must fail with a clear infrastructure error, not proceed to deploy to the wrong environment. Credential failures for the staging VM must be reported as configuration errors, not masked by falling back to development credentials.

### **Developer responsibilities**

The developer must approve the final branch names for development and staging before the workflow is modified. The developer must provision or approve the provisioning of the staging VM with the correct specifications, network placement, and IAM configuration. The developer must provide or approve the staging environment's database credentials and ensure they point to an isolated staging database (not development, not production). The developer must verify that the staging VM's firewall rules, IAP access, and service account permissions mirror the development VM's configuration.

### **IDE agent responsibilities**

The IDE agent may inspect the repository, modify the GitHub Actions workflow, create or update provisioning scripts for the staging VM, implement the revision recording mechanism, and create tests that verify the branch mapping logic. The agent may not independently provision cloud resources, select branch names, or modify production infrastructure. The agent must verify that the mapping works by simulating or triggering deployments from both branches in a controlled manner.

### **Hard stop**

Under no circumstances may the agent create a single workflow job that conditionally deploys to different environments based on runtime logic, implement feature flags or environment variables to switch environments within a single deployment, hardcode VM names or IPs in the workflow without parameterization, expose the staging environment publicly, share databases between development and staging, or continue into the staging environment provisioning details. If the branch mapping cannot be established through the existing workflow architecture, stop and report.

## **SUBLAYER 3.2 — PROVISION THE STAGING ENVIRONMENT**

### **Instruction**

The objective of Sublayer 3.2 is to provision a staging VM that is a faithful replica of the development VM in specification, configuration, and access model, but logically and physically isolated. The agent must first inspect the existing provisioning scripts, VM specifications, firewall rules, IAP configuration, service account assignments, and startup procedures for `ftd-test`. The investigation must be narrow and purposeful: determine the exact machine type, disk size, OS image, network tags, service account, IAP tunnel configuration, firewall rules, and startup script content that make `ftd-test` functional.

The resulting staging VM must be created with identical specifications: same machine type (e2-medium or equivalent), same zone (`us-west2-a`), same OS (Debian 12), same disk configuration, same service account with same IAM roles, same IAP tunnel access, same firewall rule membership, and same startup script pattern. The staging VM must have a distinct name (e.g., `ftd-staging`), distinct internal IP, distinct external IP, and must reside in the same VPC but be addressable independently. The staging VM must not share any persistent state with the development VM — no shared disks, no shared databases, no shared file systems.

The agent must use the existing provisioning script pattern (`sec/scripts/provision_vm.sh`) as the authoritative template. Do not write a new provisioning approach from scratch. If the existing script is parameterizable, parameterize it. If it is hardcoded for `ftd-test`, create a staging-specific variant that follows the same pattern. The provisioning must be idempotent — running it multiple times must not create duplicate resources or fail catastrophically.

### **Tools to use and why**

Use the existing `sec/scripts/provision_vm.sh` as the primary reference for VM creation parameters. Use `gcloud compute instances describe` on `ftd-test` to capture the exact specification. Use `gcloud compute firewall-rules list` and `gcloud compute instances get-iam-policy` to capture the network and IAM configuration. Use the terminal to execute the provisioning commands and verify the resulting VM state. Use the existing `start_app.sh` deployment verification pattern to confirm the staging VM can receive and run the application.

Use the project's existing GCP authentication (Workload Identity for CI, `gcloud` CLI for manual operations). Do not introduce Terraform, Pulumi, or any other infrastructure-as-code tool. The provisioning must be achievable via the existing `gcloud` command patterns used by the project.

### **Implementation**

Create a staging VM provisioning script (e.g., `scripts/provision_staging_vm.sh` or a parameterized version of the existing script) that creates `ftd-staging` in `us-west2-a` with the exact same specifications as `ftd-test`. The script must:

1. Create the VM with the same machine type, boot disk, OS image, and service account.
2. Attach the same network tags to inherit the same firewall rules (specifically the IAP SSH access rule).
3. Configure the same metadata (startup script, SSH keys, etc.) pattern.
4. Wait for the VM to reach `RUNNING` state and for the SSH daemon to be accessible via IAP.
5. Verify the VM can be reached via `gcloud compute ssh --tunnel-through-iap`.
6. Install the same base dependencies (Python 3.13, venv, git, curl).
7. Create the same directory structure (`/home/isabellabutera/app`, `/home/isabellabutera/frontend`).
8. Place the same `start_app.sh` script with staging-specific environment variables.
9. Verify the VM can connect to the staging PostgreSQL database (internal IP of `ftd-postgres-vm`, staging database name).

The staging VM must use a distinct database — `ftd_lakehouse_staging` (to be created on `ftd-postgres-vm`) — with the same schema as the development database but completely isolated data. The `start_app.sh` on the staging VM must set `PGDATABASE=ftd_lakehouse_staging` and use staging-specific credentials.

### **Error handling**

Provisioning failures must be caught at each step and reported with specific context (which `gcloud` command failed, what resource was being created, what the error message was). If the VM creation succeeds but SSH/IAP verification fails, the script must not leave a running VM that cannot be accessed — it must either retry with exponential backoff or clean up and report the failure. If the staging database does not exist or is not accessible, the provisioning must fail fast with a clear message rather than proceeding with a broken configuration. Firewall rule attachment failures must be reported as network configuration errors.

### **Developer responsibilities**

The developer must approve the staging VM name, machine type, and zone before provisioning. The developer must create or approve the creation of the staging database (`ftd_lakehouse_staging`) on `ftd-postgres-vm` with the correct schema and user permissions. The developer must provide the staging database credentials through the appropriate secret mechanism (GitHub Actions secret for CI, VM-local file for runtime). The developer must verify that the staging VM's network placement allows it to reach the PostgreSQL VM on the internal IP.

### **IDE agent responsibilities**

The IDE agent may create the provisioning script, execute it to create the staging VM, verify the VM's connectivity and configuration, and document the provisioning steps. The agent may not independently create databases, modify firewall rules beyond attaching existing tags, or assign IAM roles beyond what the existing pattern uses. The agent must report the provisioning outcome (success/failure, VM details, any deviations from the development VM spec) to the developer for approval.

### **Hard stop**

Under no circumstances may the agent modify the existing `ftd-test` VM, share the development database with staging, use the development VM's credentials for staging, create the staging VM in a different VPC or zone without explicit approval, implement the staging VM provisioning as a manual one-off rather than a repeatable script, or continue into the deployment workflow integration. If the staging environment cannot be provisioned to match the development environment's specification, stop and report.

## **SUBLAYER 3.3 — INTEGRATE STAGING INTO THE DEPLOYMENT WORKFLOW**

### **Instruction**

The objective of Sublayer 3.3 is to integrate the newly provisioned staging environment into the GitHub Actions deployment workflow so that pushes to the staging branch automatically deploy to the staging VM with the same reliability and verification as the development deployment. The agent must first inspect the current `deploy.yml` workflow structure, the existing "Deploy Application to ftd-test" job, its steps, its success criteria, and its failure modes. The investigation must be narrow and purposeful: determine how to replicate the job for staging with the correct branch filter, VM target, environment variables, and health checks.

The resulting workflow must contain two deployment jobs that are structurally identical but parameterized for their respective environments. Both jobs must execute the same sequence: start target VM, wait for SSH readiness, stop existing application process, clean stale files, sync backend code, sync dependencies, ensure virtual environment, install dependencies, build frontend, deploy frontend assets, start application with environment-specific variables, wait for health endpoint, record deployed revision. The only differences between the jobs must be the branch filter, the target VM name, the target database name, and any environment-specific labels.

The workflow must enforce that the development job runs only for the development branch and the staging job runs only for the staging branch. This must be implemented using GitHub Actions' `if` conditions on the job level, not by relying on step-level conditions within a shared job. The jobs must be mutually exclusive — a single push must never trigger both deployments.

Each deployment job must write deployment metadata (commit SHA, branch, commit message, timestamp, workflow run ID) to a consistent location that the running application can serve. The recommended approach is to write a `version.json` file to the VM during deployment that the application's `/version` endpoint reads, or to set environment variables that the application exposes via `/version`. This metadata must be written atomically as part of the deployment job before the health check passes.

### **Tools to use and why**

Use the existing `deploy.yml` as the authoritative reference for deployment steps, timing, and verification patterns. Use the GitHub Actions workflow syntax reference for job-level `if` conditions, matrix strategies, and environment variable interpolation. Use the terminal to validate the workflow YAML syntax and to test the workflow by pushing to the respective branches (or using `workflow_dispatch` with the correct branch context). Use the existing health check pattern (`curl -s http://127.0.0.1:8000/health`) as the verification standard.

Use the project's existing secret management pattern (GitHub Actions secrets for credentials, injected at runtime). Do not hardcode any credentials, IPs, or passwords in the workflow file. Use the existing `gcloud` command patterns for SSH, SCP, and command execution via IAP tunnel.

### **Implementation**

Modify `.github/workflows/deploy.yml` to contain two deployment jobs under the `deploy` job graph:

1. **`deploy-development`** job:
   - `if: github.ref == 'refs/heads/<development-branch-name>'`
   - Targets `ftd-test` VM
   - Sets `PGDATABASE=ftd_lakehouse_api_test`
   - Uses development credentials from GitHub secrets
   - Writes `version.json` with `environment: "development"`

2. **`deploy-staging`** job:
   - `if: github.ref == 'refs/heads/<staging-branch-name>'`
   - Targets `ftd-staging` VM
   - Sets `PGDATABASE=ftd_lakehouse_staging`
   - Uses staging credentials from GitHub secrets
   - Writes `version.json` with `environment: "staging"`

Both jobs must use the same step sequence, parameterized via job-level environment variables or a reusable workflow call if GitHub Actions supports it cleanly. The `version.json` must be written to a known path on the VM (e.g., `/home/isabellabutera/version.json`) and the FastAPI application must be updated to read this file and serve it at `/version` (or the existing `/version` endpoint must be enhanced to include this metadata).

The workflow must remove or restrict the existing `workflow_dispatch` trigger for application deployment unless it includes a required input that specifies the target environment (development or staging) and validates it against the branch mapping. Arbitrary manual deployments that bypass the branch mapping must not be possible.

### **Error handling**

Workflow failures must be specific to the failing job and environment. A failure in `deploy-development` must not block or mask a concurrent `deploy-staging` run (though they should be mutually exclusive by branch). Health check failures must include the target environment name in the error message. SSH readiness timeout must include the VM name. Credential injection failures must identify which environment's secrets were missing. The workflow must fail fast on any step failure — no continuation past a failed step.

If the `version.json` write fails, the deployment must be considered failed even if the health check passes, because traceability is a hard requirement. The health check must verify not only that the application responds with `{"status":"ok"}` but also that the `/version` endpoint returns the expected commit SHA and environment label.

### **Developer responsibilities**

The developer must review the modified workflow file before it is committed. The developer must create the staging-specific GitHub Actions secrets (e.g., `FTD_STAGING_PG_PASSWORD`, `FTD_STAGING_FIREBASE_KEY` if different from development) and verify they are accessible to the workflow. The developer must approve the branch names used in the `if` conditions. The developer must verify that the `/version` endpoint returns the correct metadata after a test deployment to each environment.

### **IDE agent responsibilities**

The IDE agent may modify the workflow file, implement the `/version` endpoint enhancement, create the `version.json` writing step, and test the workflow by triggering deployments from both branches. The agent may not create GitHub Actions secrets, modify branch protection rules, or change the workflow's authentication mechanism. The agent must verify that a push to the development branch deploys only to `ftd-test` and a push to the staging branch deploys only to `ftd-staging`.

### **Hard stop**

Under no circumstances may the agent merge the two deployment jobs into a single job with conditional logic, implement the version recording as a separate post-deployment step, allow `workflow_dispatch` to deploy to an environment without specifying which one, deploy to staging from the development branch or vice versa, share the same `version.json` path between environments without environment identification, or continue into the verification and traceability layer. If the workflow cannot be cleanly split into two branch-gated jobs, stop and report.

## **SUBLAYER 3.4 — VERIFY BRANCH-TO-ENVIRONMENT TRACEABILITY**

### **Instruction**

The objective of Sublayer 3.4 is to prove that the complete branch-to-environment workflow functions correctly and provides the required traceability. The verification must demonstrate that: a push to the development branch results in a deployment to `ftd-test` with the correct revision metadata; a push to the staging branch results in a deployment to `ftd-staging` with the correct revision metadata; the `/version` endpoint on each environment returns the commit SHA, branch name, commit message, timestamp, and environment label that match the triggering push; no cross-deployment occurs (development branch never deploys to staging, staging branch never deploys to development); and the deployment history is queryable without manual VM inspection.

The verification must distinguish between automated CI/CD deployments and any manual interventions. The test must exercise the actual GitHub Actions workflow, not a simulated or mocked deployment. The test must use the actual VMs, actual databases, and actual network paths.

### **Tools to use and why**

Use the existing GitHub Actions infrastructure to trigger real deployments by pushing test commits to the development and staging branches. Use the `gh` CLI to monitor workflow runs, inspect logs, and verify job outcomes. Use `curl` via IAP tunnels to query the `/version` and `/health` endpoints on both environments after deployment. Use the terminal to verify the `version.json` file exists on each VM with the correct content. Use Git commands to verify the commit history matches the deployed revisions.

Use the project's existing IAP tunnel patterns for accessing the application endpoints. Do not create new access methods. Use the existing test databases — the staging deployment must target `ftd_lakehouse_staging` and the development deployment must target `ftd_lakehouse_api_test`.

### **Implementation**

Create a verification procedure that:

1. Records the current state of both environments (current `/version` output, current commit on each branch).
2. Makes a small, identifiable change to the development branch (e.g., a version bump or a comment in a non-functional file).
3. Pushes the change to the development branch and monitors the workflow run to completion.
4. Verifies the `deploy-development` job succeeded and `deploy-staging` was not triggered.
5. Queries `/version` on `ftd-test` via IAP tunnel and confirms the response matches the pushed commit SHA, branch, and message, with `environment: "development"`.
6. Queries `/version` on `ftd-staging` and confirms it still shows the previous staging revision (unchanged).
7. Repeats steps 2-6 for the staging branch, verifying `deploy-staging` runs, `deploy-development` does not, and `ftd-staging` shows the new revision while `ftd-test` remains unchanged.
8. Verifies that the `version.json` file on each VM contains the expected metadata and is readable by the application.

The verification must also test the negative case: a push to a branch that is neither development nor staging (e.g., a feature branch) must result in a workflow failure with a clear "no deployment mapping for this branch" message, not a silent success.

### **Error handling**

Verification failures must be reported with specific evidence: which environment was expected to update, which actually updated, what the `/version` endpoint returned vs. what was expected, what the workflow logs show. If the `/version` endpoint is unavailable or returns stale data, the verification must fail — this is a traceability failure, not a transient issue. If the workflow succeeds but the wrong environment is updated, this is a critical mapping failure that must be reported immediately.

Infrastructure failures during verification (VM unreachable, database unavailable, IAP tunnel broken) must be reported as infrastructure blockers, not as verification failures. The agent must not retry indefinitely or modify the verification criteria to pass.

### **Developer responsibilities**

The developer must approve the verification procedure before execution. The developer must be available to resolve infrastructure blockers (VM issues, network issues, credential issues) that prevent verification. The developer must review the final verification report and approve Layer Three completion.

### **IDE agent responsibilities**

The IDE agent may execute the verification procedure, collect the evidence, and produce the verification report. The agent may not make changes to the workflow, VMs, or application code during verification — any issue discovered must be reported, not fixed inline. The agent must stop after producing the verification report.

### **Hard stop**

Under no circumstances may the agent consider Layer Three complete without successful verification of both branch-to-environment mappings, modify the verification criteria to accommodate failures, use manual deployment steps to fake a successful verification, skip the negative case test (unknown branch), or continue into Layer Four. If the verification cannot be completed due to infrastructure issues, stop and report the blocker.

## **FINAL LAYER THREE DEFINITION OF DONE**

Layer Three is complete only when the repository has a clear, enforced, and verified mapping between Git branches and deployed environments: the development branch deploys exclusively to the development environment (`ftd-test` with `ftd_lakehouse_api_test`), the staging branch deploys exclusively to the staging environment (`ftd-staging` with `ftd_lakehouse_staging`), each deployment records its revision metadata atomically, the `/version` endpoint on each environment serves this metadata accurately, and a developer can answer "what commit is running on staging?" and "what caused that version to get deployed?" by querying the `/version` endpoint or inspecting the GitHub Actions workflow history — without manual VM investigation.

The resulting architecture must make Git history the source of truth for environment state. The completion of Layer Three does not authorize work on Layer Four. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.