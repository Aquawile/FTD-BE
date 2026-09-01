# LAYER SEVEN — EXPOSE STAGING THROUGH GOOGLE CLOUD GATEWAY

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Seven after completion of Major Layer Six. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Six is complete. Layer Seven is a new architectural phase. The purpose of this phase is to expose the staging application to the public internet through Google Cloud Gateway while maintaining strict security boundaries. The desired architectural direction is: Internet → External Load Balancer → Google Cloud Gateway → Internal Load Balancer → Web VM (nginx) → Backend VM (FastAPI) → Database VM (PostgreSQL). The gateway must be infrastructure, not application logic. FastAPI remains the application's API layer; the gateway is infrastructure.

The agent must begin by creating or using a dedicated Layer Seven working branch derived from the correct completed Layer Six revision. The agent must never push directly to main under any circumstance. The agent must not rewrite or force-push shared history. The agent must preserve the successful Layer Six CI/CD behavior unless a concrete Layer Seven requirement makes a change unavoidable. Any such change must be isolated, explained, tested, and kept within the scope of Layer Seven.

The implementation must remain deliberately narrow. The concrete domain is the existing staging three-VM architecture (Web VM, Backend VM, Database VM) and the Google Cloud Gateway configuration required to expose it publicly. The agent must not implement or prepare production infrastructure, blue-green deployments, canary releases, WAF rules beyond basic requirements, custom authentication at the gateway layer, or any operational sophistication beyond exposing staging publicly. The agent must not invent missing architecture when existing repository code and infrastructure already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required public exposure.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Infrastructure work must use the project's existing GCP provisioning patterns, `gcloud` command patterns, and Workload Identity authentication. Do not introduce a competing infrastructure-as-code tool, gateway configuration framework, or service mesh merely because another tool is familiar.

Error handling is part of implementation, not an afterthought. Every gateway boundary must account for certificate provisioning failures, backend health check failures, certificate renewal issues, TLS termination problems, backend connection draining, and DDoS protection misconfiguration. Gateway failures must not leak arbitrary internal details to consumers. Failed gateway configurations must leave the existing staging environment accessible via IAP tunnels. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode production credentials, expose the Database VM publicly, modify the production database, delete existing staging behavior to simplify implementation, or create mock gateway behavior in place of required integration verification. If a gateway configuration cannot be applied because infrastructure is unavailable, the agent must report the infrastructure boundary rather than disguising it as a passing configuration.

The developer is the authority for infrastructure provisioning, certificate approval, DNS configuration, gateway feature selection, and architectural deviations. The IDE agent is responsible for repository inspection, gateway configuration, test construction, execution, and diagnosis within the approved plan. Whenever an operation could mutate a real gateway resource, the agent must first establish that the target is the staging environment. If that cannot be proven, the operation must not proceed.

## **SUBLAYER 7.1 — PREPARE FIREWALL AND NETWORK FOR GATEWAY ACCESS**

### **Instruction**

The objective of Sublayer 7.1 is to prepare the existing staging network and firewall rules to accept traffic from Google Cloud Gateway while preserving existing IAP-only access for administrative purposes. The agent must first inspect the existing VPC network, firewall rules, subnet configuration, and the current firewall rule that allows IAP SSH access (`allow-iap-ssh`). The investigation must be narrow and purposeful: determine the exact VPC network name, subnet ranges, existing firewall rules, and the current network tags applied to the Web VM (`ftd-staging-web`) and Backend VM (`ftd-staging-api`).

The resulting network configuration must allow Google Cloud Gateway to reach the Web VM on port 443 through an Internal Load Balancer, while preserving the existing IAP-only SSH access for administrative purposes. The existing `allow-iap-ssh` firewall rule (allowing TCP 22 from `35.235.240.0/20`) must remain unchanged. A new firewall rule must be created to allow traffic from the Internal Load Balancer's proxy-only subnet to the Web VM on port 443. The Internal Load Balancer's proxy-only subnet is `10.128.0.0/20` (or the specific proxy-only subnet assigned by GCP). The Web VM must retain its `http-server` and `https-server` network tags for IAP access, and may receive an additional tag for the Internal Load Balancer health checks.

