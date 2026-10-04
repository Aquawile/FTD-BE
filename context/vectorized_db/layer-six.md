# LAYER SIX — SAFETY, VERIFICATION & ROLLBACK

**Agent implementation specification.** This document defines all safety measures, verification gates, and rollback procedures for the vectorized data pipeline. The agent must follow these specifications literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

The vectorized data pipeline must be designed with fail-safe principles: if anything goes wrong, the existing raw data pipeline remains fully operational. No rollback should ever affect `raw-data-strg`, `processed-layer-one`, or any existing VM, function, or cron job.

All verification must be performed using read-only operations on existing resources and explicit test-and-cleanup for new resources.

## **Sublayer 6.1 — Safety Principles**

### **Instruction**

The objective of Sublayer 6.1 is to enumerate the safety properties that must hold at all times during implementation and beyond.

### **Safety properties**

1. **Existing pipeline isolation:** The new `ftd-vectorized-data` bucket, the `vectorize-raw-data` function, and all new service accounts are completely isolated from existing resources. No existing resource reads from, writes to, or is triggered by the new pipeline during the creation and verification phase.

2. **No bulk processing:** The function processes one object per invocation. There is no batch or bulk mode that could unexpectedly process historical data.

3. **No cron job modification:** Every existing Cloud Scheduler job is verified to be `ENABLED` and unchanged after each step. If any job is found disabled or modified, the agent must stop and escalate.

4. **No VM modification:** The data-ingest VM, staging API VM, and staging web VM are not started, stopped, reconfigured, or accessed unless explicitly needed for testing. Their startup scripts, metadata, and IAM bindings remain untouched.

5. **Read-only access to raw-data-strg:** The vectorization function has `storage.objectViewer` on `raw-data-strg` (read-only). It can never delete or modify raw data objects.

6. **Write-only access to ftd-vectorized-data:** The function has `storage.objectAdmin` on `ftd-vectorized-data` (write). It can create and overwrite vector files but cannot affect raw data.

7. **Free tier cap:** Max instances is set to 10, preventing runaway cost from unexpected event spikes. All operations fit within free-tier limits as documented in Layer Five.

## **Sublayer 6.2 — Verification Gates**

### **Instruction**

Define the explicit checkpoints that must pass before moving from one phase to the next.

### **Gate 1: Bucket creation verified**

After Layer Two execution:
- [ ] `gsutil ls gs://ftd-vectorized-data/` returns empty (no stray objects)
- [ ] `gsutil versioning get gs://ftd-vectorized-data/` returns `Enabled`
- [ ] IAM policy matches `raw-data-strg` (publicAccessPrevention: enforced)
- [ ] Directory prefixes (`sec-10k/`, `sec-8k/`, `gnews/`, `prices/`, `reddit/`) exist (created as zero-byte marker files if needed)

### **Gate 2: Function deployment verified**

After Layer Three execution:
- [ ] `gcloud functions describe vectorize-raw-data --region=us-west2` shows state `ACTIVE`
- [ ] No `eventTrigger` exists in the function config (HTTP trigger only)
- [ ] Function service account has `storage.objectViewer` on `raw-data-strg` and `storage.objectAdmin` on `ftd-vectorized-data`
- [ ] `requirements.txt` includes `sentence-transformers` and `google-cloud-storage`

### **Gate 3: Stall confirmed**

After Layer Four execution:
- [ ] All 4 Cloud Scheduler jobs are `ENABLED` (verified via `gcloud scheduler jobs list`)
- [ ] Dropping a test object into `raw-data-strg` produces NO new objects in `ftd-vectorized-data` within 30 seconds
- [ ] Function logs show no automatic invocations after the test object is uploaded
- [ ] No Cloud Storage notification exists on `raw-data-strg` for the new function's topic

### **Gate 4: Manual verification**

Before activation (Layer Four, Sublayer 4.2):
- [ ] HTTP invocation of the function succeeds with test payload
- [ ] Output JSON appears at the expected path in `ftd-vectorized-data`
- [ ] Output JSON contains valid 384-dimension vectors
- [ ] Test data is cleaned up from both buckets

### **Gate 5: Activation confirmed**

After activation (Layer Four, Sublayer 4.3):
- [ ] `gcf` notification exists on `raw-data-strg` with `OBJECT_FINALIZE` event type
- [ ] First real data arrival triggers the function automatically
- [ ] Vector output appears in `ftd-vectorized-data` with correct path mapping
- [ ] Cloud Logging shows successful processing with no errors

## **Sublayer 6.3 — Rollback Procedures**

### **Instruction**

Define the exact steps to undo any part of the new pipeline without affecting existing resources.

### **Rollback A: Deactivate the pipeline (after activation)**

If the pipeline causes issues after activation:

1. **Remove the Cloud Storage trigger:**
   ```bash
   # Delete the notification from raw-data-strg
   gcloud storage notifications delete <notification-id> --bucket=raw-data-strg
   ```

2. **Verify no further invocations:**
   Upload a test file to `raw-data-strg` and confirm no vectorization occurs within 30 seconds.

3. **The existing pipeline continues unchanged** — all raw data, processing, and PostgreSQL writes continue as before.

### **Rollback B: Delete the function**

If the function itself needs to be removed:

1. `gcloud functions delete vectorize-raw-data --region=us-west2`
2. Verify no resources in `raw-data-strg` were modified
3. Existing pipeline unaffected

### **Rollback C: Delete the vectorized bucket (pre-activation only)**

If the bucket was created but not yet activated:

1. Empty the bucket: `gsutil rm -r gs://ftd-vectorized-data/**`
2. Delete the bucket: `gsutil rb gs://ftd-vectorized-data/`
3. No existing resources are affected.

### **Rollback D: Full reset (post-activation, catastrophic failure)**

If the entire vectorized pipeline must be removed:

1. Deactivate the pipeline (Rollback A)
2. Delete the function (Rollback B)
3. Empty and delete the bucket (Rollback C + empty)
4. Delete any Cloud Pub/Sub topics created for notifications
5. Verify all existing schedulers are still `ENABLED`
6. Verify all existing VMs are unchanged

**None of these rollback procedures touch any existing resource. The raw data bucket, processed-layer-one, all VMs, all existing functions, and all existing cron jobs remain untouched.**
