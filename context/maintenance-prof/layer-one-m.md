# Layer One — Development Deployment Pipeline

## Objective

Establish the development environment as a reproducible deployment target and connect it to GitHub Actions.

## Completed Sublayer 1.1

### Development Branch Established

- **Branch:** `rawdataingestion`
- **Protection:** `main` remains protected from direct development changes
- **Deployment boundary:** `rawdataingestion` → GitHub Actions → `ftd-test` VM

### Development Target Identified

The development target is the `ftd-test` VM (10.168.0.4) in GCP project `ftd2026`, zone `us-west2-a`.

### Application Components

| Component | Source | VM Destination |
|---|---|---|
| FastAPI backend | `app/` | `/home/isabellabutera/app/app/` |
| Requirements | `requirements.txt` | `/home/isabellabutera/requirements.txt` |
| React build | `context/figma_prototype/dist/` | `/home/isabellabutera/frontend/dist/` |
| Startup script | existing on VM | `/home/isabellabutera/start_app.sh` |

### GitHub Actions Workflow

File: `.github/workflows/deploy.yml`

The workflow:
1. Checks out code from `rawdataingestion`
2. Authenticates to GCP via Workload Identity
3. Conditionally deploys based on commit message keywords
4. Deploys application code to `ftd-test`
5. Installs Python dependencies
6. Builds React frontend
7. Restarts FastAPI service
8. Verifies health endpoint

### Architectural Relationship

```
development branch (rawdataingestion)
    ↓
GitHub Actions workflow
    ↓
GCP Workload Identity auth
    ↓
gcloud compute scp/ssh
    ↓
ftd-test VM (development application target)
    ↓
PostgreSQL VM (database dependency, separate)
```

The database is a dependency of the application, not something this workflow recreates or overwrites.

## What Was NOT Done

- No staging branch created
- No staging VMs provisioned
- No public exposure of application
- No Google Cloud Gateway configured
- No production database modifications
- No direct pushes to `main`