The agent must preserve the existing VPC configuration. Do not modify the existing `allow-iap-ssh` rule, do not modify the `default-allow-internal` rule, do not change the VPC routing. The goal is additive: add only the firewall rules necessary for the Internal Load Balancer to reach the Web VM.

### **Tools to use and why**

Use `gcloud compute firewall-rules list` to capture the current firewall state. Use `gcloud compute networks describe` and `gcloud compute networks subnets list` to capture the VPC and subnet configuration. Use `gcloud compute instances describe` on `ftd-staging-web` and `ftd-staging-api` to capture their network tags and network interfaces. Use the terminal to execute the necessary `gcloud compute firewall-rules create` commands. Use the existing `gcloud` command patterns and IAP tunneling for verification.

Use the project's existing `gcloud` command patterns. Do not introduce Terraform, Pulumi, or any other infrastructure-as-code tool. The firewall changes must be achievable via the existing `gcloud` command patterns used by the project.

### **Implementation**

Create the necessary firewall rule to allow the Internal Load Balancer to reach the Web VM:

1. **Identify the proxy-only subnet** used by Internal Load Balancers in the `ftd2026` project. This is typically `10.128.0.0/20` but must be verified via `gcloud compute networks subnets list --filter="purpose=INTERNAL_HTTPS_LOAD_BALANCER"`.

2. **Create a firewall rule** named `allow-ilb-to-web-vm` (or similar naming convention):
   - Direction: INGRESS
   - Action: ALLOW
   - Target tags: `ftd-staging-web` (the network tag on the Web VM)
   - Source ranges: The proxy-only subnet range identified in step 1
   - Protocols/ports: TCP:443
   - Priority: 1000 (or appropriate priority below the default deny rule)

3. **Verify the firewall rule** is effective by checking that the Internal Load Balancer health checks can reach the Web VM on port 443 (this will be verified in later sublayers when the Internal Load Balancer is created).

4. **Verify existing rules remain intact**: `allow-iap-ssh` must still allow TCP 22 from `35.235.240.0/20`. The `default-allow-internal` rule must still allow all protocols from `10.128.0.0/9`.

### **Error handling**

Firewall rule creation failures must be caught and reported with specific context (which `gcloud` command failed, what the error message was). If the firewall rule conflicts with an existing rule, report the conflict rather than forcing the change. If the proxy-only subnet cannot be identified, report the infrastructure boundary rather than guessing the range.

### **Developer responsibilities**

The developer must approve the firewall rule creation before execution. The developer must verify that the proxy-only subnet range is correct for the project. The developer must confirm that the existing IAP SSH access remains functional after the new rule is applied.

### **IDE agent responsibilities**

The IDE agent may inspect the current firewall and network state, create the necessary firewall rule, and verify the rule is applied correctly. The agent may not modify existing firewall rules, VPC routing, or subnet configurations beyond the additive firewall rule. The agent must report the outcome (success/failure, rule details, any deviations).

### **Hard stop**

Under no circumstances may the agent modify the existing `allow-iap-ssh` firewall rule, modify the `default-allow-internal` rule, change VPC routing, modify subnet configurations, or expose port 22 or 8080 to the public internet (0.0.0.0/0). If the firewall rule cannot be created cleanly, stop and report.

## **SUBLAYER 7.2 — CREATE INTERNAL LOAD BALANCER FOR WEB VM**

### **Instruction**

