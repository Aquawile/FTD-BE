# LAYER FOUR — CRON STALLING & PIPELINE ACTIVATION

**Agent implementation specification.** This document defines the stalling strategy that ensures existing cron jobs continue running while the new vectorization pipeline was kept inactive during Layers One-Two-Three, and then the activation strategy that converts it to live event-driven processing. The agent must follow these specifications literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

The user's requirement is explicit: **existing cron jobs must continue feeding `raw-data-strg` unchanged**, while the new vectorization pipeline to `ftd-vectorized-data` was **stalled** during creation and then **activated** after developer approval.

No existing cron job, scheduler, function, or VM configuration is modified during this phase. The stalling was achieved through **selective trigger management**: the Cloud Function was created with an HTTP trigger only (no storage event trigger), and then upgraded to a storage trigger upon approval.

## **Current Cron Jobs (All Remain Untouched)**

| Job Name | Schedule | Cron Expression (UTC) | Target | Function/VM | Status |
|---|---|---|---|---|---|
| `gnews-daily-ingestion` | Daily at 00:00 | `0 0 * * *` | `gnews-ingest` CFN | Writes `gnews/{date}/batch_*.json` to `raw-data-strg` | ENABLED (unchanged) |
| `sec-8k-daily-start` | Daily at 03:30 | `30 3 * * *` | Direct VM start | Starts `data-ingest-vm` for SEC 8-K + lakehouse | ENABLED (unchanged) |
| `lakehouse-daily-pipeline` | Daily at 04:00 | `0 4 * * *` | `start-lakehouse-vm` CFN | Starts `data-ingest-vm` for lakehouse → `processed-layer-one` | ENABLED (unchanged) |
| `start-price-vm-scheduler` | Daily at 21:55 | `55 21 * * *` | `start-price-vm` CFN | Starts `data-ingest-vm` for price data | ENABLED (unchanged) |

## **Sublayer 4.1 — Stalling Strategy (EXECUTED & VERIFIED)**

### **Instruction**

The objective of Sublayer 4.1 is to ensure that no vectorization occurs on any existing or incoming data until the developer explicitly activates the pipeline. The vectorization function exists but receives no events.

### **Stalling mechanism: delayed trigger attachment**

The Cloud Function was created **without** a Cloud Storage trigger. Instead:

1. The function source code was uploaded to `gcf-v2-sources-767713105-us-west2` via `gcloud functions deploy`
2. The function was deployed as an **HTTP-triggered function** (not storage-triggered)
3. The function's IAM was set to allow the developer's account to invoke it for manual testing
4. No Cloud Storage notification was created on `raw-data-strg`

This means:
- New objects flowing into `raw-data-strg` did NOT trigger any vectorization
- The function exists and can be tested manually via HTTP
- The pipeline remains completely inert until activation

### **Implementation steps (executed)**

**Step A — Function source deployment (no trigger):**
```bash
gcloud functions deploy vectorize-raw-data \
  --gen2 \
  --runtime=python311 \
  --region=us-west2 \
  --source=/Users/isabellabutera/gcloud-bucket-data/vectorized-db-function \
  --entry-point=process_file \
  --memory=1024MB \
  --timeout=300s \
  --max-instances=10 \
  --concurrency=1 \
  --service-account=gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com \
  --set-env-vars=GCS_OUTPUT_BUCKET=ftd-vectorized-data,EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2,MAX_TEXT_LENGTH=100000 \
  --ingress-settings=internal-and-gclb \
  --trigger-http
```

**Step B — Function deployed successfully:**
- State: `ACTIVE`
- URI: `https://us-west2-ftd2026.cloudfunctions.net/vectorize-raw-data`
- Source: `gs://gcf-v2-sources-767713105-us-west2/vectorize-raw-data/function-source.zip`

**Step C — Grant IAM for manual testing:**
```bash
gcloud functions add-iam-policy-binding vectorize-raw-data \
  --region=us-west2 \
  --member="user:patrickjosephbutera@gmail.com" \
  --role="roles/cloudfunctions.invoker"

gcloud functions add-invoker-policy-binding vectorize-raw-data \
  --region=us-west2 \
  --member="user:patrickjosephbutera@gmail.com"
```

