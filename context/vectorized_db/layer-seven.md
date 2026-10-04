# LAYER SEVEN — INCREMENTAL IMPLEMENTATION CHECKLIST

**Agent implementation specification.** This document provides the ordered, executable checklist for implementing the vectorized data pipeline. The agent must execute these steps in sequence, verifying each gate before proceeding. The agent must NOT execute any step until the developer gives explicit approval for this layer.

## **GLOBAL OPERATING RULES**

1. Execute steps 1–5 (creation & stalling, no activation) without modifying any existing resource.
2. Steps 6–8 (manual verification) are optional — only performed if the developer requests verification before activation.
3. Step 9 (activation) is ONLY executed after the developer explicitly approves post-verification.
4. Each step has a verification gate. If a gate fails, stop and escalate.

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
- [ ] `gsutil ls gs://ftd-vectorized-data/` shows the 5 prefix directories
- [ ] `gsutil versioning get gs://ftd-vectorized-data/` shows `Enabled`
- [ ] IAM policy does not show public access
- [ ] `gsutil iam get gs://ftd-vectorized-data/` shows `uniformBucketLevelAccess` enabled

### **Step 2 — Grant IAM on `raw-data-strg` for the vectorization service account**
- The `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` already has `roles/storage.objectViewer` on `raw-data-strg`
- Verify this is still the case (do not add or remove unless missing)
- If missing: `gsutil iam ch serviceAccount:gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com:roles/storage.objectViewer gs://raw-data-strg/`

**Gate 2 — Verify IAM:**
- [ ] `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` appears with `objectViewer` on `raw-data-strg`
- [ ] No other IAM bindings were modified

### **Step 3 — Upload function source code**
- Create function source ZIP with:
  - `main.py` (vectorization logic per Layer Three)
  - `requirements.txt` (dependencies: `sentence-transformers`, `google-cloud-storage`)
  - Pre-downloaded `all-MiniLM-L6-v2` model in the ZIP (to avoid runtime egress)
- Upload ZIP to: `gs://gcf-v2-uploads-767713105.us-west2.cloudfunctions.appspot.com/vectorize-raw-data.zip`

**Gate 3 — Verify upload:**
- [ ] ZIP uploaded successfully
- [ ] Contains `main.py` and `requirements.txt`
- [ ] Model files (~80MB) included in ZIP

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
- [ ] `gcloud functions describe vectorize-raw-data --region=us-west2` shows state `ACTIVE`
- [ ] No `eventTrigger` field in the function config (confirming no automatic storage trigger)
- [ ] `--ingress-settings=internal` is set

### **Step 5 — Grant developer IAM to invoke the function (for verification)**
- Command:
```bash
gcloud functions add-iam-policy-binding vectorize-raw-data \
  --region=us-west2 \
  --member="user:patrickjosephbutera@gmail.com" \
  --role="roles/cloudfunctions.invoker"
```

**Gate 5 — Verify stalling:**
- [ ] All 4 Cloud Scheduler jobs show `ENABLED` in `gcloud scheduler jobs list`
- [ ] `gsutil notifications list gs://raw-data-strg` shows NO notification pointing to the new function
- [ ] Dropping a test object into `raw-data-strg/SEC/8-K/test/` produces NO output in `ftd-vectorized-data` within 30 seconds
- [ ] Function logs show zero invocations from the test upload

### **Step 6 — Manual verification (optional, developer approval required)**
- Upload test file: `gsutil cp test-file.htm gs://raw-data-strg/SEC/8-K/test/0000000000-26-test/0000000000-test-20260927.htm`
- Invoke function via HTTP with the test object path
- Verify output JSON appears at `gs://ftd-vectorized-data/sec-8k/test/0000000000-26-test/0000000000-test-20260927.json`
- Verify JSON contains 384-dimension vectors
- Clean up: `gsutil rm` test files from both buckets

**Gate 6 — Manual verification passed:**
- [ ] Test invocation succeeds
- [ ] Output vectors are valid (384 dimensions)
- [ ] Test data cleaned up from both buckets

### **Step 7 — Developer approval for activation**
Wait for explicit developer approval before proceeding.

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
- [ ] `gcloud functions describe vectorize-raw-data --region=us-west2 --format="value(eventTrigger)"` shows the storage trigger
- [ ] `gsutil notifications list gs://raw-data-strg` shows the new notification

### **Step 9 — Monitor first automatic invocation**
- Drop a small test file into the appropriate `raw-data-strg` prefix
- Monitor logs: `gcloud functions logs read vectorize-raw-data --region=us-west2 --limit=50`
- Verify vector output appears in `ftd-vectorized-data` with correct path

**Gate 9 — Production verified:**
- [ ] First real invocation through storage trigger succeeds
- [ ] Vector output is correct
- [ ] No errors in logs
- [ ] Existing pipeline (all schedulers, VMs, functions) remains unaffected

## **What to do if any gate fails**

If any verification gate fails, the agent must:
1. Stop all execution
2. Report the failing gate, the exact error or unexpected behavior, and what was inspected
3. Wait for developer decision before proceeding

If a gate fails due to a bug in the approach (not a typo), the agent may spend no more than 5 minutes investigating an alternative, then report and escalate.
