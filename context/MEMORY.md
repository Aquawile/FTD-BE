# MEMORY.md — gcloud-bucket-data Codebase

**Project:** Finance Tracker Dashboard (FTD) — data ingestion monorepo  
**GCP Project:** `ftd2026`  
**Bucket:** `raw-data-strg`  
**Branch:** `rawdataingestion`  
**VM:** `data-ingest-vm` (zone `us-west2-a`)  
**Created:** 2026-07-12  

---

## 1. High-Level Purpose

This repo is a **GCP data ingestion monorepo** for a Finance Tracker Dashboard. It contains three independent pipelines that pull financial data from external sources and land raw JSON/NDJSON/HTML files into `gs://raw-data-strg` for downstream processing by BigQuery, DBT, and a BI layer.

There is no front-end, app layer, or dashboard code here — only data pipelines.

---

## 2. Repository Structure

```
gcloud-bucket-data/
├── README.md                       # Top-level monorepo overview
├── .github/workflows/deploy.yml    # CI/CD: deploys to GCP on push to rawdataingestion
├── .kilo/                          # Kilo agent-manager config (worktrees, sessions)
├── .gitignore
│
├── sec/                            # SEC Form 8-K ingestion (VM + Cloud Scheduler)
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   ├── src/                        # Python package
│   │   ├── __init__.py
│   │   ├── config.py               # Settings dataclass (env-driven)
│   │   ├── main.py                 # Pipeline entry point orchestrator
│   │   ├── sec_client.py           # SEC EDGAR HTTP client (throttling, retries, bytes tracking)
│   │   ├── filing_fetcher.py       # Extracts 8-K filings from SEC submissions JSON
│   │   ├── delta_scan.py           # Per-CIK Submissions API delta scanning
│   │   ├── bulk_submissions.py     # Full audit via bulk submissions.zip (not daily cron)
│   │   ├── gcs_storage.py          # Upload/download to GCS
│   │   ├── fortune500.py           # Target ticker list loading (GCS → fallback CSV → bootstrap)
│   │   ├── company_roster.py       # Live SEC company_tickers.json → ticker-to-CIK map
│   │   ├── ticker_resolver.py      # Shim to company_roster.py (backward compat)
│   │   ├── error_logger.py         # Local error log writes
│   │   └── vm_lifecycle.py         # GCP metadata checks + gcloud compute instances stop
│   └── scripts/
│       ├── provision_vm.sh         # Create data-ingest-vm if missing
│       ├── install_dependencies.sh # pip install on VM
│       ├── deploy_to_vm.sh         # tar + scp + untar + install deps on VM
│       ├── setup_cloud_scheduler.sh # Create/update Cloud Scheduler job (03:30 UTC)
│       └── vm_startup.sh           # Startup-script: sources .env, runs src.main, logs to /var/log
│
├── gnews/                          # GNews financial news ingestion (Cloud Function)
│   ├── requirements.txt
│   └── main.py                     # HTTP entry: gnews_ingest(request)
│
├── prices/                         # Finnhub current price ingestion (VM script + cron)
│   ├── requirements.txt
│   ├── main.py                     # Entry: main() → fetches quotes → NDJSON → GCS
│   └── run.sh                      # VM runner: installs deps, runs main.py, traps EXIT to stop VM
│
├── cloud-functions/
│   └── start-price-vm/             # Cloud Function to start data-ingest-vm via GCP API
│       ├── requirements.txt
│       └── main.py
│
└── context/                        # Business context files
    ├── FTD_ Core User Flows.pdf
    ├── Mentorship App#1.pdf
    └── UC_Master_Table v02 (3).xlsx
```

---

## 3. GCS Layout (`gs://raw-data-strg`)

```
SEC/
├── 8-K/{CIK}/{accession}/{primary_document}
├── 8-K/{CIK}/{accession}/metadata.txt
├── config/
│   └── fortune500.json            # {"tickers": ["AAPL", "MSFT", ...]}
├── logs/
│   ├── error_log.txt
│   ├── last_successful_run.json
│   └── fortune500_roster.json
gnews/
└── YYYY-MM-DD/batch_XXX.json      # GNews API raw responses
prices/
└── YYYY-MM-DD/data.jsonl          # One NDJSON line per ticker quote
```

---

## 4. Pipeline 1 — SEC Form 8-K Ingestion (`sec/`)

### 4.1 Architecture
- **Trigger:** Cloud Scheduler `03:30 UTC` sends `POST` to `https://compute.googleapis.com/compute/v1/projects/ftd2026/zones/us-west2-a/instances/data-ingest-vm/start`
- **Runtime:** Transient GCE VM boots, runs `src/main.py`, uploads raw documents to GCS, then **stops itself** (`gcloud compute instances stop`) in a `finally` block.
- **Safety gate:** Refuses to run off-GCP unless `ALLOW_LOCAL_EXECUTION=true`.

### 4.2 Data Strategy
1. **Target roster (~500 companies):** Loaded from `gs://raw-data-strg/SEC/config/fortune500.json`. If missing, bootstraps from `FORTUNE_500_FALLBACK_URL` (S&P 500 constituents CSV) and saves it to GCS for future runs.
2. **CIK cross-reference:** Every run fetches `https://www.sec.gov/files/company_tickers.json` and maps each target ticker → `cik_str`.
3. **Roster change detection:** Compares current target list to `SEC/logs/fortune500_roster.json` from the previous run. Logs additions/removals.
4. **Daily delta-scan:** For each resolved CIK, queries `submissions/CIK##########.json` for 8-Ks in the lookback window (7 days first run, 24 hours after). Skips any filing already in GCS. Uploads only new 8-K documents.

