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

---

## 18. PostgreSQL Migration (In Progress)

### 18.1 New VM Provisioned

Created `ftd-postgres-vm` (e2-micro, us-west2-a) for PostgreSQL.  
Public access prevention enforced on bucket `processed-layer-one`.  
PostgreSQL 15.18 installed, database `ftd_lakehouse` created, user `ftd_app` created.  
Firewall rules created for user IPv4/IPv6 on TCP 5432.

**Credentials saved:**
```
Host: 34.94.89.135
Port: 5432
Database: ftd_lakehouse
Username: ftd_app
Password: 5Ou+BkyuQT3izP72219jMLy2AobRdI3f
```

### 18.2 Code Changes for PostgreSQL Output

Added `--postgres` flag to orchestrator. New `postgres_writer.py` module with `write_frame()` using `psycopg2.extras.execute_values`.  
Modified `config.py` to add PostgreSQL connection fields and `postgres_enabled` property.  
Removed `frozen=True` from `LakehouseSettings` to allow runtime env var population.

### 18.3 Issues Encountered

**SSH session drops killing background processes:**  
`gcloud compute ssh` terminates background processes when the session ends. Fixed by using `nohup` and `tee` for logging.

**Memory pressure on e2-micro:**  
Loading large DataFrames + `execute_values` with full list caused OOM. Fix applied: changed `write_frame` to use generator (`_row_generator`) instead of building full list in memory.

**Network path failure:**  
External IP `34.94.89.135` timed out from `data-ingest-vm`. Fixed by using internal IP `10.168.0.3` (VPC internal traffic allowed).

**Finnhub/GNews paths:**  
Pipeline looks for `prices/` and `gnews/` in `processed-layer-one` bucket, but raw data still lives in `raw-data-strg`. These tracks return empty. SEC data works because it was moved to `processed-layer-one`.

**`--sample` mode limitation:**  
`--sample 100` only limits initial SEC shredding. Validation Core loads full Parquet files from GCS, so PostgreSQL receives full dataset regardless of sample flag.

### 18.4 Current Status (Completed 2026-07-16)

- PostgreSQL VM running, database and user created
- All 5 tables successfully written to PostgreSQL:
  - `staging_finnhub`: 4,473 rows
  - `staging_gnews`: 73,980 rows
  - `staging_sec`: 758,054 rows
  - `fiscal_parameters`: 477 rows
  - `unified_staging`: 836,507 rows
- Finnhub/GNews bucket paths fixed to read from `raw-data-strg`
- `--sample` mode now limits all tracks (SEC, Finnhub, GNews, validation, unified)
- PostgreSQL writer uses `execute_values` with generator for memory efficiency
- Auto-creates tables with correct types (`TIMESTAMP`, `NUMERIC`, `TEXT`)
- Full pipeline run completed successfully in ~45 minutes

---

## 19. Bucket Migration: raw-data-strg → processed-layer-one

Moved all `gs://raw-data-strg/lakehouse/staging/*.parquet` to `gs://processed-layer-one/lakehouse/staging/`.  
Deleted CSV duplicates from `processed-layer-one`.  
Updated `lakehouse/config.py` to use `raw_data_gcs_bucket` for raw inputs and `gcs_bucket` for processed outputs.  
Row counts verified: 4,473 / 73,980 / 758,054 / 836,507 / 477.

---

## 20. App Development Plan: Backend API + Swagger (Experimental)

### 20.1 Context Documents Analyzed

**UC_Master_Table v02 (3).xlsx** — Contains 49 use cases across 10 requirements:
- Data Ingestion (Alpha Vantage, Reddit, SEC EDGAR) — already implemented
- Data Pipelines (parse, clean, vectorize, RAG, scoring) — partially implemented
- Data Mapping (NER, CIK lookup, ticker mapping)
- User Creation & Authentication
- Search (keyword, semantic vector, multi-hop, caching)
- Workspace management
- Audit trail
- Timeline (narrative history, alerts, export)
- Dashboard (ticker research, < 3s load)

**FTD_ Core User Flows.pdf** — 7 user flows:
1. Account Registration & Onboarding
2. Ticker Keyword Search & Dashboard Analysis
3. Workspace Creation & Asset Tracking
4. Navigating and Exporting Historical Narrative Timeline
5. Advanced Multi-Hop Querying & Context Chat (RAG)
6. Crowdsourced Error Reporting & Mapping Overrides
7. Administrative Mapping Review and Validation

**Mentorship App#1.pdf** — 12-week learning plan:
- Phase 1 (Weeks 1-4): Cloud foundations, data modeling, ingestion, serverless
- Phase 2 (Weeks 5-8): AI/LLM APIs, vector DBs, RAG, function calling
- Phase 3 (Weeks 9-12): Integration, UI, CI/CD, monitoring

### 20.2 What We Have Now

**PostgreSQL schema (5 tables, ~1.45 GB):**

| Table | Rows | Purpose |
|---|---|---|
| `staging_finnhub` | 4,473 | Price quotes (current, change, high, low, etc.) |
| `staging_gnews` | 73,980 | News article text content |
| `staging_sec` | 758,054 | SEC filing elements (8-K/10-K text sections) |
| `fiscal_parameters` | 477 | Fiscal year-end dates per CIK |
| `unified_staging` | 836,507 | Combined view of all sources |

**What exists:**
- Relational, queryable financial data in PostgreSQL
- Fortune 500 ticker coverage with CIK mappings
- Temporal coverage via `normalized_calendar_date` and `ingest_date`
- Source attribution (`source`, `form_type`, `accession_number`)
- No embeddings, no vector columns, no user tables, no auth

### 20.3 What Is Out of Scope (Do Not Build Yet)

**Explicitly excluded from this phase:**
- Embeddings / vector search (requires `text-embedding-3-small` + pgvector)
- RAG inference engine (requires embeddings + LLM API integration)
- User authentication & JWT sessions (requires `users` table, bcrypt, Firebase/Cloud Function)
- User workspaces (requires `workspaces`, `workspace_tickers` tables)
- Narrative state / timeline (requires `narrative_state` table with append-only history)
- Hype vs. Evidence scoring (requires `ticker_scores` table + weighted calculation engine)
- Mapping confidence queue (requires `mapping_review`, `errors` tables)
- Caching layer (requires Redis/Memorystore)
- Background workers / Cloud Run jobs for async processing
- Frontend UI (React, Streamlit, etc.)
- Any code that modifies existing data (write endpoints)

### 20.4 Stopping Point Definition

**STOP at:** Backend data-access layer and business logic that queries PostgreSQL directly — **no HTTP API layer, no endpoints, no Swagger, no frontend integration yet.**

**Specifically, this means:**
1. Python modules/functions that encapsulate queries against the 5 PostgreSQL tables
2. Business logic for the app\'s specific purposes (ticker search, dashboard aggregation, timeline building, etc.)
3. Direct psycopg2 (or asyncpg) database access — no HTTP server, no FastAPI, no Flask
4. Pydantic models for response typing and validation (optional but recommended)
5. Importable, testable Python code — not yet wrapped in routes or endpoints
6. No database writes from this layer (read-only against staging tables)
7. No authentication, no CORS, no Docker, no Cloud Run deployment

**What this phase produces:**
- A Python package (e.g., `app/` or `backend/`) with functions like:
  - `get_ticker_search(query) -> list[TickerResult]`
  - `get_ticker_prices(ticker, start, end) -> list[PriceRow]`
  - `get_ticker_news(ticker, start, end, limit) -> list[NewsRow]`
  - `get_ticker_filings(ticker, start, end, form_type) -> list[FilingSummary]`
  - `get_filing_elements(accession_number) -> list[ElementRow]`
  - `get_ticker_timeline(ticker, start, end) -> list[TimelineEvent]`
  - `search_content(keyword, source) -> list[SearchResult]`
- A `db.py` connection utility
- A `models.py` with Pydantic schemas
- Possibly a SQL scripts folder for raw queries and view creation