The objective of Sublayer 7.2 is to create an Internal HTTP(S) Load Balancer that fronts the Web VM (`ftd-staging-web`) on port 443. The Internal Load Balancer will be the target of the External Load Balancer (created in Sublayer 7.3) and will distribute traffic to the Web VM. The agent must first inspect the existing Web VM configuration, specifically that nginx is running on port 8080, serving the React frontend on `/` and proxying `/api/*` to the Backend VM (`10.168.0.7:8000`). The investigation must be narrow and purposeful: verify the Web VM's nginx health endpoint (`/health` returning "healthy"), verify the API proxy works (`/api/health` returns `{"status":"ok"}`), and confirm the Web VM's internal IP (`10.168.0.6`).

The resulting Internal Load Balancer must:
- Be an Internal HTTP(S) Load Balancer (not External)
- Use the proxy-only subnet in the `ftd2026` project
- Have a backend service with the Web VM (`ftd-staging-web`) as the sole backend, targeting port 8080
- Use a health check on `/health` expecting "healthy" response on port 443
- Have a URL map that routes all traffic to the backend service
- Have a forwarding rule on the proxy-only subnet with a static internal IP (or ephemeral, but static preferred for stability) on port 443
- Be in the `us-west2-a` region (same as the Web VM)

The agent must preserve the existing Web VM configuration. Do not modify nginx configuration beyond what was established in Layer Five. Do not modify the Web VM's nginx configuration or the proxy pass to the Backend VM.

### **Tools to use and why**

Use `gcloud compute health-checks create http` to create the health check. Use `gcloud compute backend-services create` with `--load-balancing-scheme=INTERNAL_MANAGED` to create the backend service. Use `gcloud compute url-maps create` to create the URL map. Use `gcloud compute target-http-proxies create` (or target-https-proxy if TLS termination at ILB) to create the target proxy. Use `gcloud compute forwarding-rules create` with `--load-balancing-scheme=INTERNAL_MANAGED` to create the forwarding rule. Use `gcloud compute addresses create` to reserve a static internal IP for the forwarding rule.

Use the project's existing `gcloud` command patterns. Do not introduce Terraform, Pulumi, or any other infrastructure-as-code tool. The Load Balancer configuration must be achievable via the existing `gcloud` command patterns used by the project.

### **Implementation**

1. **Create health check** named `web-vm-health-check`:
   - Type: HTTPS
   - Port: 443
   - Request path: `/health`
   - Expected response: "healthy"
   - Check interval: 10s, timeout: 5s, healthy threshold: 2, unhealthy threshold: 3

2. **Create backend service** named `web-vm-backend-service`:
   - Load balancing scheme: `INTERNAL_MANAGED`
   - Protocol: HTTPS
   - Health check: `web-vm-health-check`
   - Backend: Instance group containing `ftd-staging-web` (or zonal NEG if using NEGs), port 8080
   - Session affinity: NONE (or CLIENT_IP if needed for WebSocket, but not required here)

3. **Create URL map** named `web-vm-url-map`:
   - Default service: `web-vm-backend-service`
   - No host/path rules needed (all traffic to backend)

4. **Create target HTTPS proxy** named `web-vm-target-proxy`:
   - URL map: `web-vm-url-map`
   - SSL certificate: self-signed or internal CA certificate for ILB TLS termination

5. **Reserve static internal IP** named `ilb-web-vm-ip`:
   - Region: `us-west2`
   - Subnet: default subnet in `us-west2-a` (or the subnet where the Web VM resides)

6. **Create forwarding rule** named `web-vm-forwarding-rule`:
   - Load balancing scheme: `INTERNAL_MANAGED`
   - Target proxy: `web-vm-target-proxy`
   - IP address: the static internal IP from step 5
   - Ports: 443
   - Subnetwork: the subnet in `us-west2-a`
   - Network: the VPC network

7. **Verify the Internal Load Balancer**:
   - Wait for backend health checks to pass (backend becomes HEALTHY)
   - From the Backend VM, curl the ILB's internal IP on port 443: should return HTML frontend on `/`, "healthy" on `/health`, and JSON on `/api/health` and `/api/version`