### 4.3 Source Modules (responsibilities)

| Module | Responsibility |
|---|---|
| `config.py` | `Settings` frozen dataclass loaded from `.env`. Handles lookback resolution (initial 7d vs steady 1d), byte budgets, rate limits. `validate()` checks required fields. |
| `main.py` | Orchestrator: loads settings, fetches tickers, resolves CIKs, detects roster changes, runs delta-scan or bulk-refresh, uploads error log, stops VM. |
| `sec_client.py` | HTTP client with `User-Agent`, per-request throttling (≤10 req/s), exponential backoff, 3 retries, XBRL filtering, byte budget tracking (`max_download_gb`/`max_ingest_gb`). |
| `filing_fetcher.py` | Parses SEC `submissions/` JSON `recent` array. Filters to `form == "8-K"` with lookback cutoff date. Excludes XBRL files. Defines `EightKFiling` dataclass. |
| `delta_scan.py` | Per-CIK delta scan using `submissions/CIK.json`. Returns eligible `EightKFiling` objects. |
| `bulk_submissions.py` | Downloads `submissions.zip` (bulk archive), extracts per-CIK submissions. Reserved for system refresh — **not** used by daily cron. |
| `gcs_storage.py` | `GcsStorage` class: checks `filing_exists()`, uploads filing + metadata.txt, manages roster/log/initial-run manifests. |
| `fortune500.py` | Loads target tickers from GCS JSON/CSV or falls back to HTTP. Dedupes, normalizes (uppercase, `.` → `-`), and limits to ~500. Auto-bootstraps roster if missing. |
| `company_roster.py` | Fetches live SEC `company_tickers.json` → uppercase ticker → zero-padded CIK mapping. `resolve_target_ciks()` returns (resolved, missing). |
| `error_logger.py` | Thread-safe local JSONL log of HTTP failures (CIK, URL, status, attempt, message). |
| `vm_lifecycle.py` | Detects if running on GCP via metadata server. Resolves project/zone/instance name. `stop_vm()` issues `gcloud compute instances stop`. |

### 4.4 Deployment Scripts

| Script | What it does |
|---|---|
| `provision_vm.sh` | `gcloud compute instances create` with e2-medium, Debian 12, 30GB boot disk, `storage-full` + `cloud-platform` scopes, OS Login. Idempotent (exits 0 if exists). |
| `install_dependencies.sh` | Creates venv at `/opt/sec-8k-ingestion/.venv`, installs `requirements.txt`. |
| `deploy_to_vm.sh` | Tars `sec/` (excluding `.venv`, `__pycache__`, `.env`), scps to VM at `/tmp/`, untars to `/opt/sec-8k-ingestion/`, runs `install_dependencies.sh`. |
| `setup_cloud_scheduler.sh` | Creates or updates Cloud Scheduler HTTP job `sec-8k-daily-start` at `30 3 * * *` UTC. Uses OAuth service account. |
| `vm_startup.sh` | Attached as VM startup-script metadata. Sources `.env`, runs `python -m src.main`, pipes output to `/var/log/sec-8k-ingestion/ingestion.log`. |

### 4.5 Critical Environment Variables (`sec/.env.example`)

| Variable | Default | Required |
|---|---|---|
| `GCP_PROJECT` | `ftd2026` | yes |
| `GCE_INSTANCE_NAME` | `data-ingest-vm` | yes |
| `GCE_ZONE` | `us-west2-a` | yes |
| `GCS_BUCKET` | `raw-data-strg` | yes |
| `GCS_SEC_PREFIX` | `SEC` | yes |
| `SEC_USER_AGENT` | `FinanceTrackerDashboard izzybutera11@gmail.com` | yes |
| `COMPANY_TICKERS_URL` | `https://www.sec.gov/files/company_tickers.json` | yes |
| `FORTUNE_500_GCS_PATH` | `config/fortune500.json` | no |
| `FORTUNE_500_FALLBACK_URL` | S&P 500 CSV | no |
| `TARGET_COMPANY_LIMIT` | `500` | no |
| `INITIAL_LOOKBACK_DAYS` | `7` | no |
| `STEADY_LOOKBACK_DAYS` | `1` | no |
| `USE_BULK_SUBMISSIONS` | `false` | no |
| `MAX_DOWNLOAD_GB` | `2.0` | no |
| `MAX_INGEST_GB` | `5.0` | no |
| `ALLOW_LOCAL_EXECUTION` | `false` | yes (safety gate) |

---

## 5. Pipeline 2 — GNews Financial News (`gnews/`)

- **Type:** GCP Cloud Function (1st gen, Python 311, 512 MB, 300 s timeout)
- **Trigger:** HTTP (`--trigger-http`, `--allow-unauthenticated`) — typically called by Cloud Scheduler
- **Entry point:** `gnews_ingest(request)`
- **Service account:** `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com`
- **Auth:** API key injected via `--set-secrets=GNEWS_API_KEY_SECRET=gnews-api-key:latest` (Secret Manager)
- **Batching:** Fortune 500 tickers split into groups of 5. Query format: `"$AAPL" OR "$MSFT" OR "$GOOGL" ...`
- **Rate limit:** Exponential backoff retries on HTTP 429 (deadline 60 s)
- **Output:** `gs://raw-data-strg/gnews/YYYY-MM-DD/batch_XXX.json` (enriched with batch_number, query, fetched_at, article_count, total_articles_available, data)
- **CORS:** Accepts OPTIONS (204) for manual browser testing
- **Dependencies:** `functions-framework`, `flask`, `google-cloud-storage`, `google-cloud-secret-manager`, `gunicorn`