**What this phase does NOT produce:**
- HTTP server (no `uvicorn`, no FastAPI app)
- No `@app.get("/tickers")` route decorators
- No `/docs` or Swagger UI
- No CORS configuration
- No Dockerfile or containerization
- No Cloud Run deployment
- No frontend calling code

### 20.5 Methods to Build the API

**Recommended stack:**
- **Framework:** FastAPI (Python) — auto-generates Swagger, async support, type hints
- **Database driver:** psycopg2 or asyncpg (raw SQL or SQLAlchemy Core)
- **Validation:** Pydantic v2 models for request/response schemas
- **Deployment:** Docker container → GCP Cloud Run (or local dev)
- **Documentation:** Built-in Swagger UI (`/docs`) + ReDoc (`/redoc`)

**Architecture pattern:**
```
Frontend (not built)
    │
    │ HTTPS/REST
    ▼
FastAPI Backend
    │
    │ psycopg2 / asyncpg
    ▼
PostgreSQL (ftd_lakehouse on ftd-postgres-vm)
```

**Endpoint categories to implement:**

| Category | Endpoints | Source Table |
|---|---|---|
| Ticker Search | `GET /tickers?q={query}` | `unified_staging` (distinct tickers) |
| Price Data | `GET /tickers/{ticker}/prices?start=&end=` | `staging_finnhub` |
| News/Articles | `GET /tickers/{ticker}/news?start=&end=&limit=` | `staging_gnews` |
| SEC Filings | `GET /tickers/{ticker}/filings?start=&end=&form_type=` | `staging_sec` |
| Filing Elements | `GET /filings/{accession_number}/elements` | `staging_sec` |
| Fiscal Calendar | `GET /tickers/{ticker}/fiscal-year-end` | `fiscal_parameters` |
| Unified Timeline | `GET /tickers/{ticker}/timeline?start=&end=` | `unified_staging` |
| Keyword Search | `GET /search?q={keyword}&source={finnhub|gnews|sec}` | `unified_staging` (ILIKE) |

**Implementation steps (no code yet, just plan):**
1. Initialize FastAPI project structure (`main.py`, `models.py`, `db.py`, `routes/`)
2. Define Pydantic schemas for each table's response shape
3. Create database connection utility (singleton or dependency)
4. Implement read-only SQL queries with parameterized filters
5. Add CORS middleware
6. Verify Swagger UI renders at `/docs`
7. Test each endpoint with sample requests
8. (Optional) Dockerize for Cloud Run deployment



---

## 21. Use Case Feasibility Analysis (PostgreSQL Data-Access Layer Phase)

This section evaluates every use case from `UC_Master_Table v02 (3).xlsx` against the current PostgreSQL schema and the data-access layer scope (read-only Python functions querying the 5 existing staging tables).

### 21.1 Current Schema Reality Check

**Tables we HAVE:**
- `staging_finnhub` (4,473 rows) — price quotes
- `staging_gnews` (73,980 rows) — news article text
- `staging_sec` (758,054 rows) — SEC filing elements
- `fiscal_parameters` (477 rows) — fiscal year-end dates
- `unified_staging` (836,507 rows) — combined view of all sources

**Tables we DO NOT have (but UC expects):**
- `users`, `workspaces`, `workspace_tickers`
- `narrative_state` (append-only timeline history)
- `ticker_scores` (hype vs. evidence metrics)
- `mapping_review`, `errors` (mapping confidence queue)
- `document_embeddings` (vector search)
- `inference_results` (RAG outputs)

**Infrastructure we DO NOT have:**
- pgvector extension
- LLM API integration (OpenAI/Anthropic/Gemini)
- Redis / Memorystore
- Pub/Sub
- Authentication (JWT, bcrypt, Firebase)
- Cloud Run jobs / background workers

### 21.2 Use Case Feasibility Matrix

| UC | Title | Implementable Now? | Reasoning |
|---|---|---|---|
| **REQ-001: Data Ingestion** |
| UC-Ingest-01 | Schedule & Trigger Alpha Vantage News Fetch | **No** | We don't have Alpha Vantage. Our news source is GNews (different API, different schema). Ingestion scheduling is handled by Cloud Functions / Cloud Scheduler, not the data-access layer. |
| UC-Ingest-02 | Ingest & Stage Raw News Article Records | **No** | This is a write/ingestion process (dedup, hash, insert). Our data-access layer is strictly read-only. The staging already happened in the lakehouse pipeline. |
| UC-Ingest-03 | Schedule & Trigger Reddit Community Post Fetch | **No** | We have no Reddit pipeline. Our social data source is GNews only. |
| UC-Ingest-04 | Ingest & Stage Raw Reddit Post Records | **No** | No Reddit data exists. Also a write/ingestion process. |
| UC-Ingest-05 | Schedule & Trigger SEC EDGAR Filing Fetch | **No** | Our SEC ingestion is already handled by `sec/src/main.py` + Cloud Scheduler. This UC describes a different technical approach (Lambda/Cloud Run) but the data-access layer doesn't touch scheduling. |
| UC-Ingest-06 | Ingest & Stage Raw EDGAR Filing Records | **No** | This describes HTML/XBRL parsing and staging into `sec_filings` table. Our pipeline already shreds SEC filings into `staging_sec`. The data-access layer reads the output; it doesn't perform the ingestion. |
| **REQ-002: Data Pipelines** |
| UC-Pipe-01 | Parse & Clean News Article Text | **No** | Already completed in `gnews_normalizer.py`. The data-access layer consumes cleaned text; it doesn't perform cleaning. |
| UC-Pipe-02 | Vectorize & Index News Article | **No** | Requires `text-embedding-3-small` API + pgvector extension. Neither exists. Explicitly out of scope for this phase. |
| UC-Pipe-03 | Parse & Clean Reddit Post Text | **No** | No Reddit data. Also already a pipeline concern. |
| UC-Pipe-04 | Vectorize & Index Community Post | **No** | No Reddit data + no embeddings infrastructure. |
| UC-Pipe-05 | Extract & Normalize EDGAR Filing Data | **No** | Already completed in `sec_shredder.py` + `fiscal_resolver.py`. The data-access layer consumes the normalized output. |
| UC-Pipe-06 | Vectorize & Index Filing Sections | **No** | Requires embeddings + pgvector. Out of scope. |
| UC-Pipe-07 | Execute RAG Inference & Prompt Assembly | **No** | Requires embeddings + LLM API + vector search. This is the AI inference layer, not data access. |
| UC-Pipe-08 | Generate Hype vs. Evidence Score | **No** | Requires a `ticker_scores` table and a scoring engine that doesn't exist yet. No schema to query. |
| UC-Pipe-09 | Persist Narrative State Update | **No** | Requires `narrative_state` table with append-only history. This table doesn't exist. The logic also requires detecting composite score shifts >= 10 points, which depends on UC-Pipe-08. |
| **REQ-003: Data Mapping** |
| UC-Map-01 | Map News Article Entity to Ticker Symbol | **No** | Our pipeline already maps articles to tickers via `target_ticker` (set during ingestion using the Fortune 500 ticker list). The UC describes NER + fuzzy matching at ingestion time, which is a pipeline concern. The data-access layer just reads the already-mapped data. |
| UC-Map-02 | Map EDGAR Filing to Ticker via CIK Lookup | **No** | Already handled in `company_roster.py` and the SEC pipeline. `staging_sec` already has `target_cik` and `target_ticker`. The mapping is complete; the data-access layer reads it. |
| UC-Map-03 | Map Reddit Post to Ticker via Mention Detection | **No** | No Reddit data. |
| UC-Map-04 | Validate & Audit Mapping Confidence | **No** | Requires `mapping_review` table and admin dashboard UI. Neither exists. |
| UC-Map-05 | Flag and Log Mapping Error (User-Reported) | **No** | Requires `errors` table and a write endpoint for users to submit reports. Neither exists. Also requires user authentication. |
| **REQ-004: User Creation** |
| UC-User-01 | Register Account | **No** | Requires `users` table, email validation, bcrypt password hashing, confirmation email. None of this exists. |
| UC-User-02 | Recover Account | **No** | Requires `users` table + password reset token mechanism. |
| **REQ-005: Authentication** |
| UC-Auth-01 | Login & Credential Validation | **No** | Requires `users` table, JWT issuance, credential validation against stored hashes. |
| UC-Auth-02 | Session Lifecycle Management | **No** | Requires JWT tokens, Redis for session storage, token rotation logic. |
| **REQ-006: Search** |
| UC-Search-01 | Execute User Keyword Search | **Partial** | **Implementable:** Search by ticker symbol (`target_ticker ILIKE`). **Not implementable:** Company name search (no company name lookup table — we only have ticker symbols). Hype/evidence scores (no `ticker_scores` table). Narrative summaries (require aggregation/LLM). |
| UC-Search-02 | Rank & Return Search Results | **No** | Requires weighted scoring combining semantic similarity (embeddings) with metadata. We have no embeddings and no ranking engine. |
| UC-Search-03 | Filter Search Results by Date Range | **Partial** | **Implementable:** Date range filtering is a query parameter (`WHERE normalized_calendar_date >= %s AND <= %s`). This is a feature of any search function, not a standalone endpoint. |
| UC-Search-04 | Execute Semantic Vector Search | **No** | Requires pgvector extension + pre-computed embeddings. Neither exists. |
| UC-Search-05 | Augment LLM Prompt with Retrieved Context | **No** | Requires LLM API + embeddings + vector search. This is the RAG inference layer. |
| UC-Search-06 | Decompose & Execute Multi-Hop Query | **No** | Requires LLM query router + parallel execution orchestration. |
| UC-Search-07 | Cache & Return Repeated Search and Inference Results | **No** | Requires Redis / Memorystore for caching. |
| **REQ-007: Workspace** |
| UC-Work-01 | Create & Manage Research Workspace | **No** | Requires `workspaces` table, soft-delete logic, and write endpoints. |
| UC-Work-02 | Add & Remove Ticker from Workspace | **No** | Requires `workspace_tickers` join table, 50-ticker limit enforcement, cache invalidation signal. |
| **REQ-008: Audit Trail** |
| UC-Audit-01 | Source Link Management & Integrity Validation | **No** | Requires scheduled URL validation job, `source_url` column tracking, broken-link flagging. Our current schema has no URL column and no validation mechanism. |
| **REQ-009: Timeline** |
| UC-Time-01 | Render & Navigate Narrative Timeline | **Partial** | **Implementable:** Chronological query of `unified_staging` with `ORDER BY normalized_calendar_date` and pagination (LIMIT/OFFSET). **Not implementable:** The actual timeline rendering (UI), lazy-loading protocol (requires HTTP), and linking to source documents (requires URL storage). Also, the UC references `narrative_state` table which we don't have; `unified_staging` is the closest substitute. |
| UC-Time-02 | Set Alerts & Export Timeline View | **No** | Requires Pub/Sub for alerts and export generation (PDF/CSV). Neither infrastructure exists. |
| **REQ-010: Dashboard** |
| UC-Dash-01 | Render Ticker Research Dashboard | **No** | This is a frontend/UI requirement. The underlying data queries (prices, news, filings, scores) can be implemented individually, but "render dashboard" with < 3s load is a frontend + aggregation concern. Materialized views would help but require schema changes. |