### **Verification of stalling (executed & passed)**

Verified on 2026-09-27:
1. ✓ `eventTrigger` absent from function config (only `httpsTrigger` present) — confirmed via API
2. ✓ No storage notifications on `raw-data-strg` — confirmed via GCS API
3. ✓ All 4 Cloud Scheduler jobs `ENABLED` and unchanged — confirmed via API
4. ✓ Test object upload to `raw-data-strg` produced NO output in `ftd-vectorized-data` — confirmed via GCS API (test file cleaned up)

## **Sublayer 4.2 — Manual Verification Method (Executed)**

### **Instruction**

The objective of Sublayer 4.2 is to define the manual verification process that proves the vectorization pipeline works correctly before enabling it for automatic (cron-driven) operation.

### **Verification procedure**

1. **Upload a test file to `raw-data-strg`:**
   ```bash
   echo "<html><body>Test filing content for vectorization verification</body></html>" > /tmp/test-sec-8k.htm
   gsutil cp /tmp/test-sec-8k.htm gs://raw-data-strg/SEC/8-K/99999999/0000000000-26-000000/test-8k-20260927.htm
   ```

2. **Invoke the function manually via HTTP:**
   ```bash
   FUNC_URL=$(gcloud functions describe vectorize-raw-data --region=us-west2 --format="value(url)")
   curl -X POST "$FUNC_URL" \
     -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
     -H "Content-Type: application/json" \
     -d '{"bucket": "raw-data-strg", "name": "SEC/8-K/99999999/0000000000-26-000000/test-8k-20260927.htm"}'
   ```

3. **Check the output in `ftd-vectorized-data`:**
   ```bash
   gsutil ls gs://ftd-vectorized-data/sec-8k/99999999/0000000000-26-000000/
   gsutil cat gs://ftd-vectorized-data/sec-8k/99999999/0000000000-26-000000/test-8k-20260927.json | python3 -m json.tool
   ```

4. **Verify vector dimensions:**
   - The JSON output must contain `"dimension": 384`
   - Each chunk must have a non-empty `"vector"` array of 384 floats
   - The `"chunks"` array must have at least 1 entry

5. **Clean up test data:**
   ```bash
   gsutil rm gs://raw-data-strg/SEC/8-K/99999999/0000000000-26-000000/test-8k-20260927.htm
   gsutil rm gs://ftd-vectorized-data/sec-8k/99999999/0000000000-26-000000/test-8k-20260927.json
   ```

### **Verification gate**

The pipeline was manually verified via HTTP invocation. Test data was uploaded and cleaned up. Vectors were confirmed to be 384-dimensional.

## **Sublayer 4.3 — Activation (Deferred)**

### **Instruction**

The activation step is NOT executed during this phase. It is documented here for completeness but will only be executed after the developer explicitly approves after manual verification.

### **Activation steps (deferred)**

When the developer approves, the agent executes:

1. **Create the Cloud Storage notification:**
   ```bash
   gcloud storage notifications create gs://raw-data-strg \
     --event-types=OBJECT_FINALIZE \
     --payload-format=JSON_API_V1 \
     --topic=vectorize-raw-data-topic
   ```

2. **Create a Pub/Sub subscription and link to the function:**
   ```bash
   gcloud functions deploy vectorize-raw-data \
     --gen2 \
     --update-trigger-storage=raw-data-strg
   ```

3. **Confirm the trigger is attached:**
   ```bash
   gcloud functions describe vectorize-raw-data --region=us-west2 --format="value(eventTrigger)"
   ```

4. **Monitor the first automatic invocation:**
   ```bash
   gcloud functions logs read vectorize-raw-data --region=us-west2 --limit=50
   ```

### **Security consideration on activation**

When activation occurs, the function will fire on ALL `OBJECT_FINALIZE` events in `raw-data-strg`. The function source code already skips `metadata.txt` files and the `SEC/config/` directory, so these do not trigger vectorization. No additional Cloud Scheduler jobs or triggers are needed — the function is event-driven.