---

## 6. Pipeline 3 — Finnhub Prices (`prices/`)

- **Type:** Script executed on `data-ingest-vm`
- **Entry point:** `python3 main.py` (invoked by `run.sh`)
- **Trigger:** Cron `0 22 * * * /home/isabellabutera/prices/run.sh` (installed on VM via deploy workflow)
- **Auth:** API key read from Secret Manager (`finnhub-api-key` in project `ftd2026`)
- **Rate:** 1 request per second (`REQUEST_DELAY_SECONDS = 1.0`); auto-backs off 2s on HTTP 429; aborts after **5 consecutive failures**
- **Dedup:** If `gs://raw-data-strg/prices/YYYY-MM-DD/data.jsonl` exists → no-op (skips entire fetch)
- **Output:** `gs://raw-data-strg/prices/YYYY-MM-DD/data.jsonl` — one NDJSON line per ticker with fields:
  - `symbol`, `timestamp`, `current`, `change`, `percent_change`, `high`, `low`, `open`, `previous_close`
- **VM lifecycle:** `run.sh` uses `trap EXIT` to stop the VM after pipeline finishes

---

## 7. Cloud Function — Start Price VM (`cloud-functions/start-price-vm/`)

- **Type:** GCP Cloud Function (Python 311, 256 MB, 30 s timeout)
- **Trigger:** HTTP (`--allow-unauthenticated`)
- **Entry point:** `start_vm(request)`
- **Auth:** Runs on VM; uses GCE metadata server to fetch an access token, then calls Compute Engine `start` API
- **Dependencies:** stdlib only (`urllib`, `json`)
- **After deploy:** Typically called by Cloud Scheduler before the prices pipeline runs (if VM is stopped and needs waking)

---

## 8. CI/CD — `.github/workflows/deploy.yml`

- **Trigger:** Push to `rawdataingestion` branch OR `workflow_dispatch`
- **Auth:** Workload Identity (`github-actions-pool` → `github-actions-deploy@ftd2026.iam.gserviceaccount.com`)
- **Three deployable components** (conditioned on commit message or workflow dispatch):
  1. `start-price-vm` Cloud Function — deploys if commit contains `start-price-vm` or `deploy`
  2. `gnews-ingest` Cloud Function — deploys if commit contains `gnews` or `deploy`
  3. `prices` VM script — starts VM, scps files, installs deps on VM, installs/updates cron, stops VM (if commit contains `prices` or `deploy`)

---

## 9. SEC Pipeline Execution Flow (in detail)

```
Cloud Scheduler (03:30 UTC)
    │
    ▼
gcloud compute instances start data-ingest-vm
    │
    ▼
VM startup-script runs:
    cd /opt/sec-8k-ingestion
    python -m src.main
    │
    ├── Settings.from_env(project_root)  →  loads .env
    ├── validate()                       →  checks SEC_USER_AGENT, GCP_PROJECT, etc.
    ├── is_running_on_gcp()              →  metadata server ping (guardrail)
    │
    ├── fetch_target_tickers()
    │       ├── download_config_blob("SEC/config/fortune500.json") from GCS
    │       └── If missing/invalid → fetch_target_tickers_from_http() → S&P 500 CSV → dedupe/limit → bootstrap back to GCS
    │
    ├── fetch_ticker_cik_map()           →  downloads SEC company_tickers.json → ticker→CIK map
    ├── resolve_target_ciks()            →  (ciks, missing_tickers)
    ├── load_roster_manifest()           →  reads SEC/logs/fortune500_roster.json
    ├── save_roster_manifest()           →  logs additions/removals
    │
    ├── storage.has_completed_initial_run()  →  checks SEC/logs/last_successful_run.json
    ├── resolve_lookback_days()              →  7d if first run, 1d if steady state
    │
    ├── mode = "bulk-refresh" (if USE_BULK_SUBMISSIONS=true) else "delta-scan"
    │
    ├── For each CIK:
    │       ├── sec_client.get_submissions(cik)  →  data.sec.gov/submissions/CIK.json
    │       ├── extract_recent_8k_filings()      →  8-Ks within lookback window, no XBRL
    │       └── For each 8-K:
    │               ├── storage.filing_exists()  →  gs://.../8-K/{CIK}/{accession}/{document}
    │               ├── if missing → sec_client.download_document()  →  Archives/edgar/data/...
    │               ├── storage.upload_filing()  →  raw HTML
    │               └── storage.upload_metadata() →  metadata.txt
    │
    ├── If initial run → mark_initial_run_complete()  →  writes last_successful_run.json
    ├── error_logger.has_entries() → upload_error_log()  →  SEC/logs/error_log.txt
    │
    ▼ finally block
stop_vm(settings)  →  gcloud compute instances stop data-ingest-vm ...
```

---

## 10. Prices Pipeline Execution Flow (in detail)