### 21.3 What IS Implementable in This Phase

Based on the analysis above, the data-access layer can implement **query functions** for these app purposes:

| Functionality | Supported By | UC Mapping |
|---|---|---|
| Ticker search by symbol | `unified_staging.target_ticker` ILIKE | UC-Search-01 (partial) |
| Price time-series | `staging_finnhub` by ticker + date range | UC-Search-03 (partial) |
| News article retrieval | `staging_gnews` by ticker + date range | UC-Search-01 (partial) |
| SEC filing list | `staging_sec` aggregated by `accession_number` | UC-Search-01 (partial) |
| SEC filing elements | `staging_sec` by `accession_number` | UC-Search-01 (partial) |
| Fiscal year-end lookup | `fiscal_parameters` joined to `staging_sec` | UC-Map-02 (partial — already mapped) |
| Unified timeline | `unified_staging` by ticker + date range + source filter | UC-Time-01 (partial) |
| Keyword/content search | `unified_staging.content_body` ILIKE | UC-Search-01 (partial) |

**Common pattern:** Every implementable function is a **parameterized SELECT query** against one of the 5 existing tables. No joins to non-existent tables. No writes. No embeddings. No LLM calls.

### 21.4 What Is NOT Implementable and Why

| Category | UCs | Why Not Now | When It Becomes Possible |
|---|---|---|---|
| **Data Ingestion** | UC-Ingest-01 through 06 | Different pipelines (Alpha Vantage, Reddit) or already completed by lakehouse pipeline. Ingestion is not a data-access concern. | Never for Alpha Vantage/Reddit unless those pipelines are built. SEC ingestion is already done. |
| **Data Pipelines (processing)** | UC-Pipe-01, 03, 05 | Already completed in `lakehouse/pipelines/`. The data-access layer consumes their output. | N/A — already done |
| **Data Pipelines (AI/embeddings)** | UC-Pipe-02, 04, 06, 07, 08, 09 | Require embeddings (pgvector + API), LLM calls, scoring engine, narrative_state table. None of this schema or infrastructure exists. | After Phase 2 of the learning plan (Weeks 5-8) when vector DBs and LLM APIs are introduced |
| **Data Mapping (ingestion-time)** | UC-Map-01, 02, 03 | Already completed by pipeline. `target_ticker` and `target_cik` are already populated in all staging tables. | N/A — already done |
| **Data Mapping (admin/review)** | UC-Map-04, 05 | Require `mapping_review` and `errors` tables + admin UI + user auth. | After user auth is implemented (REQ-004/005) |
| **User Creation** | UC-User-01, 02 | Require `users` table, email service, password hashing. | When auth infrastructure is built |
| **Authentication** | UC-Auth-01, 02 | Require `users` table + JWT + Redis sessions. | After user table exists |
| **Search (semantic/LLM)** | UC-Search-02, 04, 05, 06, 07 | Require embeddings, LLM API, Redis cache. | After Phase 2 AI infrastructure is in place |
| **Workspace** | UC-Work-01, 02 | Require `workspaces` table + user auth + write endpoints. | After user auth is implemented |
| **Audit Trail** | UC-Audit-01 | Requires URL validation infrastructure and source_url tracking. | When ingestion pipelines are updated to store URLs |
| **Timeline (UI/alerts)** | UC-Time-02 | Requires Pub/Sub, export generation, alert subscription logic. | After core timeline query exists and notification infra is added |
| **Dashboard** | UC-Dash-01 | Frontend/UI requirement. Underlying data queries can be built, but rendering/aggregation is a later step. | After data-access layer exists and frontend development begins |

### 21.5 The Exact Scope for This Phase

**Build these Python functions (read-only against existing tables):**

| Function | SQL Pattern | Returns |
|---|---|---|
| `search_tickers(query, limit)` | `SELECT DISTINCT target_ticker, target_cik FROM unified_staging WHERE target_ticker ILIKE %s LIMIT %s` | `list[TickerResult]` |
| `get_ticker_prices(ticker, start, end)` | `SELECT ... FROM staging_finnhub WHERE target_ticker = %s AND date BETWEEN %s AND %s ORDER BY date` | `list[PriceRow]` |
| `get_ticker_news(ticker, start, end, limit)` | `SELECT ... FROM staging_gnews WHERE target_ticker = %s AND date BETWEEN %s AND %s ORDER BY ingest_date DESC LIMIT %s` | `list[NewsRow]` |
| `get_ticker_filings(ticker, start, end, form_type)` | `SELECT ... FROM staging_sec WHERE target_ticker = %s AND filing_date BETWEEN %s AND %s AND form_type = %s GROUP BY accession_number` | `list[FilingSummary]` |
| `get_filing_elements(accession_number, item_number, element_type)` | `SELECT ... FROM staging_sec WHERE accession_number = %s AND ... ORDER BY item_number` | `list[ElementRow]` |
| `get_ticker_fiscal_year_end(ticker)` | `SELECT ... FROM fiscal_parameters JOIN staging_sec USING (target_cik) WHERE target_ticker = %s LIMIT 1` | `FiscalYearEnd` |
| `get_ticker_timeline(ticker, start, end, sources, limit, offset)` | `SELECT ... FROM unified_staging WHERE target_ticker = %s AND date BETWEEN %s AND %s AND source = ANY(%s) ORDER BY date DESC LIMIT %s OFFSET %s` | `list[TimelineEvent]` |
| `search_content(keyword, source, limit)` | `SELECT ... FROM unified_staging WHERE content_body ILIKE %s AND source = %s LIMIT %s` | `list[SearchResult]` |