### **Error handling**

Load Balancer creation failures must be caught and reported with specific context (which `gcloud` command failed, what the error message was). If the backend health checks never pass, report the health check configuration and the Web VM's actual response. If the forwarding rule cannot be created due to IP conflicts, report the conflict. If the backend never becomes HEALTHY, report the health check response from the Web VM on port 443.

### **Developer responsibilities**

The developer must approve the Internal Load Balancer configuration before creation. The developer must verify the static internal IP does not conflict with existing allocations. The developer must confirm the Web VM's nginx is correctly serving the frontend and proxying API requests before the ILB is created.

### **IDE agent responsibilities**

The IDE agent may create the Internal Load Balancer components via `gcloud` commands, verify the backend becomes HEALTHY, and test the ILB from the Backend VM. The agent may not modify the Web VM's nginx configuration, the Web VM's firewall rules beyond what was done in 7.1, or the Backend VM configuration. The agent must report the ILB configuration (IP, backend health, forwarding rule details) to the developer.

### **Hard stop**

Under no circumstances may the agent create an External Load Balancer in this sublayer, expose the Internal Load Balancer to the public internet, modify the Web VM's nginx configuration, change the Web VM's port from 8080, or modify the Backend VM. If the Internal Load Balancer cannot be created with the Web VM as a healthy backend on port 443, stop and report.

## **SUBLAYER 7.3 — CREATE EXTERNAL LOAD BALANCER AND GOOGLE CLOUD GATEWAY**

### **Instruction**

The objective of Sublayer 7.3 is to create the External HTTP(S) Load Balancer with Google Cloud Gateway (or External HTTP(S) Load Balancer with Cloud Armor) that fronts the Internal Load Balancer created in Sublayer 7.2, exposing the staging application to the public internet. The External Load Balancer will terminate TLS, provide DDoS protection, and route traffic to the Internal Load Balancer's internal IP. The agent must first inspect the Internal Load Balancer created in Sublayer 7.2, specifically its internal IP address, the backend health status, and the fact that it serves the React frontend on `/` and proxies `/api/*` to the Backend VM.

The resulting External Load Balancer must:
- Be an External HTTP(S) Load Balancer (Global) with Google Cloud Gateway (or External HTTP(S) Load Balancer with Cloud Armor enabled)
- Terminate TLS using a Google-managed certificate (or a developer-provided certificate)
- Have a backend service that targets the Internal Load Balancer's internal IP on port 443
- Use a health check that verifies the Internal Load Balancer's `/health` endpoint on port 443
- Have a URL map that routes all traffic to the backend service
- Have a forwarding rule on a static external IP (reserved) on ports 80 (HTTP redirect to HTTPS) and 443 (HTTPS)
- Enable Cloud Armor with a basic security policy (allow all, but with rate limiting on sensitive paths if applicable)
- Enforce HTTPS: redirect HTTP (port 80) to HTTPS (port 443)

The agent must preserve the Internal Load Balancer and Web VM configuration. Do not modify the Internal Load Balancer, the Web VM's nginx, or the Backend VM.

### **Tools to use and why**

Use `gcloud compute ssl-certificates create` (for Google-managed certificate) or `gcloud compute ssl-certificates create` with `--certificate` and `--private-key` (for custom certificate). Use `gcloud compute backend-services create` with `--load-balancing-scheme=EXTERNAL_MANAGED` to create the external backend service. Use `gcloud compute health-checks create http` for the health check. Use `gcloud compute url-maps create` for the URL map. Use `gcloud compute target-https-proxies create` for the HTTPS target proxy. Use `gcloud compute target-http-proxies create` for the HTTP redirect proxy. Use `gcloud compute forwarding-rules create` with `--load-balancing-scheme=EXTERNAL_MANAGED` for the forwarding rules. Use `gcloud compute addresses create` to reserve a static external IP.

