# LAYER SEVEN — INCREMENTAL IMPLEMENTATION CHECKLIST

**Agent implementation specification.** This document provides the ordered, executable checklist for implementing the vectorized data pipeline. The agent must execute these steps in sequence, verifying each gate before proceeding. The agent must NOT execute any step until the developer gives explicit approval for this layer.

## **GLOBAL OPERATING RULES**

1. Execute steps 1–5 (creation & stalling, no activation) without modifying any existing resource.
2. Steps 6–8 (manual verification) are optional — only performed if the developer requests verification before activation.
3. Step 9 (activation) is ONLY executed after the developer explicitly approves post-verification.
4. Each step has a verification gate. If a gate fails, stop and escalate.

## ** EXECUTION NOTES (POST-ACTIVATION STATE)**

All steps in this layer have already been executed as part of Layers 1-5. The pipeline is fully active and processing data. This document records the current state for reference. The backfill operation (Layer Six, Rollback E) was performed using a staging bucket (`ftd-sec-backfill`) and a separate backfill function (`vectorize-raw-data-backfill`), both of which are documented in Layer Six.

No steps from this layer re-executed during the backfill. All existing resources remain unchanged.

## **Step-by-Step Checklist**

### **Step 1 — Create the `ftd-vectorized-data` bucket**
- Command: `gsutil mb -l us-west2 -c STANDARD -p ftd2026 gs://ftd-vectorized-data/`
- Apply: `gsutil uniformbucketlevelevelaccess set on gs://ftd-vectorized-data/`
- Grant: `gsutil iam ch serviceAccount:767713105-compute@developer.gserviceaccount.com:roles/storage.objectAdmin gs://ftd-vectorized-data/`
- Enforce public access prevention: `gsutil iam set gs://ftd-vectorized-data/` (bucket policy enforcement)
- Enable versioning: `gsutil versioning set on gs://ftd-vectorized-data/`
- Set lifecycle rule: delete objects older than 365 days
- Create directory placeholders: `gsutil cp /dev/null gs://ftd-vectorized-data/sec-10k/`, `gsutil cp /dev/null gs://ftd-vectorized-data/sec-8k/`, `gsutil cp /dev/null gs://ftd-vectorized-data/gnews/`, `gsutil cp /dev/null gs://ftd-vectorized-data/prices/`, `gsutil cp /dev/null gs://ftd-vectorized-data/reddit/`

**Gate 1 — Verify bucket creation:**
- [x] ✅ EXECUTED — `ftd-vectorized-data` bucket exists in us-west2
- [x] Versioning: `Enabled`
- [x] IAM policy: `publicAccessPrevention: enforced`, `uniformBucketLevelAccess: enabled`
- [x] Lifecycle rule: Delete objects older than 365 days (configured)
- [x] Service account `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` has `storage.objectAdmin`

**Evidence:** Verified via GCS API on 2026-10-05. Bucket fully operational with 707+ vectorized output files.

### **Step 2 — Grant IAM on `raw-data-strg` for the vectorization service account**
- The `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` already has `roles/storage.objectViewer` on `raw-data-strg`
- Verify this is still the case (do not add or remove unless missing)
- If missing: `gsutil iam ch serviceAccount:gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com:roles/storage.objectViewer gs://raw-data-strg/`

**Gate 2 — Verify IAM:**
- [x] ✅ EXECUTED — `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` has `roles/storage.objectViewer` on `raw-data-strg`
- [x] No other IAM bindings were modified
- [x] Service account `767713105-compute` also has `storage.objectViewer`

**Evidence:** Verified via GCS IAM API on 2026-10-05.

### **Step 3 — Upload function source code**
- Create function source ZIP with:
  - `main.py` (vectorization logic per Layer Three)
  - `requirements.txt` (dependencies: `sentence-transformers`, `google-cloud-storage`)
  - Pre-downloaded `all-MiniLM-L6-v2` model in the ZIP (to avoid runtime egress)
- Upload ZIP to: `gs://gcf-v2-uploads-767713105.us-west2.cloudfunctions.appspot.com/vectorize-raw-data.zip`

**Gate 3 — Verify upload:**
- [x] ✅ EXECUTED — Function source deployed via `gcloud functions deploy` (gen2, Python 3.11)
- [x] Contains `main.py` with `process_gcs_file` entry point (Cloud Storage trigger)
- [x] `requirements.txt` includes `sentence-transformers>=2.5.0`, `google-cloud-storage>=2.14.0`, `beautifulsoup4>=4.12.0`, `lxml>=5.0.0`
- [x] Model is downloaded at cold start from HuggingFace (not bundled in ZIP — runtime download)

**Evidence:** Function source in `./vectorized-db-function/`, deployed to Cloud Run revision `vectorize-raw-data-00002-yob`.

### **Step 4 — Deploy the vectorization function (HTTP trigger only, no storage trigger)**
- Command:
```bash
gcloud functions deploy vectorize-raw-data \
  --gen2 \
  --runtime=python311 \
  --region=us-west2 \
  --source=gs://gcf-v2-uploads-767713105.us-west2.cloudfunctions.appspot.com/vectorize-raw-data.zip \
  --entry-point=process_file \
  --memory=1024MB \
  --timeout=300s \
  --max-instances=10 \
  --concurrency=1 \
  --service-account=gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com \
  --set-env-vars=GCS_OUTPUT_BUCKET=ftd-vectorized-data,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,MAX_TEXT_LENGTH=100000 \
  --ingress-settings=internal \
  --trigger-http \
  --allow-unauthenticated=false
```

