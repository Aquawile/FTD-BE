# FTD Development Deployment Pipeline

## Branch Strategy

| Branch | Purpose | Deploys To |
|---|---|---|
| `main` | Protected production reference | None (manual only) |
| `rawdataingestion` | Active development stream | `ftd-test` VM via GitHub Actions |

**Rule:** Never push directly to `main`. All development work occurs on `rawdataingestion`.

## Deployment Architecture

```
rawdataingestion branch
    ↓
GitHub Actions workflow (.github/workflows/deploy.yml)
    ↓
Google Cloud Workload Identity authentication
    ↓
gcloud compute scp/ssh
    ↓
ftd-test VM (10.168.0.4)
```

## Development VM: ftd-test

- **Zone:** us-west2-a
- **Internal IP:** 10.168.0.4
- **External IP:** 34.94.193.132
- **FastAPI:** bound to 127.0.0.1:8000
- **Access:** IAP/SSH tunneling only (no public exposure)

## What Gets Deployed

### Backend (FastAPI)
- Source: `app/` directory → `/home/isabellabutera/app/app/`
- Entry point: `app.main:app`
- Dependencies: `requirements.txt` → venv at `/home/isabellabutera/app/.venv/`
- Startup: `/home/isabellabutera/start_app.sh`

### Frontend (React/Vite)
- Source: `context/figma_prototype/`
- Build: `npm run build` → `dist/`
- Deployed to: `/home/isabellabutera/frontend/dist/`
- Served: Python HTTP server or Vite dev server (local)

## Workflow Triggers

The `Deploy to GCP` workflow triggers on:
1. Push to `rawdataingestion` branch
2. Manual `workflow_dispatch`

Deployment jobs are conditional on commit messages containing:
- `app`, `backend`, `frontend`, `deploy`, `prices`, `gnews`, `start-price-vm`

## Security Constraints

- FastAPI remains bound to `127.0.0.1:8000`
- No public firewall rules for port 8000
- PostgreSQL remains on private VPC (ftd-postgres-vm)
- No `0.0.0.0` bindings
- No production database modifications from CI/CD