Use the project's existing `gcloud` command patterns. Do not introduce Terraform, Pulumi, or any other infrastructure-as-code tool. The Load Balancer configuration must be achievable via the existing `gcloud` command patterns used by the project.

### **Implementation**

1. **Reserve a static external IP** named `ext-lb-staging-ip`:
   - Global IP address
   - Description: "Static external IP for staging External Load Balancer"

2. **Create SSL certificate** (Google-managed preferred):
   - Name: `staging-ssl-cert`
   - Domains: the staging domain (e.g., `staging.ftd.example.com` — developer must provide)
   - Type: Google-managed (auto-provisioned and renewed)

3. **Create health check** named `ext-lb-health-check`:
   - Type: HTTPS
   - Port: 443
   - Request path: `/health` (proxied through ILB to Web VM)
   - Expected response: "healthy"
   - Check interval: 30s, timeout: 10s, healthy threshold: 2, unhealthy threshold: 3

4. **Create backend service** named `ext-lb-backend-service`:
   - Load balancing scheme: `EXTERNAL_MANAGED`
   - Protocol: HTTPS (to ILB)
   - Health check: `ext-lb-health-check`
   - Backend: The Internal Load Balancer's internal IP as a non-GCP backend (or use Internet NEG pointing to ILB internal IP), port 443
   - Enable Cloud CDN: OFF (staging, not needed)
   - Security policy: basic Cloud Armor policy (see step 8)

5. **Create URL map** named `ext-lb-url-map`:
   - Default service: `ext-lb-backend-service`

5. **Create target HTTPS proxy** named `ext-lb-target-https-proxy`:
   - URL map: `ext-lb-url-map`
   - SSL certificate: `staging-ssl-cert`

6. **Create target HTTP proxy** named `ext-lb-target-http-proxy`:
   - URL map: redirect map that sends all HTTP to HTTPS (or use URL map with redirect)

7. **Create forwarding rules**:
   - HTTPS forwarding rule: `ext-lb-https-forwarding-rule`, IP: static external IP, port 443, target: `ext-lb-target-https-proxy`
   - HTTP forwarding rule: `ext-lb-http-forwarding-rule`, IP: same static external IP, port 80, target: `ext-lb-target-http-proxy` (redirect)

8. **Create Cloud Armor security policy** named `staging-armor-policy`:
   - Default rule: allow all
   - Rate limiting rule: optional, e.g., 100 requests/minute per IP on `/api/*` paths
   - Attach to `ext-lb-backend-service`

9. **Verify the External Load Balancer**:
   - Wait for SSL certificate provisioning (Google-managed can take up to 60 minutes)
   - Wait for backend health checks to pass
   - From the public internet, curl the staging domain on HTTPS: should return React frontend on `/`, JSON on `/api/health` and `/api/version`
   - Verify HTTP redirects to HTTPS
   - Verify TLS certificate is valid and matches the domain

### **Error handling**

Certificate provisioning failures must be caught and reported (DNS not propagated, domain verification failed). If the backend health checks never pass, report the health check configuration and the Internal Load Balancer's actual response on port 443. If the SSL certificate cannot be provisioned due to DNS issues, report the DNS configuration required. If the External Load Balancer cannot route to the Internal Load Balancer, report the internal IP connectivity.

### **Developer responsibilities**

The developer must provide the staging domain name for the SSL certificate. The developer must configure DNS (A record) to point the staging domain to the reserved static external IP. The developer must approve the External Load Balancer configuration before creation. The developer must verify the SSL certificate is valid and the domain resolves correctly.

### **IDE agent responsibilities**

The IDE agent may create the External Load Balancer components via `gcloud` commands, verify the backend becomes HEALTHY, and test the External Load Balancer from the public internet. The agent may not modify the Internal Load Balancer, the Web VM, the Backend VM, or the Database VM. The agent must report the External LB configuration (external IP, SSL certificate status, backend health) to the developer.