**Supporting infrastructure:**
- `app/db.py` — connection pool, query executor
- `app/models.py` — Pydantic schemas for all response shapes
- `app/queries/` — raw SQL strings organized by domain
- `app/services/` — Python functions that execute queries and return models

**Explicitly NOT building:**
- No HTTP server, routes, or endpoints
- No FastAPI, Flask, or web framework
- No Swagger, OpenAPI, or API docs
- No CORS, no auth middleware
- No Docker, no Cloud Run, no deployment
- No frontend code
- No schema changes to PostgreSQL
- No write operations from this layer



---

## 22. Frontend Wiring Plan: React Prototype → FastAPI Backend

### 22.1 What We Are Doing Now

We are wiring the Figma prototype (React + Vite + Tailwind app in `context/Create Full HD Prototype/`) to the FastAPI backend we built in Phase 2. This means replacing hardcoded mock data arrays in `App.tsx` with `fetch()` calls to our running API endpoints.

**What changes:** Only the data source in React components. No new endpoints, no backend changes, no schema changes.

**What stays the same:** Component structure, navigation, styling, tabs, modals, all UI logic.

### 22.2 The Figma Prototype Architecture

The prototype is a single-file React app (`src/app/App.tsx`, ~2745 lines) with:
- React state (`page`, `activeTab`, `selectedTicker`) drives navigation
- Mock arrays defined at the top: `TICKERS`, `NEWS_ARTICLES`, `TIMELINE_EVENTS`, `WORKSPACES`, `ALERTS_DATA`, `CHAT_HISTORY`
- Every screen reads from these arrays directly
- No HTTP calls, no API integration, no auth

**Key navigation pattern:**
```typescript
const [page, setPage] = useState<Page>("landing");
const navigate = (p: Page) => setPage(p);
// Buttons call navigate("dashboard"), navigate("ticker"), etc.
```

### 22.3 What "Wiring to API" Means (Detailed)

For each screen that displays data, we replace the mock array source with a `fetch()` call:

**Example — Landing Page Search:**
```typescript
// BEFORE (mock):
const results = TICKERS.filter(t => t.symbol.toLowerCase().includes(query));

// AFTER (real API):
const [results, setResults] = useState([]);
useEffect(() => {
  fetch(`http://localhost:8000/tickers/search?q=${query}&limit=20`)
    .then(res => res.json())
    .then(setResults);
}, [query]);
```

**Example — Ticker Dashboard News Tab:**
```typescript
// BEFORE (mock):
const articles = NEWS_ARTICLES.filter(a => a.ticker === ticker);

// AFTER (real API):
const [articles, setArticles] = useState([]);
useEffect(() => {
  fetch(`http://localhost:8000/tickers/${ticker}/news?start=2026-01-01&end=2026-07-17&limit=50`)
    .then(res => res.json())
    .then(setArticles);
}, [ticker]);
```

**Pattern for every screen:**
1. Replace `const data = MOCK_ARRAY.filter(...)` with `useState` + `useEffect` + `fetch()`
2. Map over state variable instead of mock array in JSX
3. Add loading state (`setLoading(true/false)`) during fetch
4. Add error handling (fallback to empty array on error)

### 22.4 Exact Screens to Wire

| Screen | Mock Source | API Endpoint | CRUD Function |
|---|---|---|---|
| Landing page search bar | `TICKERS` (filtered) | `GET /tickers/search?q=` | `search_tickers()` |
| Dashboard ticker cards | `TICKERS` (all) | `GET /tickers/search?q=` | `search_tickers()` |
| Search results page | `TICKERS` (filtered) | `GET /tickers/search?q=` | `search_tickers()` |
| Ticker dashboard — header | `TICKERS[0]` fields | `GET /tickers/{ticker}/prices` (latest) | `get_ticker_prices()` |
| Ticker dashboard — Prices tab | `TICKERS[0].priceHistory` | `GET /tickers/{ticker}/prices?start=&end=` | `get_ticker_prices()` |
| Ticker dashboard — News tab | `NEWS_ARTICLES` | `GET /tickers/{ticker}/news?start=&end=&limit=` | `get_ticker_news()` |
| Ticker dashboard — Filings tab | custom mock | `GET /tickers/{ticker}/filings` | `get_ticker_filings()` |
| Ticker dashboard — Timeline tab | `TIMELINE_EVENTS` | `GET /tickers/{ticker}/timeline?start=&end=&sources=&limit=&offset=` | `get_ticker_timeline()` |
| Filings page (list) | custom mock | `GET /tickers/{ticker}/filings` | `get_ticker_filings()` |
| Filings page (detail) | custom mock | `GET /filings/{accession_number}/elements` | `get_filing_elements()` |
| Search page (keyword) | `TICKERS` + `NEWS_ARTICLES` (filtered) | `GET /search?q=` | `search_content()` |

**NOT wired (mock only):**
- Login, register, forgot password, verify email, onboarding screens — mock navigation only
- Account settings — mock tabs
- Workspaces page — mock data, no API
- Alerts page — mock data, no API
- AI Chat page — mock data, no LLM
- Admin pages — mock data, no API
- Dashboard stats (tickers tracked, articles analyzed) — hardcoded counters

### 22.5 What Stays Mock (Not Wired)

| Screen | Why It Stays Mock |
|---|---|
| Login / Register / Forgot Password / Verify Email / Onboarding | Mentor said mock users and some but not all auth. These are navigation flows, not data screens. |
| Account Settings | Requires auth user context — deferred. |
| Workspaces | Requires `workspaces` table + auth — deferred. |
| Alerts | Requires scoring engine + `narrative_state` — deferred. |
| AI Chat | Requires LLM/embeddings — deferred. |
| Admin pages | Requires mapping queue tables + auth — deferred. |
| Dashboard stats counters | Hardcoded UI chrome, not real data. Could be wired later. |

### 22.6 Technical Implementation Details

**No proxy needed.** React dev server runs on `localhost:5173`, FastAPI on `localhost:8000`. CORS is already configured for this origin.

**Environment:** React will use a plain `BASE_URL` constant:
```typescript
const API_BASE = "http://localhost:8000";
```
No `.env` file needed for this. Hardcoded for local dev. Production would use an environment variable.

**State management:** Each component manages its own data state. No Redux, no Context API for data fetching. Simple `useState` + `useEffect` per screen.

**Date handling:** The Figma prototype uses JS `Date` objects and date strings. The API returns ISO date strings (`YYYY-MM-DD`). We'll format dates in React components as needed.

**Error handling:** Generic fallbacks:
```typescript
fetch(url)
  .then(res => res.json())
  .then(setData)
  .catch(() => setData([])); // show empty state on error
