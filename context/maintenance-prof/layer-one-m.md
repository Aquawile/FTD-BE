# Layer One — Development Deployment Pipeline

## Sublayer 1.2 — Audit of Existing Development Environment

### Development VM Identity

| Property | Value |
|---|---|
| VM Name | `ftd-test` |
| GCP Project | `ftd2026` |
| Zone | `us-west2-a` |
| Internal IP | `10.168.0.4` |
| External IP | `34.94.193.132` |
| OS User | `isabellabutera` |
| Python | 3.13.5 |
| Node.js | Not installed |
| Systemd services | None for application |

### Current Manual Deployment Process

The application is currently deployed manually via SSH/SCP. The exact steps are:

1. **Stop existing FastAPI process**
   ```bash
   gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --command="pkill -f uvicorn || true"
   ```

2. **Sync backend code**
   ```bash
   gcloud compute scp --recurse app/ ftd-test:/home/isabellabutera/app/app/ --zone=us-west2-a --project=ftd2026
   gcloud compute scp main.py ftd-test:/home/isabellabutera/main.py --zone=us-west2-a --project=ftd2026
   gcloud compute scp models.py ftd-test:/home/isabellabutera/models.py --zone=us-west2-a --project=ftd2026
   gcloud compute scp router.py ftd-test:/home/isabellabutera/router.py --zone=us-west2-a --project=ftd2026
   gcloud compute scp requirements.txt ftd-test:/home/isabellabutera/requirements.txt --zone=us-west2-a --project=ftd2026
   ```

3. **Install Python dependencies**
   ```bash
   gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --command="cd /home/isabellabutera/app && .venv/bin/pip install --break-system-packages -r /home/isabellabutera/requirements.txt"
   ```

4. **Start/Restart FastAPI**
   ```bash
   gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --command="bash /home/isabellabutera/start_app.sh"
   ```

5. **Verify health**
   ```bash
   gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --command="curl -s http://127.0.0.1:8000/health"
   ```

### Application Runtime Details

**Backend (FastAPI):**
- Entry point: `app.main:app`
- Runtime: Uvicorn via `.venv/bin/uvicorn`
- Bind: `127.0.0.1:8000` (loopback only)
- Process management: `nohup` + background process in `start_app.sh`
- No systemd service
- Logs: `/tmp/uvicorn.log`

**Frontend (React/Vite):**
- Source: `context/figma_prototype/`
- Build output: `context/figma_prototype/dist/`
- Current serving: Local Vite dev server (`localhost:5173`) on developer machine
- NOT deployed to VM (no Node.js on VM)
- Access via IAP tunnel: `localhost:18000 → ftd-test:8000`

### Environment Variables and Configuration

**Set in `start_app.sh` on VM:**
| Variable | Value | Purpose |
|---|---|---|
| `PGHOST` | `10.168.0.3` | PostgreSQL VM internal IP |
| `PGPORT` | `5432` | PostgreSQL port |
| `PGDATABASE` | `ftd_lakehouse_api_test` | Application test database |
| `PGUSER` | `ftd_app` | PostgreSQL application user |
| `PGPASSWORD` | `5Ou+BkyuQT3izP72219jMLy2AobRdI3f` | PostgreSQL password |
| `FIREBASE_PROJECT_ID` | `ftd-2026` | Firebase project |
| `FIREBASE_CREDENTIALS_PATH` | `/home/isabellabutera/firebase-key.json` | Firebase Admin SDK key |
| `FIREBASE_AUTH_ENABLED` | `true` | Enable Firebase auth |

**Set in React source code (`App.tsx`):**
| Variable | Value | Purpose |
|---|---|---|
| `firebaseConfig.projectId` | `ftd-2026` | Firebase project ID |
| `firebaseConfig.apiKey` | `AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8` | Firebase Web API key (public, client-side) |
| `API_BASE` | `http://127.0.0.1:18000` | Backend API URL (dev tunnel) |

### Secrets and Credentials Strategy

**DO NOT commit to repository:**
- PostgreSQL password (`PGPASSWORD`)
- Firebase Admin SDK private key (`/home/isabellabutera/firebase-key.json`)
- Any GCP service account keys

**Safe to commit:**
- Firebase Web API key (client-side, public by design)
- GitHub Actions workflow files
- Application source code

**Where secrets live:**
- PostgreSQL password: in `start_app.sh` on VM only
- Firebase service account key: in `/home/isabellabutera/firebase-key.json` on VM only
- GCP Workload Identity: handles GitHub Actions → GCP authentication without storing keys

### Repository Components to Deploy

| Component | Source Path | VM Destination | Notes |
|---|---|---|---|
| FastAPI app | `app/` | `/home/isabellabutera/app/app/` | Python package |
| Entry points | `main.py`, `models.py`, `router.py` | `/home/isabellabutera/` | Top-level scripts |
| Python deps | `requirements.txt` | `/home/isabellabutera/requirements.txt` | Installed in venv |
| React build | `context/figma_prototype/dist/` | `/home/isabellabutera/frontend/dist/` | Static assets |
| Startup script | existing on VM | `/home/isabellabutera/start_app.sh` | NOT in repo, lives on VM |

### What the Deployment Recipe Must Do

1. Authenticate to GCP via Workload Identity (already configured)
2. Stop existing uvicorn process on `ftd-test`
3. Sync `app/` directory to `/home/isabellabutera/app/app/`
4. Sync top-level Python files to `/home/isabellabutera/`
5. Sync `requirements.txt` to VM
6. Install Python dependencies in existing venv
7. Build React frontend locally (no Node on VM)
8. Sync `dist/` to `/home/isabellabutera/frontend/dist/`
9. Execute `start_app.sh` to restart FastAPI
10. Verify `/health` endpoint responds

### Constraints and Boundaries

- **No Docker/Kubernetes**: deployment is via direct file sync and process restart
- **No systemd**: process managed via `nohup` in startup script
- **No public exposure**: FastAPI bound to `127.0.0.1:8000`, access via IAP tunnel only
- **No production DB**: uses `ftd_lakehouse_api_test` exclusively
- **No main branch deployments**: all automation targets `rawdataingestion` branch
- **Database is dependency, not deployment target**: PostgreSQL VM is separate infrastructure

### Existing GitHub Actions Infrastructure

The repository already contains `.github/workflows/deploy.yml` with:
- GCP Workload Identity authentication configured
- Deployment to other GCP targets (Cloud Functions, data-ingest-vm)
- Branch trigger on `rawdataingestion`
- Manual `workflow_dispatch` support

The new application deployment job should integrate into this existing workflow rather than creating a separate one.