### **Hard stop**

Under no circumstances may the agent expose the Database VM or Backend VM directly to the External Load Balancer, disable TLS termination at the External Load Balancer, disable HTTPS redirect, use self-signed certificates for the external endpoint, or expose the Internal Load Balancer's internal IP to the public internet. If the External Load Balancer cannot be created with a valid SSL certificate and healthy backend on port 443, stop and report.

## **SUBLAYER 7.4 — CONFIGURE DNS AND TLS FOR STAGING DOMAIN**

### **Instruction**

The objective of Sublayer 7.4 is to configure DNS and TLS for the staging domain so that the External Load Balancer created in Sublayer 7.3 can serve traffic on a proper hostname with a valid TLS certificate. The agent must first obtain the static external IP address reserved in Sublayer 7.3 and the staging domain name provided by the developer.

The resulting DNS and TLS configuration must:
- Have an A record pointing the staging domain (e.g., `staging.ftd.example.com`) to the static external IP reserved in Sublayer 7.3
- Have a Google-managed SSL certificate provisioned for the staging domain, attached to the External Load Balancer's target HTTPS proxy
- Ensure the certificate is actively serving (not in "provisioning" state) before declaring the gateway live
- Ensure HTTP traffic on port 80 redirects to HTTPS on port 443

The agent must preserve the External Load Balancer configuration from Sublayer 7.3. Do not modify the External Load Balancer, the Internal Load Balancer, or any VM configurations.

### **Tools to use and why**

Use `gcloud compute ssl-certificates describe` to monitor certificate provisioning status. Use `gcloud compute addresses describe` to confirm the static external IP. Use `dig` or `nslookup` to verify DNS propagation. Use `curl` with `-v` to verify TLS handshake and certificate validity from the public internet.

Use the project's existing `gcloud` command patterns. Do not introduce external DNS management tools or certificate management tools beyond what GCP provides.

### **Implementation**

1. **Verify DNS configuration**:
   - Developer provides staging domain (e.g., `staging.ftd.example.com`)
   - Create or verify A record: `staging.ftd.example.com` → static external IP from Sublayer 7.3
   - Verify DNS propagation: `dig staging.ftd.example.com +short` returns the static external IP

2. **Verify SSL certificate provisioning**:
   - Monitor `gcloud compute ssl-certificates describe staging-ssl-cert --format="value(managed.status)"`
   - Wait for status to become `ACTIVE` (can take up to 60 minutes after DNS propagation)
   - If status is `FAILED`, report the failure reason (usually DNS not propagated or domain not authorized)

3. **Verify TLS termination**:
   - Once certificate is ACTIVE, curl the staging domain with `-v` flag
   - Verify TLS handshake completes, certificate is valid, CN/SAN matches the staging domain
   - Verify certificate chain is valid and trusted

4. **Verify HTTP to HTTPS redirect**:
   - `curl -I http://staging.ftd.example.com` should return 301/302 redirect to `https://staging.ftd.example.com`
   - `curl -I https://staging.ftd.example.com` should return 200 with valid TLS

### **Error handling**

Certificate provisioning failures must be reported with the specific failure reason from GCP (usually DNS not propagated, CAA record blocking, or domain not authorized). If DNS does not propagate within 24 hours, report the DNS configuration issue. If the certificate remains in `PROVISIONING` state beyond 60 minutes after DNS propagation, report the provisioning delay.

### **Developer responsibilities**

The developer must provide the staging domain name. The developer must configure the DNS A record in their DNS provider. The developer must verify the domain is accessible and authorize Google to provision the certificate (may require adding a CAA record or responding to email verification).

### **IDE agent responsibilities**

The agent may monitor certificate provisioning status, verify DNS resolution, and test TLS connectivity. The agent may not modify DNS records, request certificates for unauthorized domains, or modify the External Load Balancer configuration. The agent must report the certificate status, DNS resolution, and TLS verification results to the developer.

