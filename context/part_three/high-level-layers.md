# Part Three — Frontend Real-Data Integration & UI Restoration

## Overview

Part Three operates on the existing React/HTML frontend imported from Figma, located at `context/figma_prototype/`. The application is currently rendered as a single-file React app (`src/app/App.tsx`) with all pages, routing, components, mock data, and shared primitives defined inline. The backend FastAPI service is running on the staging VM (`ftd-staging-api`, internal IP `10.168.0.7`) and the staging web VM (`ftd-staging-web`, internal IP `10.168.0.6`) serves the built frontend assets via nginx on port 8080. Public access is provided through a Cloudflare Tunnel (`https://specification-frog-parliamentary-turns.trycloudflare.com`) terminating HTTP to the External Load Balancer IP `136.110.247.187`.

## Architecture Constraints

| Property | Value |
|---|---|
| Frontend source | `context/figma_prototype/src/app/App.tsx` (single file, 2860 lines) |
| Build output | `context/figma_prototype/dist/` |
| Backend API | FastAPI on `ftd-staging-api:8000` (bound to `0.0.0.0` for internal LB) |
| Web server | nginx on `ftd-staging-web:8080` proxying `/api/` to `10.168.0.7:8000` |
| Public access | Cloudflare Tunnel → External LB → Internal LB → Web VM → Backend API |
| Database | PostgreSQL on `ftd-postgres-vm` (internal IP `10.168.0.3`), accessed only via FastAPI |
| Data providers | GNews (free tier), SEC EDGAR (free tier), Finnhub (free tier) |
| Provider access | Backend-only; React must never call providers directly |

## Data Access Rules

- **React must not communicate with PostgreSQL directly.** All data flows through FastAPI routes.
- **React must not call external data providers directly.** All provider access is backend-only.
- **Mock data source code must be preserved.** The constants, helper functions, and type definitions that reproduce mock data should remain in the codebase as reference implementations. Only the rendered/displayed mock elements should be replaced with live API calls.
- **Hype score and stock price chart are out of scope for Part Three.** These UI elements should remain as mock data until a later phase. Do not remove their source code.
- **Postgres is read-only for this phase.** Under no circumstances may any layer in Part Three modify, delete, or alter existing Postgres tables or data. All Postgres data is already stripped to contain only the fields needed by the webapp.

## What This Part Does NOT Include

- No changes to the existing Postgres schema or data
- No new provider integrations (providers are already wired in the backend)
- No hype score implementation
- No stock price chart implementation
- No Docker, Kubernetes, or infrastructure changes
- No changes to the existing Cloudflare Tunnel or load balancer configuration

## Layer Map

| Layer | Title | Scope |
|---|---|---|
| One | Authentication & Landing Page Reconstruction | Replace public landing with login-first entry, fix forms, restore old landing safely |
| Two | Profile Page UI Restructuring & Form Fixes | Rename Account→Profile, fix controlled inputs, enable photo upload, restructure sidebar |
| Three | Dashboard Real Data Integration — Article Count & Core Metrics | Wire articles-analyzed count and primary stats to Postgres |
| Four | Dashboard Real Data Integration — Tickers, Workspaces & Alerts | Replace mock tickers, workspaces, alerts with live data |
| Five | Mock Data Cleanup & UI Artifact Removal | Remove rendered mock elements while preserving source code |
| Six | Data Provider Context, Constraints & Free-Tier Behavior | Document provider limits, caching, update frequency, and safe fetching patterns |

(End of file - total 51 lines)