```
Cron (22:00 on VM)
    │
    ▼
/home/isabellabutera/prices/run.sh
    ├── trap EXIT → stop VM no matter what
    ├── pip install -r requirements.txt
    ├── python3 main.py
    │       ├── _get_gcs_bucket()          →  storage.Client().bucket("raw-data-strg")
    │       ├── load_tickers()             →  gs://raw-data-strg/SEC/config/fortune500.json
    │       ├── get_finnhub_api_key()     →  Secret Manager → finnhub-api-key/latest
    │       ├── Check blob: prices/YYYY-MM-DD/data.jsonl
    │       │   └── if exists → no-op, exit 0
    │       ├── For each ticker:
    │       │   ├── fetch_quote(api_key, symbol)  →  Finnhub /v1/quote
    │       │   ├── On 429 → sleep 2s, retry once
    │       │   ├── serialize_quote()             →  JSON with symbol/timestamp/current/change/...
    │       │   ├── time.sleep(1.0)               →  rate limit
    │       │   └── track consecutive failures (abort if ≥5)
    │       ├── upload NDJSON to gs://raw-data-strg/prices/YYYY-MM-DD/data.jsonl
    │       └── exit 0
    │
    ▼ (trap fires)
gcloud compute instances stop data-ingest-vm ...
```

---

## 11. Key Design Patterns & Guardrails

1. **Rate limiting:** All external API clients enforce per-second request ceilings. SEC uses ≤10 req/s with throttling; Finnhub uses 1/s delay; GNews uses sleep(0.5) between batches.
2. **Gaslit retries:** API calls retry on rate limits and transient errors (exponential backoff + `Retry-After` header respect).
3. **Idempotency / dedup:** SEC checks `blob.exists()` before uploading. Prices skips the entire fetch if the day's blob already exists.
4. **Byte budgets:** SEC pipeline tracks bytes transferred and aborts if `max_ingest_gb` or `max_download_gb` is exceeded.
5. **Self-terminating VM:** SEC pipeline stops the VM in a `finally` block, ensuring shutdown even on errors.
6. **Off-GCP guardrail:** SEC pipeline refuses to run unless on GCP metadata server (or `ALLOW_LOCAL_EXECUTION=true`).
7. **Secret management:** API keys live in GCP Secret Manager. Cloud Function receives via `--set-secrets`; prices script fetches via `secretmanager_v1.SecretManagerServiceClient()`.
8. **Local fallback → GCS persistence:** If dynamic/rotating config (Fortune 500 roster) is missing from GCS, pipeline fetches fallback URL, bootstraps, and saves back to GCS.
9. **Type safety:** Python 3.10+ union syntax (`X | None`), `from __future__ import annotations`, dataclasses throughout.

---

## 12. Context Files (Business Context)

These files in `context/` provide the business/domain context for the Finance Tracker Dashboard. I cannot directly parse their binary contents, but they should be considered the source of truth for user stories, flows, and requirements:

- **`FTD_ Core User Flows.pdf`** — Likely contains end-to-end user journey maps for the dashboard.
- **`Mentorship App#1.pdf`** — Likely mentorship / app flow context (possibly related to client onboarding or stakeholder flows).
- **`UC_Master_Table v02 (3).xlsx`** — Use-case master table (UC = Use Cases). This is almost certainly the canonical backlog of features, likely with columns such as ID, Description, Priority, Status, Pipeline coverage, etc.

**IMPORTANT:** Future agents working on this repo should open these files first to understand the business requirements before touching ingestion code.

---

## 13. Kilo Workspace Config (`.kilo/`)

- **Agent Manager JSON** tracks two worktrees:
  - `wt-1782679017149-1` → branch `momentous-season` (parent: `rawdataingestion`)
  - `wt-1783894975295-1` → branch `alabaster-birch` (parent: `rawdataingestion`, active session `ses_0a792dbf9ffe7Xkp0xsnNnSJ31`)
- Worktree paths live under `.kilo/worktrees/`.

---

## 14. Common Commands

### SEC Pipeline
```bash
cd sec
bash scripts/provision_vm.sh                          # Create VM (idempotent)
bash scripts/install_dependencies.sh                   # Inside VM
cp .env.example .env && vim .env                       # Configure secrets
bash scripts/setup_cloud_scheduler.sh                  # Start SEC VM at 03:30 UTC
bash scripts/deploy_to_vm.sh                           # Push latest code to VM
```

### Prices / GNews deploy via CI
```bash
git commit -m "deploy" && git push origin rawdataingestion
# or
git commit -m "prices deploy" && git push origin rawdataingestion
git commit -m "gnews deploy" && git push origin rawdataingestion
```

### Start prices VM manually (after Cloud Function is deployed)
```bash
curl -X POST https://<region>-<project>.cloudfunctions.net/start-price-vm
```

---

## 15. Known Caveats & Gotchas

1. **SEC pipeline does NOT start automatically from this repo.** It requires manual `provision_vm.sh`, `.env`, and `setup_cloud_scheduler.sh` steps.
2. **Prices cron time is 22:00 UTC on the VM** (local VM clock, not a Cloud Scheduler job). The deploy workflow must scp `run.sh` and install the cron entry.
3. **VM is shared** between SEC and prices pipelines. The prices `run.sh` and SEC pipeline both stop the VM when done.
4. **All ticker normalizations:** `.` → `-` (e.g., `BRK.B` → `BRK-B`), uppercase, deduplicated.
5. **XBRL files are always skipped** in SEC ingestion.
6. **`ALLOW_LOCAL_EXECUTION=false`** is the default and production posture. Set to `true` ONLY for debug.
7. **GNews Cloud Function is Gen1** (`--no-gen2`). Memory/CPU scales to 1 instance max.
8. **Context folder files are business assets, not code.** Do not modify them; they are the project's source of truth for requirements.

---

## 16. Option 1 Implementation: Relational-Analytical Lakehouse Staging Pipeline

**Goal:** Process the three raw GCS data streams into schema-enforced, temporally-synchronized staging tables before any embedding occurs.

**Status:** Core local pipeline implemented, executed, and verified. BigQuery catalog deployed and verified on 2026-07-13.

