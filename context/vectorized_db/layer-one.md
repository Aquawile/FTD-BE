# LAYER ONE — RAW DATA SOURCE ANALYSIS & PRESERVATION

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer One of the vectorized data pipeline. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

The existing data pipeline in `ftd2026` is fully operational. The raw data bucket `raw-data-strg` receives data from three active ingestion sources: SEC filings, GNews articles, and price data (Finnhub). SEC 8-K ingestion runs on the data-ingest VM triggered by a Cloud Scheduler job. The purpose of this layer is to fully document every data source, ingestion schedule, and file format so that the new vectorized pipeline can be designed to process **future** arrivals only, without disrupting any existing flow.

The agent must not modify any existing bucket, function, VM, cron job, or service account during this phase. This layer is read-only analysis and documentation only.

The agent must not invent missing architecture. All findings are based on the inspected GCP infrastructure (buckets, Cloud Functions, Scheduler jobs, VM metadata). If a behavior cannot be determined from the infrastructure, the agent must report it and stop rather than guessing.

The agent must use the repository's existing GCP tooling (`gcloud`, `gsutil` CLI, GCS JSON API) for all inspection. All inspection commands must be run with the `patrickjosephbutera@gmail.com` account, which has Owner permissions on `ftd2026`.

## **SUBLAYER 1.1 — DOCUMENT EXISTING BUCKETS, SCHEDULES, & DATA FORMATS**

### **Instruction**

The objective of Sublayer 1.1 is to produce a complete inventory of every data source, its destination bucket, the scheduled trigger that writes it, the service account used, the file format, and the directory structure. This inventory is the authoritative reference for the vectorized pipeline design in Layer Two and beyond.

The agent must inspect:
1. All GCS buckets in the project and their IAM policies
2. All Cloud Scheduler jobs and their schedules/URIs
3. All Cloud Functions and their environment variables
4. The data-ingest VM startup script and metadata
5. The lakehouse pipeline run script (`scripts/lakehouse-pipeline/run.sh`)
6. Sample file structures within each bucket prefix
7. All service accounts and their roles

### **Tools to use and why**

Use `gcloud` CLI to list buckets, scheduler jobs, functions, and service accounts. Use `gsutil`/GCS JSON API to list object prefixes and sample files. Use `gcloud compute instances describe` to read VM metadata. Read the repository file `scripts/lakehouse-pipeline/run.sh` for the pipeline script.

### **Implementation**

1. **Document all GCS buckets** (`gcloud storage buckets list`):
   - `raw-data-strg` — raw data landing zone, location `US-WEST2`, STANDARD storage class, publicAccessPrevention: `enforced`
   - `processed-layer-one` — parquet output from lakehouse pipeline, same config
   - `gcf-sources-767713105-us-west2` — Cloud Function source archive (Google-managed)
   - `gcf-v2-sources-767713105-us-west2` — Cloud Function v2 source archive (Google-managed, has lifecycle rule deleting old versions)
   - `gcf-v2-uploads-767713105.us-west2.cloudfunctions.appspot.com` — Function upload bucket (Google-managed, deletes after 1 day)

2. **Document all Cloud Scheduler jobs** (`gcloud scheduler jobs list`):
   - `gnews-daily-ingestion` — schedule `0 0 * * *` (daily midnight UTC), triggers `POST https://us-west2-ftd2026.cloudfunctions.net/gnews-ingest`, OIDC with `gnews-scheduler-sa@ftd2026.iam.gserviceaccount.com`
   - `sec-8k-daily-start` — schedule `30 3 * * *` (daily 03:30 UTC), directly starts `data-ingest-vm` via Compute API, OAuth with `sec-scheduler-sa@ftd2026.iam.gserviceaccount.com`
   - `lakehouse-daily-pipeline` — schedule `0 4 * * *` (daily 04:00 UTC), triggers `POST https://us-west2-ftd2026.cloudfunctions.net/start-lakehouse-vm`, OIDC with `gnews-scheduler-sa@ftd2026.iam.gserviceaccount.com`
   - `start-price-vm-scheduler` — schedule `55 21 * * *` (daily 21:55 UTC), triggers `GET https://us-west2-ftd2026.cloudfunctions.net/start-price-vm`

