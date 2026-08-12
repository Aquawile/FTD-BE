# FTD Development Deployment Pipeline

## Branch Strategy

| Branch | Purpose | Deploys To |
|---|---|---|
| `main` | Protected production reference | None (manual only) |
| `rawdataingestion` | Active development stream | `ftd-test` VM via GitHub Actions |

**Rule:** Never push directly to `main`. All development work occurs on `rawdataingestion`.

## Development VM: ftd-test

- **Zone:** us-west2-a
- **Internal IP:** 10.168.0.4
- **External IP:** 34.94.193.132
- **OS User:** isabellabutera
- **Python:** 3.13.5
- **Node.js:** Not installed (frontend built locally, deployed as static assets)
- **FastAPI:** bound to 127.0.0.1:8000
- **Access:** IAP/SSH tunneling only (no public exposure)
- **Process management:** nohup + start_app.sh (no systemd)

## Current Manual Deployment Recipe

1. `pkill -f uvicorn` on VM
2. `gcloud compute scp` backend files to `/home/isabellabutera/app/app/`
3. `gcloud compute scp` top-level files to `/home/isabellabutera/`
4. `pip install -r requirements.txt` in VM venv
5. `bash /home/isabellabutera/start_app.sh`
6. `curl http://127.0.0.1:8000/health` to verify

## What Gets Deployed

| Component | Source | VM Destination |
|---|---|---|
| FastAPI backend | `app/` | `/home/isabellabutera/app/app/` |
| Entry points | `main.py`, `models.py`, `router.py` | `/home/isabellabutera/` |
| Python deps | `requirements.txt` | `/home/isabellabutera/requirements.txt` |
| React build | `context/figma_prototype/dist/` | `/home/isabellabutera/frontend/dist/` |
| Startup script | existing on VM | `/home/isabellabutera/start_app.sh` |

## Environment Variables (on VM only)

| Variable | Purpose |
|---|---|
| `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` | PostgreSQL connection |
| `FIREBASE_PROJECT_ID` | Firebase project |
| `FIREBASE_CREDENTIALS_PATH` | Firebase Admin SDK key |
| `FIREBASE_AUTH_ENABLED` | Enable Firebase auth |

## Secrets Strategy

**Repository (safe):**
- Firebase Web API key (client-side, public by design)
- GitHub Actions workflow files
- Application source code

**VM only (never commit):**
- PostgreSQL password
- Firebase Admin SDK private key (`/home/isabellabutera/firebase-key.json`)
- GCP service account keys

**GitHub Actions:**
- Uses GCP Workload Identity (no key files needed)
- Existing provider: `projects/767713105/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider`
- Service account: `github-actions-deploy@ftd2026.iam.gserviceaccount.com`

## Security Constraints

- FastAPI remains bound to `127.0.0.1:8000`
- No public firewall rules for port 8000
- PostgreSQL remains on private VPC (ftd-postgres-vm)
- No `0.0.0.0` bindings
- No production database modifications from CI/CD
- No Docker/Kubernetes introduced

## What This Layer Does NOT Include

- No staging branch or VMs
- No Google Cloud Gateway
- No public exposure of application
- No production database modifications
- No direct pushes to `main`