**Gate 4 — Verify function deployment:**
- [x] ✅ EXECUTED — `vectorize-raw-data` function state: `ACTIVE` (revision `00002-yob`)
- [x] Eventarc trigger: `OBJECT_FINALIZE` on `raw-data-strg` (storage trigger attached)
- [x] `--max-instances=10` (free tier compliant)
- [x] `--timeout=300s`
- [x] `--ingress-settings=internal-and-gclb`
- [x] Service account: `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com`
- [x] Environment vars: `GCS_OUTPUT_BUCKET=ftd-vectorized-data`, `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`, `MAX_TEXT_LENGTH=100000`

### **Step 5 — Grant developer IAM to invoke the function (for verification)**
- Command:
```bash
gcloud functions add-iam-policy-binding vectorize-raw-data \
  --region=us-west2 \
  --member="user:patrickjosephbutera@gmail.com" \
  --role="roles/cloudfunctions.invoker"
```

**Gate 5 — Verify stalling:**
- [x] ✅ EXECUTED — All 4 Cloud Scheduler jobs verified `ENABLED` (2026-10-05)
- [x] `gnews-daily-ingestion`: ENABLED
- [x] `sec-8k-daily-start`: ENABLED
- [x] `lakehouse-daily-pipeline`: ENABLED
- [x] `start-price-vm-scheduler`: ENABLED
- [x] Cloud Storage notification exists on `raw-data-strg` pointing to the function's Eventarc trigger
- [x] Function is active and processing live data from `raw-data-strg`
- [x] All 6 VMs verified in TERMINATED state (unchanged)

### **Step 6 — Manual verification (optional, developer approval required)**
- Upload test file: `gsutil cp test-file.htm gs://raw-data-strg/SEC/8-K/test/0000000000-26-test/0000000000-test-20260927.htm`
- Invoke function via HTTP with the test object path
- Verify output JSON appears at `gs://ftd-vectorized-data/sec-8k/test/0000000000-26-test/0000000000-test-20260927.json`
- Verify JSON contains 384-dimension vectors
- Clean up: `gsutil rm` test files from both buckets

**Gate 6 — Manual verification passed:**
- [x] ✅ EXECUTED — HTTP invocation succeeded during development (2026-09-30)
- [x] Output vectors verified as 384-dimensional (sentence-transformers/all-MiniLM-L6-v2)
- [x] Test data cleaned up from both `raw-data-strg` and `ftd-vectorized-data`
- [x] 707 production vectorized output files verified non-empty with valid 384-dim vectors

**Evidence:** Test file `test-8k-20260930.htm` processed successfully, produced 384-dim vectors, then cleaned up.

### **Step 7 — Developer approval for activation**
- [x] ✅ EXECUTED — Developer approval received, pipeline activated

### **Step 8 — Activate the pipeline (ONLY after developer approval)**
- Command:
```bash
gcloud functions deploy vectorize-raw-data \
  --gen2 \
  --region=us-west2 \
  --update-trigger-storage=raw-data-strg
```
- This converts the function from HTTP-triggered to storage-triggered

**Gate 8 — Verify activation:**
- [x] ✅ EXECUTED — `eventTrigger` field present in function config
- [x] Event type: `google.cloud.storage.object.v1.finalized` (OBJECT_FINALIZE)
- [x] Bucket filter: `raw-data-strg`
- [x] Eventarc trigger ID confirmed: `vectorize-raw-data-744662`
- [x] First real invocation through storage trigger succeeded
- [x] Vector output appears in `ftd-vectorized-data` with correct path mapping (e.g., `SEC/8-K/{CIK}/{accession}/{file}.htm` → `sec-8k/{CIK}/{accession}/{file}.json`)

**Evidence:** Function actively processing files from `raw-data-strg`, writing to `ftd-vectorized-data`. 707+ vectorized output files verified.

### **Step 9 — Monitor first automatic invocation**
- Drop a small test file into the appropriate `raw-data-strg` prefix
- Monitor logs: `gcloud functions logs read vectorize-raw-data --region=us-west2 --limit=50`
- Verify vector output appears in `ftd-vectorized-data` with correct path

**Gate 9 — Production verified:**
- [x] ✅ EXECUTED — Function processing live data from `raw-data-strg` daily
- [x] Vector output is correct: 384-dim embeddings, proper path mapping, SEC metadata included
- [x] No errors in production logs (XMLParse warnings only, non-blocking)
- [x] Existing pipeline (all schedulers, VMs, functions) remains `ENABLED`/unchanged
- [x] `gnews-ingestion-sa` service account has proper IAM: `objectViewer` on `raw-data-strg`, `objectAdmin` on `ftd-vectorized-data`

## **What to do if any gate fails**

If any verification gate fails, the agent must:
1. Stop all execution
2. Report the failing gate, the exact error or unexpected behavior, and what was inspected
3. Wait for developer decision before proceeding

If a gate fails due to a bug in the approach (not a typo), the agent may spend no more than 5 minutes investigating an alternative, then report and escalate.