```

**Loading states:** Simple boolean:
```typescript
const [loading, setLoading] = useState(true);
// show spinner or skeleton while loading
```

### 22.7 Strict Stopping Points

**I WILL:**
- Modify only `context/Create Full HD Prototype/src/app/App.tsx`
- Replace mock data arrays with `fetch()` calls for the 11 screens listed in 22.4
- Add loading and error states for each wired screen
- Test by running `npm run dev` in the prototype folder and confirming real data appears
- Commit the modified `App.tsx` to the repo

**I WILL NOT:**
- Modify any file outside `context/Create Full HD Prototype/src/app/App.tsx`
- Add new React components, pages, or routes
- Modify the FastAPI backend (it's already complete)
- Add POST/PUT/DELETE endpoints
- Add auth, JWT, or user tables
- Add Redux, Context API, or state management libraries
- Modify `package.json` or add npm dependencies
- Wire screens that are supposed to stay mock (login, workspaces, alerts, AI chat, admin)
- Deploy to production or set up Cloud Run for the frontend
- Add tests

**Phase 3 is complete when:**
1. All 11 screens in 22.4 display real data from the API
2. All mock-only screens still navigate correctly (no broken routes)
3. Loading states appear during data fetches
4. Error states show gracefully when API is unreachable
5. The app is runnable with `npm run dev` and `uvicorn app.main:app --reload` running simultaneously
6. Code is committed and pushed

**After Phase 3, we stop.** We do not proceed to auth, workspaces, LLM, or any other feature until you explicitly direct otherwise.



---

## 24. Step-by-Step Frontend Wiring: Step 1 Detailed Plan — SearchPage

### 24.1 What I Discovered From the Prototype Code

After thoroughly reading `App.tsx` (2745 lines), I found that the Figma prototype's data screens use mock arrays with **richer data than our PostgreSQL schema contains**:

| Screen | Mock Data Fields | Our API Returns | Match? |
|---|---|---|---|
| **SearchPage** (line 1052) | `symbol`, `name`, `sector`, `hype`, `evidence`, `price`, `change` | `search_tickers()` → `ticker`, `cik` only | **MISMATCH** |
| **Dashboard** (line 896) | `symbol`, `name`, `sector`, `hype`, `evidence`, `price`, `change` | Same as above | **MISMATCH** |
| **TickerDashboard header** (line 1163) | `symbol`, `name`, `price`, `change`, `hype`, `evidence` | `get_ticker_prices()` → `date`, `current`, `change`, etc. | **PARTIAL** |
| **TickerDashboard news** (line 1165) | `headline`, `source`, `time`, `summary`, `claims`, `evidenceLinks`, `hype`, `evidence` | `get_ticker_news()` → `target_ticker`, `date`, `ingest_date`, `content_body` | **MISMATCH** |
| **TickerDashboard overview** | AI summary text, key claims with evidence labels, financial metrics (revenue, EPS) | No LLM, no scoring engine | **MISMATCH** |
| **FilingsPage** (line 1566) | `type`, `date`, `period`, `size`, `sections`, `key` | `get_ticker_filings()` → `form_type`, `filing_date`, `element_count` | **PARTIAL** |
| **FilingsPage detail** | Section summaries with evidence scores, XBRL extraction status | `get_filing_elements()` → raw element text | **MISMATCH** |
| **TimelinePage** (line 1457) | `date`, `type`, `title`, `description`, `score_delta` | `get_ticker_timeline()` → `date`, `source`, `element_type`, `content_body` | **MISMATCH** |
| **CommunityPage** (line 1650) | Reddit posts with `score`, `comments`, `hype`, `evidence`, `flair` | No Reddit data | **NO MATCH** |
| **ChatPage** (line 1997) | AI-generated multi-hop RAG responses | No LLM | **NO MATCH** |
| **Workspaces** | Workspace CRUD, ticker tracking | No workspace tables | **NO MATCH** |

### 24.2 The Core Problem

The Figma prototype was designed for the **final product** — a full app with:
- Hype/Evidence scoring engine (`ticker_scores` table)
- LLM-generated summaries and claims extraction
- Company metadata (sector, name, financial metrics)
- Reddit/community data
- Vector search and RAG

**Our current PostgreSQL schema only has raw data:**
- Price quotes (Finnhub)
- News article text (GNews)
- SEC filing elements (SEC shredder)
- Fiscal year-end dates

**The prototype's mock data represents a future state.** We cannot faithfully reproduce it without building the missing infrastructure first.

### 24.3 Step 1 Strategy: SearchPage with Data Shape Adaptation

**What I'm actually wiring for Step 1:**

Instead of trying to force the prototype's rich mock data into our simpler API, I will:

1. **Call `GET /tickers/search?q={query}`** when the user types in the search input
2. **Adapt the UI to display what our API returns:** ticker symbol + CIK only
3. **Simplify the result cards** — remove hype/evidence bars, price, change, sector (our API doesn't return these)
4. **Keep the navigation flow intact** — clicking a result still navigates to the ticker dashboard

**This means the SearchPage will look different from the Figma mockup after wiring.** It will show simpler, factual results (just ticker + CIK) rather than the rich mock cards with scores. This is honest to what our data actually provides.

**What stays the same:**
- Search input field
- Filter chips (UI only — they won't filter results since our API doesn't support sector filtering)
- Sort dropdown (UI only — our API doesn't support sorting)
- Navigation to ticker dashboard on click
- Page layout, spacing, styling, Tailwind classes

**What changes:**
- Result cards show only: ticker symbol, CIK
- Removes: hype/evidence bars, price, change, sector, divergence scores
- Loading state while fetching
- Error state if API fails

**Why this approach:** It's honest to the data we have. We don't fake Hype/Evidence scores or invent company names. The user sees real data from PostgreSQL, just in a simpler format than the mockup.

### 24.4 Step 1 Implementation Details

**File modified:** `context/Create Full HD Prototype/src/app/App.tsx` only

**Exact changes in SearchPage component (lines 1052-1158):**

1. Add `useState` imports (already imported at top)
2. Add state variables inside `SearchPage`:
   - `const [results, setResults] = useState([])`
   - `const [loading, setLoading] = useState(false)`
   - `const [error, setError] = useState(false)`

3. Add `useEffect` to fetch from API:
   ```typescript
   useEffect(() => {
     if (!query.trim()) return;
     setLoading(true);
     setError(false);
     fetch(\`http://localhost:8000/tickers/search?q=${encodeURIComponent(query)}&limit=20\`)
       .then(res => {
         if (!res.ok) throw new Error(\`HTTP \${res.status}\`);
         return res.json();
       })
       .then(data => setResults(Array.isArray(data) ? data : []))
       .catch(() => setError(true))
       .finally(() => setLoading(false));
   }, [query]);
   ```

4. Replace `const results = TICKERS.filter(...)` with the state variable
5. Update result card JSX to use `results` state instead of `TICKERS.filter(...)`
6. Simplify card content: show ticker symbol and CIK only, remove hype/evidence/price/change
7. Add loading spinner when `loading === true`
8. Add error message when `error === true`

**What the SearchPage will look like after wiring:**
- Search input at top (same as before)
- "X results for 'query'" text
- Simplified result cards: ticker symbol in mono font, CIK below it, clickable to navigate to ticker dashboard
- No sector badges, no hype/evidence bars, no price displays
- Loading spinner during fetch
- "No results found" or "Error loading results" states

### 24.5 Why Not Wire the Richer Screens First?

The Dashboard, Ticker Dashboard, Filings, and Timeline pages all depend on having a **selected ticker** context. The SearchPage is the natural entry point — it finds tickers, then the user clicks into the ticker dashboard.

If I wired the Dashboard first, I'd need to hardcode or mock the ticker selection anyway. The SearchPage is the authentic entry point.

### 24.6 What I'm Explicitly NOT Doing in Step 1

- NOT modifying any other page components
- NOT adding new files
- NOT modifying the API
- NOT adding auth
- NOT changing the styling or Tailwind classes (keeping layout identical)
- NOT trying to fabricate hype/evidence scores or other non-existent data
- NOT wiring Dashboard, TickerDashboard, Filings, Timeline, Community, Chat, Workspaces, Alerts, Admin
- NOT adding POST/PUT/DELETE endpoints
- NOT modifying `package.json` or adding dependencies

### 24.7 Verification for Step 1

**How to verify Step 1 is complete:**
1. Start React dev server: `cd context/Create\ Full\ HD\ Prototype && npm run dev`
2. Start FastAPI server: running on `data-ingest-vm` port 8000
3. Open `localhost:5173`
4. Navigate to Search page (click "Research" in sidebar, or from landing page go through mock auth to dashboard → click search)
5. Type "AAPL" in search input
6. Confirm: results appear showing "AAPL" with CIK
7. Confirm: loading spinner appears briefly
8. Confirm: clicking result navigates to ticker dashboard
9. Confirm: no console errors
10. Confirm: all other pages still work (navigation intact)

**Hard stopping point:** SearchPage loads real ticker data from the API and handles loading/error states. Nothing else is touched.

### 24.8 Dependencies for Step 1

- FastAPI server must be running on `localhost:8000` (or accessible via the same network)
- React dev server on `localhost:5173`
- No additional npm packages needed
- No backend changes needed

If the FastAPI server is not reachable, the SearchPage will show the error state. The code changes can still be committed; they just need the backend running to display data.

## 23. Pipeline Architecture Clarification

Our data pipeline uses **three sources**, not the five originally planned:

| Original Plan | Actual Implementation | Reason |
|---|---|---|
| Alpha Vantage News | GNews | GNews provides cleaner article text, better API |
| Alpha Vantage Prices | Finnhub | Finnhub provides real-time quotes with richer fields |
| Reddit Community Posts | None | Not implemented — social sentiment not in scope for MVP |
| SEC EDGAR Filings | Custom SEC shredder | Provides shredded HTML elements, not just raw filings |

**What this means for the schema:**
- `staging_finnhub`: 4,473 rows of price data (Fortune 500 tickers)
- `staging_gnews`: 73,980 rows of news article text
- `staging_sec`: 758,054 rows of SEC filing elements (8-K and 10-K, shredded into narrative/quantitative sections)
- `fiscal_parameters`: 477 rows of fiscal year-end dates extracted from 10-K cover pages
- `unified_staging`: 836,507 rows combining all three sources into one searchable relation

**The UC table references Alpha Vantage and Reddit** — those UCs (UC-Ingest-01, UC-Ingest-03, UC-Pipe-03, UC-Pipe-04) describe pipelines we deliberately did not build. They are not "missing" — they are intentionally out of scope. Our GNews and Finnhub pipelines serve the same app purposes with different data sources.

**The UC table also references capabilities we don't have yet** (embeddings, LLM, vector search, scoring engine, user auth). These are deferred to later phases per mentor guidance and the mentorship learning plan.

**Bottom line:** The use cases that are implementable are the ones that match our actual three sources and read-only data retrieval. Everything else is either already done by the pipeline, describes different data sources we didn't choose, or requires infrastructure we haven't built yet.

---

## 25. Authentication & Authorization System — Implementation Plan

### 25.1 Phase 1: Database Schema & Migrations (Completed 2026-07-26)

**Purpose:** Create the four authentication tables in PostgreSQL so that the auth subsystem has a persistent storage layer.

**Migration files (already existed at correct paths):**
- `app/auth/migrations/001_create_auth_tables.sql` — Creates `users`, `permissions`, `user_permissions`, `user_permissions_index` tables with `CREATE TABLE IF NOT EXISTS` (idempotent)
- `app/auth/migrations/002_create_indexes.sql` — Creates indexes on `user_permissions_index(user_id)` and `user_permissions_index(permission_name)` with `CREATE INDEX IF NOT EXISTS` (idempotent)

**Tables created (verified via `\dt` and `\d` in psql):**

| Table | Columns | Key Constraints |
|---|---|---|
| `users` | `id` SERIAL PK, `email` TEXT UNIQUE NOT NULL, `password_hash` TEXT NOT NULL, `created_at` TIMESTAMP DEFAULT NOW(), `is_active` BOOLEAN DEFAULT TRUE | PK on `id`, UNIQUE on `email`, FK from `user_permissions.user_id` CASCADE |
| `permissions` | `id` SERIAL PK, `name` TEXT UNIQUE NOT NULL, `description` TEXT | PK on `id`, UNIQUE on `name`, FK from `user_permissions.permission_id` CASCADE |
| `user_permissions` | `user_id` INTEGER NOT NULL FK, `permission_id` INTEGER NOT NULL FK | Composite PK `(user_id, permission_id)`, both FKs CASCADE |
| `user_permissions_index` | `user_id` INTEGER NOT NULL, `permission_name` TEXT NOT NULL | Index on `user_id`, Index on `permission_name` |

**Validation evidence:**
- `\dt` confirmed 9 tables (5 existing + 4 new): `fiscal_parameters`, `permissions`, `staging_finnhub`, `staging_gnews`, `staging_sec`, `unified_staging`, `user_permissions`, `user_permissions_index`, `users`
- No existing tables or data modified or deleted
- Migration is idempotent (uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`)

**Execution method:** SSH tunnel through `ftd-postgres-vm` (see Section 26 below).

### 25.2 Implementation Plan Reference

The full implementation plan spans 7 phases covering the authentication & authorization backend:
1. **Phase 1** — Database schema & migrations (this section)
2. **Phase 2** — Core auth infrastructure (config, models, hasher, token)
3. **Phase 3** — `/auth/login` endpoint
4. **Phase 4** — Auth middleware & dependencies
5. **Phase 5** — Permission seeding & index maintenance
6. **Phase 6** — Protecting existing endpoints
7. **Phase 7** — Integration testing & validation

The plan is documented in the full implementation plan and follows strict additive-only, no-destructive-commands safety guardrails.

---

## 26. SSH Workaround: Accessing ftd-postgres-vm PostgreSQL

**Problem:** The `ftd-postgres-vm` VM (e2-micro, `us-west2-a`, external IP `35.236.126.62`) does not allow anonymous/public access to PostgreSQL port 5432 or SSH port 22 from arbitrary IPs. Direct `psql` connections to `34.94.89.135` or the VM's external IP `35.236.126.62` time out. The `gcloud compute ssh` command also times out because it requires an interactive IAP tunnel setup that doesn't work in non-interactive shell contexts.

**Workaround:** Use `gcloud compute start-iap-tunnel` to create a local port-forward隧道 through GCP's Identity-Aware Proxy (IAP), then connect `psql` to the local forwarded port.

### 26.1 Steps

```bash
# 1. Start IAP tunnel (runs in background)
gcloud compute start-iap-tunnel ftd-postgres-vm 5432 \
  --zone=us-west2-a --project=ftd2026 \
  --local-host-port=127.0.0.1:5433 &

# 2. Wait for tunnel to establish
sleep 3

# 3. Connect psql through the tunnel
PGHOST=127.0.0.1 PGPORT=5433 PGDATABASE=ftd_lakehouse \
  PGUSER=ftd_app PGPASSWORD='5Ou+BkyuQT3izP72219jMLy2AobRdI3f' \
  psql -c "\dt"

# 4. Close tunnel when done
kill <tunnel_pid>
```

### 26.2 Alternative: SSH Config + gcloud compute ssh

The `gcloud compute config-ssh` command sets up SSH config entries:
```
Host ftd-postgres-vm.us-west2-a.ftd2026
    HostName 35.236.126.62
    IdentityFile /Users/isabellabutera/.ssh/google_compute_engine
    UserKnownHostsFile=/Users/isabellabutera/.ssh/google_compute_known_hosts
    HostKeyAlias=compute.4333432600937155991
    IdentitiesOnly=yes
```

Then use: `ssh ftd-postgres-vm.us-west2-a.ftd2026` — this uses GCP's IAP tunneling under the hood and requires browser-based authentication on first use.

### 26.3 Notes

- GCP firewall rules allow TCP 5432 from external IPs (`allow-postgres-from-user-ipv4` rule exists) but the VM's PostgreSQL may only listen on internal interfaces
- The `gcloud compute ssh` IAP tunnel approach is the most reliable method for non-interactive scripts
- Credentials are stored in `run_pg.sh` and `app/db.py` with `PGPASSWORD` environment variable
- Do NOT commit credentials to version control; use environment variables or secret management

---

## 27. Authentication & Authorization System — Phase 2 (Completed 2026-07-26)

### 27.1 What Was Done

Installed `bcrypt` and `PyJWT` dependencies and created all foundational auth modules under `app/auth/`. No existing files were modified.

### 27.2 New Files Created

| File | Purpose |
|---|---|
| `app/auth/__init__.py` | Package init (empty) |
| `app/auth/config.py` | JWT config from env vars with defaults (`JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`, `JWT_EXPIRATION_MINUTES=60`, `JWT_ISSUER=ftd-auth`, `JWT_AUDIENCE=ftd-api`, `JWT_TOKEN_VERSION=1`, `BCRYPT_ROUNDS=12`) |
| `app/auth/models.py` | Pydantic models: `LoginRequest` (email, password), `LoginResponse` (access_token, token_type), `TokenData` (user_id, email, permissions); also `normalize_email()` utility |
| `app/auth/hasher.py` | `hash_password(password) -> str` (bcrypt, `$2b$` prefix) and `verify_password(password, hash) -> bool` |
| `app/auth/token.py` | `create_access_token(data, expires_delta) -> str` (JWT with `iss`, `aud`, `exp`, `iat`, `sub`, `email`, `tv` claims) and `verify_token(token) -> dict \| None` |
| `requirements.txt` | Root-level deps file with `bcrypt>=4.1.0` and `PyJWT>=2.8.0` |

### 27.3 Dependencies Installed

- `bcrypt` 5.0.0 — password hashing/verification
- `PyJWT` 2.13.0 — JWT creation, signing, verification

### 27.4 Unit Tests Created

| File | Tests |
|---|---|
| `tests/test_hasher.py` | 5 tests: hash produces `$2b$` prefix, verify correct/incorrect passwords, unique salt per hash, invalid hash returns False |
| `tests/test_token.py` | 8 tests: token creation returns string, contains all required claims, valid token verifies, expired token returns None, malformed token returns None, wrong secret returns None, wrong token version returns None, `sub` claim is string in payload |

All 13 unit tests pass.

### 27.5 Key Design Decisions

1. **`sub` claim stored as string** — PyJWT 2.x requires `sub` to be a string, so `create_access_token` converts integer user IDs to strings. Consumers must convert back to int when needed.
2. **`verify_token` catches `jwt.InvalidTokenError`** — this is the base exception class for all PyJWT validation failures (expired, invalid signature, wrong issuer/audience).
3. **`verify_password` catches `ValueError`** — `bcrypt.checkpw` raises `ValueError` on an invalid hash format rather than returning `False`. The function safely returns `False` in this case.
4. **`normalize_email()` in `models.py`** — strips whitespace and lowercases email before any database interaction, as required by the plan.
5. **No `email-validator` dependency** — email normalization uses stdlib (strip + lower), which is sufficient for the lookup pattern. The plan noted this as optional.

### 27.6 Files NOT Modified

- No existing application files were modified in Phase 2. The implementation is strictly additive.

---

## 28. Authentication & Authorization System — Phase 3 (Completed 2026-07-26)

### 28.1 What Was Done

Created the `/auth/login` endpoint, the repository for user lookup, and wired the auth router into `app/main.py`.

### 28.2 New Files Created

| File | Purpose |
|---|---|
| `app/auth/repository.py` | `get_user_by_email(email)` — normalizes email before querying `users` table with parameterized SQL |
| `app/auth/router.py` | `POST /auth/login` endpoint: validates `LoginRequest`, normalizes email, looks up user, checks `is_active`, verifies password with `bcrypt`, creates JWT with `sub` (user id) and `email` claims, returns `LoginResponse` |
| `app/auth/__init__.py` | Previously missing; created as empty package init |

### 28.3 Files Modified

| File | Change |
|---|---|
| `app/main.py` | Added `from app.auth.router import router as auth_router` and `app.include_router(auth_router)` before existing route includes |

### 28.4 Test Results (validated via local server + IAP tunnel)

| Test Case | Expected | Actual |
|---|---|---|
| Valid login (`testuser@example.com` / `testpass123`) | 200 + JWT | ✅ 200 with access_token |
| Invalid password | 401 | ✅ 401 |
| Non-existent email | 401 | ✅ 401 |
| Inactive user | 401 | ✅ 401 |
| Malformed body (missing password) | 422 | ✅ 422 |
| Email normalization (`TestUser@Example.com`) | 200 + JWT | ✅ 200 with access_token |

### 28.5 Key Design Decisions

1. **Generic 401 error message** — Both "user not found" and "wrong password" return the same `{"detail":"Invalid credentials"}` message to prevent email enumeration attacks.
2. **Password verification happens after user lookup** — Both missing user and wrong password return the same response.
3. **Inactive users treated as invalid credentials** — Consistent security posture.
4. **Sub stored as string** — `sub` is stored as a string `"1"` (not integer 1) in the JWT, matching PyJWT 2.x requirements.
5. **No permissions in JWT** — Permissions are resolved from PostgreSQL on each request (Phase 4), not embedded in the token.

### 28.6 Files NOT Modified (existing preserved)

- `app/routes/tickers.py`, `app/routes/filings.py`, `app/routes/search.py`, `app/routes/news.py` — not touched yet (Phase 6)
- `app/auth/migrations/001_create_auth_tables.sql`, `app/auth/migrations/002_create_indexes.sql` — not modified
- `app/auth/config.py`, `app/auth/models.py`, `app/auth/hasher.py`, `app/auth/token.py` — created in Phase 2; not modified

---

## 29. Authentication & Authorization System — Phase 4 (Completed 2026-07-26)

### 29.1 What Was Done

Created the authorization middleware (intercepts every request, validates JWT, attaches user identity), dependency injection functions (`get_current_user`, `get_current_permissions`, `require_permission`), and permission constants. Modified `app/main.py` to register the middleware.

### 29.2 New Files Created

| File | Purpose |
|---|---|
| `app/auth/permissions.py` | 8 permission constants (`PERMISSION_TICKERS_SEARCH`, etc.) and `ALL_PERMISSIONS` frozenset |
| `app/auth/middleware.py` | `AuthMiddleware` class (subclasses `BaseHTTPMiddleware`): extracts Bearer token, validates JWT via `verify_token()`, attaches `request.state.user_id` and `request.state.email`, skips public paths (`/health`, `/auth/login`, `/docs*`, `/openapi.json`, `/redoc`), returns 401 for missing/invalid/expired/malformed tokens |
| `app/auth/dependencies.py` | FastAPI dependencies: `get_current_user` (validates JWT, returns `{user_id, email}`), `get_current_permissions` (queries `user_permissions_index` for user's permission set), `require_permission(permission)` (raises HTTP 403 if permission absent) |

### 29.3 Files Modified

| File | Change |
|---|---|
| `app/main.py` | Added `from app.auth.middleware import AuthMiddleware` and `app.add_middleware(AuthMiddleware)` after CORS middleware |

### 29.4 Validation Results

| Check | Result |
|---|---|
| All modules import successfully | ✅ |
| AuthMiddleware is in middleware stack before CORS | ✅ |
| All 10 routes registered correctly | ✅ |
| All 8 permission constants defined correctly | ✅ |
| `PUBLIC_PATHS` includes `/health` and `/auth/login` | ✅ |
| `get_current_user` raises HTTP 401 when token missing | ✅ |
| `get_current_permissions` queries PostgreSQL (not JWT) | ✅ |
| `require_permission` raises HTTP 403 when permission absent | ✅ |
| `require_permission` allows request through when permission present | ✅ |

### 29.5 Key Design Decisions

1. **`AuthMiddleware` as `BaseHTTPMiddleware` subclass** — Required by Starlette's `app.add_middleware()` API; plain async functions are not supported as middleware classes.
2. **`public_paths` excludes `/auth/login`** — The login endpoint must work without authentication so users can obtain tokens.
3. **Permission resolution queried from PostgreSQL on every request** — Per the plan's requirement that permission changes become effective immediately (stateless JWTs don't carry permissions).
4. **`oauth2_scheme` uses `auto_error=False`** — So `get_current_user` can raise its own 401 with a custom message instead of FastAPI's default 401.
5. **`request.state.user_id` and `request.state.email`** — Auth middleware attaches user identity to request state for downstream middleware/dependencies to access.
6. **Middleware runs before route handlers** — Auth interception happens before any route logic executes.

### 29.6 Files NOT Modified (existing preserved)

- All existing route handlers — dependencies added in Phase 6

---

## 30. SSH/VPN Access — Persistent Issues and Workaround

### 30.1 SSH Tunnel Failure Pattern

The `ftd-postgres-vm` SSH daemon (`sshd`) fails to respond to SSH banner exchanges after a VM stop/start cycle. The VM boots fully (reaches `multi-user.target` in ~25s), TCP ports 22 and 5432 accept connections at the GCP network layer (`nc -zv` succeeds), but `sshd` does not send its banner or respond to any SSH handshake. `gcloud compute ssh`, direct `ssh` to the external IP, and `gcloud compute start-iap-tunnel` all hang at "banner exchange" or "failed to connect to backend."

The direct `nc | nc` test to port 22 confirms zero response from sshd. PostgreSQL on port 5432 similarly accepts TCP but does not complete authentication handshakes from external sources (only responds to connections originating from within the GCP VPC network or via `gcloud compute ssh --command`).

### 30.2 Working Approaches

| Method | Status | Notes |
|---|---|---|
| `gcloud compute ssh --command="..."` | **Unreliable after VM restart** — hangs at banner exchange | Worked reliably before the VM was stopped |
| `gcloud compute start-iap-tunnel` | **Fails** — "failed to connect to backend" | Persistent IAP TCP forwarding issue |
| `ssh` via external IP | **Fails** — connection established, no banner | TCP works, sshd not responding |
| `ssh ftd-postgres-vm.us-west2-a.ftd2026` | **Fails** — same as above | Uses GCP SSH config, same issue |
| `nc -zv IP PORT` | **Succeeds** at TCP level only | Confirms firewall allows traffic, not service health |

### 30.3 Workaround for Database Operations

Use `gcloud compute ssh --command=` for one-off database commands (this uses GCP's internal IAP channel which works for command execution even when the persistent SSH tunnel doesn't):

```bash
gcloud compute ssh ftd-postgres-vm --zone=us-west2-a --project=ftd2026 \
  --command="PGPASSWORD='5Ou+BkyuQT3izP72219jMLy2AobRdI3f' psql -h 127.0.0.1 -U ftd_app -d ftd_lakehouse -c \"YOUR_SQL_HERE\""
```

### 30.4 VM Restart Procedure

If the VM is terminated, restart it and wait 60+ seconds before attempting SSH:

```bash
gcloud compute instances start ftd-postgres-vm --zone=us-west2-a --project=ftd2026
# Wait 60+ seconds for sshd to initialize after OS Login cache refresh
gcloud compute ssh ftd-postgres-vm --zone=us-west2-a --project=ftd2026 --command="echo READY"
```

### 30.5 Known VM State

- `ftd-postgres-vm`: e2-micro, `us-west2-a`, external IP currently `34.94.216.101` (changed from `35.236.126.62` after stop/start; GCP ephemeral IPs change on each start-stop cycle)
- SSH daemon requires reinitialization after VM stop/start cycles
- PostgreSQL (`ftd_lakehouse`) is operational — accessible via `gcloud compute ssh --command=` inline commands
- `data-ingest-vm`: RUNNING at `34.20.146.65` (external IP), operational for its pipeline purpose only

---

## 31. Authentication & Authorization System — Phase 5 (Completed 2026-07-31)

### 31.1 What Was Done

Populated the `permissions` table, created index maintenance scripts, and added the composite index on `user_permissions_index(user_id, permission_name)`.

### 31.2 New Files Created

| File | Purpose |
|---|---|
| `app/auth/seed_data.py` | Idempotent script to seed `permissions` table with all 8 constants from `permissions.py`. Uses `INSERT ... ON CONFLICT DO NOTHING`. Prints summary of inserts vs. existing. |
| `app/auth/index_maintainer.py` | Two functions: `rebuild_user_permissions_index()` (TRUNCATE + INSERT from joined `user_permissions` + `permissions`) and `sync_user_permissions_index(user_id)` (DELETE + INSERT for single user). |
| `app/auth/migrations/003_create_composite_index.sql` | Creates composite index `idx_user_permissions_index_composite` on `user_permissions_index(user_id, permission_name)`. Uses `CREATE INDEX IF NOT EXISTS`. |

### 31.3 Database Changes Executed

1. **Permissions table**: Already seeded with all 8 permission constants during Phase 3 (manually via `gcloud compute ssh`). `seed_data.py` is idempotent and confirms no duplicates.
2. **Composite index**: Created `idx_user_permissions_index_composite ON user_permissions_index(user_id, permission_name)`. Verified via `\d user_permissions_index`.
3. **Index state**: All three indexes now exist on `user_permissions_index`:
   - `idx_user_permissions_index_composite` (user_id, permission_name) — new in Phase 5
   - `idx_user_permissions_index_user_id` (user_id)
   - `idx_user_permissions_index_permission_name` (permission_name)

### 31.4 Validation

| Check | Result |
|---|---|
| `permissions` table has all 8 rows | ✅ (8 rows confirmed) |
| `user_permissions_index` composite index exists | ✅ (verified via `\d user_permissions_index`) |
| Single-column indexes still present | ✅ |
| `seed_data.py` is idempotent (`ON CONFLICT DO NOTHING`) | ✅ |
| `rebuild_user_permissions_index()` and `sync_user_permissions_index()` implemented | ✅ |
| No existing tables modified | ✅ |

### 31.5 Files NOT Modified

- All existing application files preserved
- Only additive changes: new files + new migration

---

## 32. Authentication & Authorization System — Phase 6 (Completed 2026-07-31)

### 32.1 What Was Done

Applied the `require_permission(...)` dependency to all 9 existing GET endpoints so that every route is now protected by authentication and authorization. The `/health` endpoint remains publicly accessible; `/auth/login` is excluded from the auth middleware.

### 32.2 Files Modified

| File | Change |
|---|---|
| `app/routes/tickers.py` | Added `from app.auth.dependencies import require_permission` and `permission: str = require_permission("...")` to all 6 endpoints |
| `app/routes/filings.py` | Added `from app.auth.dependencies import require_permission` and `from fastapi import Depends` + permission dependency to 1 endpoint |
| `app/routes/search.py` | Added `from app.auth.dependencies import require_permission` and `from fastapi import Depends` + permission dependency to 1 endpoint |
| `app/routes/news.py` | Added `from app.auth.dependencies import require_permission` and `from fastapi import Depends` + permission dependency to 1 endpoint |

### 32.3 Permission Mapping

| Endpoint | Permission |
|---|---|
| `GET /tickers/search` | `tickers.search` |
| `GET /tickers/{ticker}/prices` | `tickers.prices` |
| `GET /tickers/{ticker}/news` | `tickers.news` |
| `GET /tickers/{ticker}/filings` | `tickers.filings` |
| `GET /tickers/{ticker}/timeline` | `tickers.timeline` |
| `GET /tickers/{ticker}/fiscal-year-end` | `tickers.fiscal_year_end` |
| `GET /filings/{accession_number}/elements` | `filings.read` |
| `GET /search` | `search.read` |
| `POST /auth/login` | **none** (public) |
| `GET /health` | **none** (public) |

### 32.4 Key Design Decision

`require_permission()` already returns a `Depends(...)` object (not a raw dependency function), so route handlers use it directly as `permission: str = require_permission("...")` — NOT wrapped in `Depends(...)` again — because FastAPI dependency injection auto-unwraps `Depends` objects when used as parameter defaults.

### 32.5 Files NOT Modified

- All existing route handler business logic — only a dependency parameter was added