### 16.1 10-K Bootstrap (Completed)

**Files:**
- `sec/src/fetch_10k.py` (new)
- `sec/src/filing_fetcher.py` (extended with `TenKFiling` and `extract_recent_10k_filings`)

**Behavior:**
- One-time manual script; no cron/scheduler.
- Resolves Fortune 500 tickers → CIKs via existing `company_roster.py`.
- Fetches single most recent 10-K per CIK from SEC `submissions/CIK.json`.
- Skips only clearly-raw-XBRL filenames (`.xml`, `-xbrl.htm`); keeps inline XBRL 10-Ks.
- Safety guard: aborts after 5 consecutive failures.
- Uploads to `gs://raw-data-strg/SEC/10-K/{CIK}/{accession_no_dashes}/{document}` + `metadata.txt`.
- Writes manifest to `SEC/logs/10k_bootstrap_manifest.json`.

**Current archive:** 495 10-K HTML files, one per company.

### 16.2 Lakehouse Module Structure

```
lakehouse/
├── __init__.py
├── config.py              # LakehouseSettings (reuses sec/src/config.py Settings)
├── requirements.txt
├── README.md
├── orchestrator.py        # Entry point: runs all tracks in sequence
├── engines/
│   ├── __init__.py
│   ├── fiscal_resolver.py # Extracts fiscal year-end from 10-K cover pages
│   ├── validation_core.py # Fortune 500 filter + normalized_calendar_date + date_precision
│   └── unified_staging.py # Concatenates all sources into single relation
└── pipelines/
    ├── __init__.py
    ├── finnhub_coercion.py    # prices NDJSON → structured DataFrame
    ├── gnews_normalizer.py    # gnews JSON → clean text DataFrame
    └── sec_shredder.py        # SEC 8-K/10-K HTML → structured rows
```

### 16.3 Pipeline Results (2026-07-13 Final Run)

**GCS staging output:** `gs://raw-data-strg/lakehouse/staging/`

| File | Rows | Notes |
|---|---|---|
| `staging_finnhub.parquet` | 4,473 | Filtered to Fortune 500 CIKs; null-timestamp records removed |
| `staging_gnews.parquet` | 73,980 | Cleaned text, tagged by ticker |
| `staging_sec.parquet` | 758,054 | 422 8-Ks + 990 10-Ks shredded, Fortune 500 filtered |
| `fiscal_parameters.parquet` | 477 | Fiscal year-end extracted from 10-Ks (96.4% success rate) |
| `unified_staging.parquet` | 836,507 | All sources concatenated; 0 null join keys |

**Total storage:** ~265 MB Parquet

### 16.4 Fiscal Resolver: Diagnosis and Fix

**Original success rate:** ~20% (197/990)  
**Current success rate:** 96.4% (477/495 HTML files)

**Root cause of failures:** Modern 10-Ks use inline XBRL with nested HTML tags inside `ix:nonNumeric` elements. The original regex patterns:
1. Looked for the wrong tag name (`dei:FiscalYearEndDate` instead of `dei:CurrentFiscalYearEndDate`)
2. Used `([^<]+)` which stops at the first nested tag like `<b>` or `<span>`

**Fix applied:** Rewrote `_extract_fy_from_html()` in `fiscal_resolver.py`:
1. Try visible text patterns first (legacy format)
2. Fall back to inline XBRL with `re.DOTALL` regex capturing full inner XML
3. Strip nested tags with `re.sub(r'<[^>]+>', '', raw)`
4. Extract year from `dei:DocumentFiscalYearFocus` and combine with month/day
5. Handle special formats like `--10-03` (day-month without year)

**Verified on:** 4 representative CIKs + full scan of all 495 10-K HTML files.

### 16.5 Date Precision and Fallback Chain

**Problem:** 31,004 SEC rows had `null` `normalized_calendar_date` because fiscal resolver failed for 18/495 CIKs and `period_of_report` was missing from SEC API.

**Fix:** Added `date_precision` column and 4-tier fallback chain in `validation_core.py`:

**For 10-Ks:**
1. `period_of_report` → `date_precision = 'exact_fiscal'`
2. `fiscal_year_end_date` from `fiscal_parameters` → `date_precision = 'fiscal'`
3. `filing_date` from SEC submissions API → `date_precision = 'event'`
4. `ingest_date` (our processing timestamp) → `date_precision = 'ingestion'`

**For 8-Ks:**
1. `filing_date` from SEC submissions API → `date_precision = 'event'`
2. `ingest_date` → `date_precision = 'ingestion'`

**No data is fabricated.** Every fallback is a real timestamp from a real source:
- SEC API (`periodOfReport`, `filingDate`)
- 10-K HTML cover page (`fiscal_year_end_date`)
- Our own processing system (`ingest_date`)

**Result:** 0 null `normalized_calendar_date` values in any table. All 836,507 unified rows have valid temporal coordinates.

**Distribution:**
- `fiscal`: 719,783 rows (from 10-K fiscal year-end)
- `event`: 38,271 rows (from SEC filing date)
- `exact_fiscal`: 0 rows (period_of_report not populated in SEC API for these filings)
- `ingestion`: 0 rows (not needed after fallback chain)

### 16.6 Finnhub Null Timestamp Filter

**Problem:** Raw price NDJSON contained 489 records with null `timestamp` and null `current` price. These incomplete API responses produced rows that could not participate in temporal joins.

**Fix:** Added explicit skip in `finnhub_coercion.py`: if `timestamp is None` or `current is None`, drop the record before DataFrame creation.