3. **Document all Cloud Functions** (`gcloud functions list`):
   - `gnews-ingest` — Python 3.11, env: `GCS_BUCKET=raw-data-strg`, `GCS_PREFIX=gnews`, `TICKERS_GCS_PATH=SEC/config/fortune500.json`, 512M memory, max 1 instance, service account `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com`
   - `reddit-ingest` — Python 3.11, **ARCHIVED / inactive** (was used for Reddit ingestion, no longer feeds data to `raw-data-strg`)
   - `start-lakehouse-vm` — Python 3.11, env: `GCE_ZONE=us-west2-a`, `GCP_PROJECT=ftd2026`, service account `github-actions-deploy@ftd2026.iam.gserviceaccount.com`
   - `start-price-vm` — Python 3.11, env: `GCE_ZONE=us-west2-a`, `GCP_PROJECT=ftd2026`, service account `github-actions-deploy@ftd2026.iam.gserviceaccount.com`

4. **Document the data-ingest VM** (`gcloud compute instances describe data-ingest-vm`):
   - Machine type: `e2-medium` (2 vCPU, 4GB RAM)
   - Status: TERMINATED (started daily at 03:30 UTC by scheduler, runs, then self-stops)
   - Boot disk: 30GB
   - Startup script at `/opt/sec-8k-ingestion/.env` reads environment variables, activates `.venv`, runs `python -m src.main` (SEC 8-K ingestion), then runs `/home/isabellabutera/scripts/lakehouse-pipeline/run.sh` (lakehouse + parquet generation to `processed-layer-one`, then PostgreSQL writes)
   - After completion, the startup script self-stops the VM via `gcloud compute instances stop`

5. **Document bucket directory structures**:
   - `raw-data-strg/SEC/` — SEC filings (10-K annual reports and 8-K current reports from EDGAR):
     - `SEC/10-K/{CIK}/{accession}/{filename}.htm` (HTML filing) + `metadata.txt`
     - `SEC/8-K/{CIK}/{accession}/{filename}.htm` (HTML filing) + `metadata.txt`
     - `SEC/10-K/{CIK}/{accession}/metadata.txt` — ~120 bytes (contains filing metadata as key=value pairs)
     - `SEC/config/fortune500.json` — 5652 bytes (ticker list for GNews ingestion)
   - `raw-data-strg/gnews/` — News articles from GNews API:
     - `gnews/{YYYY-MM-DD}/batch_NNN.json` — JSON array of news articles (~12KB each)
   - `raw-data-strg/prices/` — Price data from Finnhub:
     - `prices/{YYYY-MM-DD}/data.jsonl` — JSON Lines price data (~94KB)

6. **Document all service accounts** (`gcloud iam service-accounts list`):
   - `767713105-compute@developer.gserviceaccount.com` — compute default, has `objectAdmin` on both buckets
   - `ftd2026@appspot.gserviceaccount.com` — App Engine, has `objectCreator` on `raw-data-strg`
   - `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` — GNews ingestion, has `objectViewer` on `raw-data-strg`
   - `github-actions-deploy@ftd2026.iam.gserviceaccount.com` — used by Cloud Functions to start/stop VM
   - `sec-scheduler-sa@ftd2026.iam.gserviceaccount.com` — used by SEC scheduler to start VM

7. **Document secrets** (`gcloud secrets list`):
   - `ALPHA_VANTAGE_API_KEY` — **ARCHIVED / inactive** (not in use by any active function)
   - `databento-api-key` — **ARCHIVED / inactive**
   - `finnhub-api-key` — Active (used by price data ingestion)
   - `firebase-key`
   - `firebase-web-api`
   - `gnews-api-key` — Active (used by gnews-ingest function)

### **What "Vectorized" Means**

"Vectorized data" in this context means **numerical embedding vectors** generated from text data, NOT relational/parquet format. The pipeline converts raw text content (SEC filing HTML, GNews article JSON, price data JSONL) into **384-dimensional floating-point embedding vectors** using the `sentence-transformers/all-MiniLM-L6-v2` model.

This is fundamentally different from the existing `processed-layer-one` pipeline, which:
- Shreds HTML into structured element rows (tabular data)
- Writes Parquet files with schema-validated columns
- Loads into PostgreSQL tables (relational)

The vectorization pipeline:
- Extracts text from raw files (HTML → plain text, JSON → text fields)
- Splits text into ~2000-character chunks
- Encodes each chunk into a 384-dimension numerical vector via neural network
- Stores output as JSON: `{"text_preview": "...", "vector": [0.123, 0.456, ...]}`

The output is **not** relational data — it is numerical vectors suitable for semantic search and similarity comparison.

### **Verification**

The agent must verify that this sublayer is complete by confirming:
- Every Cloud Scheduler job's `lastAttemptTime` shows recent successful execution
- Every Cloud Function has at least one recent trigger
- The `raw-data-strg` bucket has objects in every prefix documented above
- The `processed-layer-one` bucket contains the expected `.parquet` files
- No IAM policy has been modified

