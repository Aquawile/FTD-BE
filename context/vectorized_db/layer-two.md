# LAYER TWO — VECTORIZED DATA BUCKET CREATION

**Agent implementation specification.** This document specifies the creation of the `ftd-vectorized-data` GCS bucket. The agent must follow these specifications literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

The new vectorized data bucket must mirror the security and location settings of the existing `raw-data-strg` and `processed-layer-one` buckets so that the same service accounts and network access patterns apply. The bucket must be created in `us-west2` (same region as the raw data bucket) to ensure free same-region data transfer.

The agent must not modify any existing bucket properties, IAM bindings, or lifecycle rules. Only the new bucket is created.

The bucket must use the same security posture as `raw-data-strg`:
- `publicAccessPrevention: enforced`
- `uniformBucketLevelAccess: enabled`
- `bucketPolicyOnly: enabled`

### **Naming Convention**

Following the existing bucket naming pattern (`raw-data-strg`, `processed-layer-one`), the new bucket is named `ftd-vectorized-data`. This name:
- Is globally unique (verified against all existing GCS bucket names in the project)
- Clearly indicates it stores vectorized embeddings
- Does not collide with any existing bucket name

### **Sublayer 2.1 — Bucket Creation Command**

### **Instruction**

The objective of Sublayer 2.1 is to create the `ftd-vectorized-data` bucket with the exact configuration needed to receive vectorized data from the future pipeline.

### **Implementation**

**Executed on 2026-09-27 with the `patrickjosephbutera@gmail.com` account:**

The bucket was created using the GCS JSON API (gsutil CLI timed out due to network latency) with all settings in a single POST:

```bash
# Created via GCS JSON API (gsutil was timing out)
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ftd-vectorized-data",
    "location": "US-WEST2",
    "storageClass": "STANDARD",
    "iamConfiguration": {
      "uniformBucketLevelAccess": {"enabled": true},
      "publicAccessPrevention": "enforced"
    },
    "versioning": {"enabled": true},
    "lifecycle": {
      "rule": [{"action": {"type": "Delete"}, "condition": {"age": 365}}]
    }
  }' \
  "https://storage.googleapis.com/storage/v1/b?project=ftd2026"
```

IAM bindings added via `gsutil iam ch` (successful after 3-48s):
```bash
gsutil iam ch "serviceAccount:767713105-compute@developer.gserviceaccount.com:roles/storage.objectAdmin" gs://ftd-vectorized-data/
gsutil iam ch "serviceAccount:gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com:roles/storage.objectAdmin" gs://ftd-vectorized-data/
gsutil iam ch "user:patrickjosephbutera@gmail.com:roles/storage.objectViewer" gs://ftd-vectorized-data/
```

### **Directory Structure (pre-created)**

The directory structure mirrors the source structure in `raw-data-strg` so that the vectorization function can map input paths to output paths deterministically. No placeholder objects were created — the prefixes will be created on first write by the vectorization function.

### **Verification**

The agent verified the bucket is correctly configured on 2026-09-27:

1. `curl -H "Authorization: Bearer $ACCESS_TOKEN" "https://storage.googleapis.com/storage/v1/b/ftd-vectorized-data"` — confirmed bucket exists with:
   - `location: US-WEST2`
   - `storageClass: STANDARD`
   - `versioning.enabled: true`
   - `iamConfiguration.publicAccessPrevention: enforced`
   - `iamConfiguration.uniformBucketLevelAccess.enabled: true`
   - `lifecycle.rule[0].action.type: Delete`, `condition.age: 365`

2. IAM verified on `ftd-vectorized-data`:
   - `roles/storage.objectAdmin` → `serviceAccount:767713105-compute@developer.gserviceaccount.com`
   - `roles/storage.objectAdmin` → `serviceAccount:gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com`
   - `roles/storage.objectViewer` → `user:patrickjosephbutera@gmail.com`
   - `publicAccessPrevention: enforced` (no public access)
   - Only legacy project-level roles exist for Editor/Viewer (default, expected)

3. Confirmed bucket is empty (no objects in `ftd-vectorized-data`)

4. Confirmed `raw-data-strg` IAM was NOT modified — `gnews-ingestion-sa` already had `objectViewer`