**Result:** 4,473 clean price rows (down from 4,957). All have valid `normalized_calendar_date`.

### 16.7 Validation Core Schema Preservation

**Fix:** Changed validation from stripping columns to preserving all source-specific columns while ensuring canonical columns exist. Canonical columns (`target_ticker`, `target_cik`, `element_type`, `content_body`, `normalized_calendar_date`, `ingest_date`) are listed first; source-specific extras follow.

**Result:**
- Finnhub retains price fields (`symbol`, `timestamp`, `current`, `change`, `percent_change`, `high`, `low`, `open`, `previous_close`)
- GNews retains text fields (`content_body`)
- SEC retains metadata fields (`element_id`, `accession_number`, `form_type`, `item_number`, `period_of_report`, `filing_date`, `date_precision`)

### 16.8 BigQuery Catalog (Deployed 2026-07-13)

**Files:**
- `lakehouse/catalog/bq_external.py` — generates `CREATE OR REPLACE EXTERNAL TABLE` DDL
- `lakehouse/catalog/bq_views.py` — generates `CREATE OR REPLACE VIEW` DDL
- `lakehouse/catalog/bq_external_tables.sql` — 5 external table definitions
- `lakehouse/catalog/bq_views.sql` — 4 view definitions

**External tables (deployed in `ftd2026.lakehouse`):**
- `ftd2026.lakehouse.staging_finnhub`
- `ftd2026.lakehouse.staging_gnews`
- `ftd2026.lakehouse.staging_sec`
- `ftd2026.lakehouse.unified_staging`
- `ftd2026.lakehouse.fiscal_parameters`

**Views (deployed in `ftd2026.analytics`):**
- `ftd2026.analytics.prices_mart` — price time-series with DATE dates
- `ftd2026.analytics.sentiment_mart` — GNews text with DATE dates
- `ftd2026.analytics.sec_elements_mart` — SEC elements with DATE dates
- `ftd2026.analytics.unified_financials` — cross-source queryable view

**Status:** Deployed and verified on 2026-07-13.

**Billing protection:** GCP budget alert set at $0.01 USD for project `ftd2026` (billing account `014789-893C12-EBA34F`). Alerts at 50% and 100% of budget.

### 16.9 Integrity Verification Results

| Check | Result |
|---|---|
| SEC `target_ticker` backfill | 0 nulls — all 758,054 rows populated |
| SEC `normalized_calendar_date` coverage | 0 nulls — fallback chain executed for all rows |
| Unified staging join keys | 0 nulls in `target_ticker`, `target_cik`, `normalized_calendar_date` |
| `date_precision` population | 100% of SEC rows labeled (`fiscal` or `event`) |
| Canonical columns present | All 3 staging tables + unified have required columns |
| Source-specific columns preserved | Finnhub price fields, SEC metadata fields all retained |
| BigQuery external table row counts | Match GCS exactly (4,473 / 73,980 / 758,054 / 836,507 / 477) |
| BigQuery view compilation | All 4 views created successfully |
| BigQuery DATE casting | `normalized_calendar_date` and `filing_date` cast to DATE in views |

### 16.10 Remaining Work

| Step | Status | Notes |
|---|---|---|
| Apply BigQuery external table DDL | **Completed** | 5 external tables deployed in `ftd2026.lakehouse` |
| Apply BigQuery view DDL | **Completed** | 4 views deployed in `ftd2026.analytics` |
| Verification cross-source joins | **Completed** | AAPL SEC-to-price join verified |
| Dataflow wrappers | **Not planned** | Current data volume (~520 MB) handled fine by local pandas |
| Iceberg catalog | **Not planned** | BigQuery external tables provide SQL queryability without Iceberg server |
| Airflow/Composer | **Not planned** | Manual `orchestrator.py` invocation is sufficient |
| Annual 10-K delta cron | **Not started** | 10-Ks are annual; not needed for initial bootstrap |

### 16.11 Run Command

```bash
cd /Users/isabellabutera/gcloud-bucket-data
PYTHONPATH=/Users/isabellabutera/gcloud-bucket-data:/Users/isabellabutera/gcloud-bucket-data/sec /Users/isabellabutera/gcloud-bucket-data/.venv/bin/python3 -m lakehouse.orchestrator
```

**Sample mode for fast testing:**
```bash
PYTHONPATH=/Users/isabellabutera/gcloud-bucket-data:/Users/isabellabutera/gcloud-bucket-data/sec /Users/isabellabutera/gcloud-bucket-data/.venv/bin/python3 -m lakehouse.orchestrator --sample 2
```

**Time cost:** ~17 minutes for full pipeline (mostly SEC HTML parsing).
**GCS storage cost:** ~265 MB total for Parquet staging files.
**Cloud cost:** $0 (all compute is local; BigQuery catalog not yet applied).

---

## 17. Post-Mortem: Issues Encountered and Fixes Applied

This section documents every significant failure, root cause, fix, and verification step encountered during Option 1 development.

### 17.1 Fiscal Resolver Low Success Rate

**Symptom:** Only ~20% of 10-K HTML files yielded a fiscal year-end date (197/990). The remaining 80% produced no date, leaving `normalized_calendar_date` null for thousands of SEC rows.

**Root Cause:** The regex patterns in `_extract_fy_from_html()` had two flaws:
1. They looked for `dei:FiscalYearEndDate`, but modern 10-Ks use `dei:CurrentFiscalYearEndDate`.
2. They used `([^<]+)` to capture text inside inline XBRL tags. Modern 10-Ks nest HTML tags like `<b>` and `<span>` inside `ix:nonNumeric` elements, so `([^<]+)` stopped at the first nested tag and returned empty or truncated text.