### **Hard stop**

Under no circumstances may the agent use self-signed certificates, proceed without a valid TLS certificate, disable HTTPS redirect, or expose the staging application on HTTP only. If the verification cannot be completed due to infrastructure issues, stop and report the blocker.

## **FINAL LAYER SEVEN DEFINITION OF DONE**

Layer Seven is complete only when the staging application is publicly accessible through Google Cloud Gateway with the following verified properties:

1. **External Load Balancer** terminates TLS with a valid Google-managed certificate on a custom staging domain, redirects HTTP to HTTPS, and has a static external IP with DNS A record pointing to it.

2. **Internal Load Balancer** routes traffic from the External Load Balancer to the Web VM, terminating TLS on port 443 and connecting to the Web VM on port 8080 via internal VPC, with healthy backend checks.

3. **Web VM** (`ftd-staging-web`) serves the React frontend on `/`, proxies `/api/*` to the Backend VM via internal VPC, and has nginx health endpoint returning "healthy".

4. **Backend VM** (`ftd-staging-api`) runs FastAPI on 0.0.0.0:8000, connects to the staging database on the Database VM, serves `/health` and `/version` endpoints.

5. **Database VM** (`ftd-postgres-vm`) hosts `ftd_lakehouse_staging` with all migrations applied.

6. **CI/CD Pipeline** gates deployment on CI success, deploys correct artifacts to each VM, applies migrations safely, writes version metadata atomically, and verifies end-to-end health.

7. **Traceability**: A developer can answer "what commit is running on staging?" by querying `https://staging.ftd.example.com/api/version` and "what caused that version to get deployed?" by inspecting GitHub Actions workflow history — without manual VM investigation.

8. **Security**: Database VM not exposed publicly, Backend VM not exposed publicly, Web VM only accessible via Internal Load Balancer, SSH access only via IAP, HTTP redirects to HTTPS, TLS certificate valid and auto-renewed.

9. **Failure Gates**: Broken CI blocks deployment entirely; failed health checks block deployment; failed migrations block backend startup.

10. **Verification**: All checks pass from public internet via the staging domain, including TLS validity, HTTP→HTTPS redirect, frontend serving, API proxying, version metadata accuracy, cross-deployment isolation, and database connectivity.

The resulting architecture makes the staging environment a publicly accessible, TLS-terminated, gateway-fronted replica of the intended production architecture, with the CI/CD pipeline as the sole deployment mechanism. The completion of Layer Seven does not authorize work on Layer Eight (production). Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.

## **SUBLAYER 7.5 — END-TO-END GATEWAY VERIFICATION**

### **Instruction**

The objective of Sublayer 7.5 is to prove that the complete gateway architecture functions correctly: Internet traffic reaches the External Load Balancer, TLS is terminated, traffic routes through the Internal Load Balancer to the Web VM, the Web VM serves the React frontend and proxies API requests to the Backend VM, the Backend VM connects to the Database VM, and the version metadata is traceable end-to-end. The verification must demonstrate that: a push to the `staging` branch triggers CI, CI passes, the full multi-VM deploy sequence runs, the External Load Balancer serves the application on the staging domain with valid TLS, all health checks pass, the `/version` endpoint returns correct metadata, no cross-deployment occurs, and a failed CI run blocks deployment.

The verification must exercise the actual public endpoint, not internal IAP tunnels. The test must use the actual staging domain, actual TLS certificate, actual External Load Balancer, actual Internal Load Balancer, actual Web VM, actual Backend VM, and actual Database VM.

### **Tools to use and why**

Use `curl` with `-v` from the public internet to test the staging domain. Use `gh` CLI to monitor workflow runs. Use `gcloud compute ssh` via IAP tunnels to verify internal VM state and version metadata files. Use `dig` and `openssl s_client` to verify DNS and TLS. Use Git commands to verify commit history.