**Fix:** Rewrote `_extract_fy_from_html()` in `fiscal_resolver.py`:
1. Try visible text patterns first (legacy format).
2. Fall back to inline XBRL with `re.DOTALL` regex that captures the full inner XML.
3. Strip nested tags with `re.sub(r'<[^>]+>', '', raw)`.
4. Extract year from `dei:DocumentFiscalYearFocus` and combine with month/day.
5. Handle special formats like `--10-03` (day-month without year).

**Verification:** Full scan of all 495 10-K HTML files. Success rate increased from ~20% to 96.4% (477/495).

---

### 17.2 Null `normalized_calendar_date` in SEC Rows

**Symptom:** 31,004 SEC rows had `null` `normalized_calendar_date` after validation. These rows could not participate in temporal joins with Finnhub or GNews data.

**Root Cause:** The validation core only tried two fallbacks for 10-Ks: `period_of_report` → `fiscal_year_end_date`. For 18/495 CIKs, both were missing or unparseable. There was no further fallback, so the date remained null.

**Fix:** Added `date_precision` column and a 4-tier fallback chain in `_enrich_sec_dates()`:
- **10-Ks:** `period_of_report` → `fiscal_year_end_date` → `filing_date` → `ingest_date`
- **8-Ks:** `filing_date` → `ingest_date`

Each fallback is a real timestamp from a real source. No data is fabricated. The `date_precision` column labels which source provided the date: `exact_fiscal`, `fiscal`, `event`, or `ingestion`.

**Verification:** After re-running validation, 0 null `normalized_calendar_date` values in any staging table. All 836,507 unified rows have valid temporal coordinates.

---

### 17.3 Null `normalized_calendar_date` in Finnhub Rows

**Symptom:** 489 Finnhub price records had null `timestamp` and null `current` price. These incomplete API responses produced rows that could not participate in temporal joins.

**Root Cause:** The Finnhub NDJSON contains some records with null `timestamp` and null `current` price. These are incomplete API responses, not valid price quotes.

**Fix:** Added explicit skip in `load_price_frames()`: if `timestamp is None` or `current is None`, drop the record before it enters the DataFrame.

**Verification:** Price staging reduced from 4,957 to 4,473 rows (484 incomplete records removed). All remaining rows have valid `normalized_calendar_date`.

---

### 17.4 Null-Type Parquet Columns

**Symptom:** `content_body` in `staging_finnhub.parquet` and `period_of_report` in `staging_sec.parquet` were written as Parquet `null` type instead of `large_string`. BigQuery external tables may not surface null-type columns, which would break views referencing them.

**Root Cause:** In pandas, these columns contained Python `None` values. When PyArrow converted the DataFrame to Parquet, columns with all `None` values were inferred as `null` type rather than `string`.

**Fix:** Modified source code to write empty strings `""` instead of `None`:
- `finnhub_coercion.py`: Added `rec["content_body"] = ""` for every price row.
- `sec_shredder.py`: Changed `period_of_report=period_of_report or ""` and `filing_date=filing_date or ""`.
- `unified_staging.py`: Changed `df["form_type"] = ""` instead of `None`.

**Verification:** After re-running pipeline, PyArrow schema inspection showed no null-type columns in any Parquet file.

---

### 17.5 Decimal Price Columns Corrupted by `fillna("")`

**Symptom:** Pipeline crashed with `pyarrow.lib.ArrowTypeError: ('int or Decimal object expected, got str', 'Conversion failed for column current with type object')` when writing `unified_staging.parquet`.

**Root Cause:** The `_coerce_schema()` function in `validation_core.py` called `fillna("")` on all object columns. Finnhub price columns (`current`, `change`, etc.) are `Decimal` objects stored in object-dtype columns. `fillna("")` converted Decimals to strings like `"157.52"`. When PyArrow tried to serialize these strings into `decimal128` columns, it failed because strings are not valid decimal values.

**Fix:** Modified `_coerce_schema()` to skip non-string object columns during null filling:
```python
for col in df.select_dtypes(include=["object"]).columns:
    sample = df[col].dropna()
    if len(sample) > 0 and not isinstance(sample.iloc[0], str):
        continue
    df[col] = df[col].fillna("")
```

**Verification:** Re-ran pipeline. PyArrow successfully serialized all tables. Decimal prices preserved as `decimal128(7,3)` etc.

---

### 17.6 Finnhub Timestamp Format Mismatch

**Symptom:** All 4,473 Finnhub rows had null `timestamp` after the first pipeline run. `normalized_calendar_date` was also null.

**Root Cause:** The raw Finnhub NDJSON uses ISO 8601 strings like `"2026-07-10T20:00:00+00:00"`. The initial pipeline code attempted `int(timestamp)`, which fails on ISO strings and returns `None`. This propagated through the pipeline, making both `timestamp` and `normalized_calendar_date` null.

**Fix:** 
1. Pipeline now preserves the raw ISO string as-is.
2. `_coerce_schema()` converts it to `datetime64[us, UTC]` using `pd.to_datetime()`.
3. `normalized_calendar_date` is derived from the parsed timestamp.

**Verification:** After fix, all 4,473 rows have valid `timestamp` (type `datetime64[us, UTC]`) and `normalized_calendar_date` (type `timestamp[us]`).

---

### 17.7 8-K Support Gaps

**Symptom:** 8-K filings were processed but had no fiscal year-end metadata. The date fallback chain was designed only for 10-Ks.

**Root Cause:** 8-Ks are event-driven filings (e.g., CEO departure, merger agreement). They do not have `period_of_report` or fiscal year-end dates. The initial validation logic only handled 10-K date resolution.

**Fix:** Extended `_enrich_sec_dates()` with 8-K-specific logic:
- **Priority 1:** `filing_date` → `normalized_calendar_date` + `date_precision = 'event'`
- **Priority 2:** `ingest_date` → `normalized_calendar_date` + `date_precision = 'ingestion'`

**Verification:** All 422 8-K HTML files were shredded. All 8-K rows received `filing_date` from SEC submissions API. 0 null dates in 8-K rows.

---

### 17.8 Validation Core Dropping Source-Specific Columns

**Symptom:** Earlier versions of validation core projected to a fixed column list, stripping SEC metadata like `element_id`, `accession_number`, `period_of_report`, `filing_date`.

**Root Cause:** The validation code used a hardcoded column whitelist and dropped anything not in it.

**Fix:** Changed validation to preserve all existing columns and only add missing canonical ones. Canonical columns (`target_ticker`, `target_cik`, `element_type`, `content_body`, `normalized_calendar_date`, `ingest_date`) are listed first; source-specific extras follow.

**Verification:** Finnhub retains price fields. GNews retains text fields. SEC retains all metadata fields.

---

### 17.9 BigQuery Reserved Keyword Conflicts

**Symptom:** BigQuery DDL execution failed with `Syntax error: Expected ")" or "," but got keyword CURRENT` when creating external tables.

**Root Cause:** BigQuery reserved words like `timestamp` and `current` cannot be used as unquoted column names in DDL.

**Fix:** Backtick-quoted reserved keywords in all DDL files:
- `bq_external_tables.sql`: `` `timestamp` ``, `` `current` ``
- `bq_views.py`: `` `current` `` in `prices_mart`
- `bq_external.py`: Updated generator to quote reserved words

**Verification:** Re-ran DDL against BigQuery. All 5 external tables created successfully.

---

### 17.10 BigQuery View Dataset Reference Bug

**Symptom:** View DDL failed with `Not found: Table ftd2026:analytics.staging_finnhub` when creating views.

**Root Cause:** The view generator templates used `{project}.{dataset}.staging_finnhub` for the `FROM` clause, but views are created in the `analytics` dataset while external tables live in `lakehouse`. The `{dataset}` placeholder resolved to `analytics`, so views referenced `analytics.staging_finnhub` instead of `lakehouse.staging_finnhub`.

**Fix:** Hardcoded `lakehouse` in all view `FROM` clauses:
```sql
FROM `{project}.lakehouse.staging_finnhub`
```

**Verification:** All 4 views created successfully in `ftd2026.analytics`. Cross-source joins verified.

---

### 17.11 Pipeline Progress Appeared Stuck

**Symptom:** During SEC shredding, the pipeline showed no new log output for 15-20 minutes at a time. Appeared frozen.

**Root Cause:** SEC HTML parsing is CPU-bound and slow. The shredder processes 1,412 HTML files (422 8-Ks + 990 10-Ks), each requiring BeautifulSoup parsing, boilerplate removal, and table-to-Markdown conversion. This is inherently slow on a single core.

**Fix:** No code fix needed. This is expected behavior. The pipeline was working; it just takes ~20 minutes for the SEC track. Added process monitoring (`ps aux`) to confirm it was still running.

**Verification:** Pipeline completed successfully in ~25 minutes total.

---

### 17.12 GCS File Deletion and Re-run Strategy

**Symptom:** After discovering corrupted Finnhub timestamps and null-type columns in the first pipeline run, the existing Parquet files on GCS contained flawed schemas.

**Root Cause:** The pipeline overwrites files in place. There was no versioning or backup of staging outputs.

**Fix:** Before re-running, deleted all 5 flawed Parquet files from GCS:
```bash
gsutil rm gs://raw-data-strg/lakehouse/staging/*.parquet
```
Then ran the pipeline once with all fixes applied.

**Verification:** New Parquet files have correct schemas: 0 null-type columns, proper temporal types, preserved Decimal prices.

---

### Summary Table

| Issue | Impact | Fix | Verification |
|---|---|---|---|
| Fiscal resolver 20% success | 18 CIKs missing dates | DOTALL regex + correct XBRL tags | 477/495 = 96.4% |
| 31,004 null SEC dates | Unjoinable rows | 4-tier fallback + `date_precision` | 0 null dates |
| 484 null Finnhub dates | Unjoinable price rows | Skip null-timestamp records | 4,473 clean rows |
| Null-type Parquet cols | BQ external tables may hide cols | Write `""` instead of `None` | 0 null types in schema |
| Decimal corruption | Pipeline crash | Skip non-string cols in `fillna` | PyArrow round-trip OK |
| Finnhub timestamp format | All timestamps null | Preserve ISO string, parse later | `datetime64[us, UTC]` |
| 8-K date gaps | 8-K rows unjoinable | `filing_date` fallback for 8-Ks | 0 null dates in 8-Ks |
| Column stripping | Lost SEC metadata | Preserve all columns | Source-specific fields retained |
| BQ reserved keywords | DDL syntax error | Backtick-quote `timestamp`, `current` | All tables created |
| View dataset reference | Views pointed to wrong dataset | Hardcode `lakehouse` in FROM | All views created |
| Slow SEC parsing | Appeared stuck | No fix needed; expected behavior | Pipeline completed |
| Flawed GCS files | Bad schemas persisted | Delete + re-run pipeline | Clean schemas verified |