Use the project's existing IAP tunnel patterns for internal verification. Do not create new access methods. Use the existing staging domain and certificate.

### **Implementation**

Create a verification procedure that:

1. Records the current state of the staging environment (current `/version` output via public domain, current commit on `staging` branch).
2. Makes a small, identifiable change to the `staging` branch (e.g., a version bump or a comment in a non-functional file).
3. Pushes the change to the `staging` branch and monitors the CI workflow to completion (success).
4. Monitors the deploy workflow: verifies CI passed gate, `deploy-staging-migrations` runs, `deploy-staging-backend` runs, `deploy-staging-web` runs, `deploy-staging-verify` runs.
5. Queries the staging domain via public internet:
   - `curl https://staging.ftd.example.com/` → returns HTML (React frontend)
   - `curl https://staging.ftd.example.com/api/health` → returns `{"status":"ok"}` (proxied through gateway → ILB → Backend VM)
   - `curl https://staging.ftd.example.com/api/version` → returns version metadata matching pushed commit
   - `curl -I http://staging.ftd.example.com` → returns 301/302 redirect to HTTPS
   - `openssl s_client -connect staging.ftd.example.com:443 -servername staging.ftd.example.com` → shows valid certificate chain
4. Queries the Backend VM directly via IAP tunnel (for cross-reference):
   - `curl http://10.168.0.7:8000/health` → returns `{"status":"ok"}`
   - `curl http://10.168.0.7:8000/version` → returns version metadata matching pushed commit
5. Verifies the `version.json` file on both VMs contains the expected metadata and is readable by the application.
6. Verifies that the `staging` branch push did NOT trigger any development environment deployment (check `ftd-test` version unchanged).
7. Tests the failure gate: introduces a breaking change (e.g., syntax error in a test file) to a feature branch, opens a PR to `staging`, verifies CI fails, and verifies no staging deployment is triggered.
8. Verifies that GitHub Actions workflow history shows the complete chain: commit → CI run → migration run → backend deploy → web deploy → verify run → success.

### **Error handling**

Verification failures must be reported with specific evidence: which endpoint was expected to respond, which actually responded, what the response was vs. what was expected, what the workflow logs show. If the public endpoint returns 5xx, the verification must fail — this is an architecture failure, not a transient issue. If the TLS certificate is invalid or expired, the verification must fail. If the workflow succeeds but the wrong environment is updated, this is a critical routing failure that must be reported immediately. If CI fails but deployment still proceeds, this is a gate failure that must be reported immediately.

Infrastructure failures during verification (VM unreachable, database unavailable, IAP tunnel broken, inter-VM connectivity broken, DNS not propagated, certificate not provisioned) must be reported as infrastructure blockers, not as verification failures. The agent must not retry indefinitely or modify the verification criteria to pass.

### **Developer responsibilities**

The developer must approve the verification procedure before execution. The developer must be available to resolve infrastructure blockers (VM issues, network issues, credential issues, proxy configuration issues, DNS issues, certificate issues) that prevent verification. The developer must review the final verification report and approve Layer Seven completion.

### **IDE agent responsibilities**

The IDE agent may execute the verification procedure, collect the evidence, and produce the verification report. The agent may not make changes to the workflows, VMs, gateway configuration, or application code during verification — any issue discovered must be reported, not fixed inline. The agent must stop after producing the verification report.

### **Hard stop**

Under no circumstances may the agent consider Layer Seven complete without successful verification of the full public gateway stack, the TLS certificate validity, the HTTP-to-HTTPS redirect, the proxy routing through both load balancers, the database connectivity, and the CI gate. The agent must not modify the verification criteria to accommodate failures. The agent must not use manual deployment steps to fake a successful verification. The agent must not skip the failure gate test (broken CI blocks deploy). If the verification cannot be completed due to infrastructure issues, stop and report the blocker.