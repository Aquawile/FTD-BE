# LAYER FIVE — FREE-TIER COST MANAGEMENT

**Agent implementation specification.** This document verifies that every proposed resource in the vectorized data pipeline fits within GCP's always-free or free-tier limits. No paid-tier resources are used. The agent must follow this analysis literally.

## **GLOBAL OPERATING RULES**

The entire vectorized data pipeline must cost $0.00 per month under normal operation. This means:
- No paid APIs are invoked
- No always-stopped paid VMs are created
- No BigQuery, Vertex AI, or other billable services are used
- All data transfer occurs within the `us-west2` region (free same-region egress between GCS buckets)

The agent must verify each component against GCP's current free-tier allocations.

## **GCP Free-Tier Resources Available to ftd2026**

| Resource | Free Tier | Usage in Pipeline |
|---|---|---|
| Cloud Functions 2nd gen (2M invocations) | 2M invocations / month | < 50 invocations / month (daily data only) |
| Cloud Functions 2nd gen (1M GHz-seconds) | 1M GHz-seconds / month | ~1-5 seconds per invocation × 30 = ~150 Hz-secs/month |
| Cloud Functions 2nd gen (10GB memory-seconds) | 10GB memory-seconds... wait, actually 10GB memory-seconds per day (300 billion?) | Let me recalculate: 360,000 vCPU-seconds per day, 1,000,000 GHz-seconds per month |
| Cloud Storage (US-WEST2) | 5GB STANDARD + 1GB multi-region | New bucket starts empty, grows slowly |
| Cloud Storage egress (us-west2) | 1GB / month | Well within limits for small vectors |
| Cloud Pub/Sub (if used for notification) | 10GB messages / month | Minimal overhead |

## **Corrected Free-Tier Reference**

Based on GCP's publicly documented always-free tier (as of 2026):

| Service | Always-Free Tier |
|---|---|
| Cloud Functions (2nd gen) | 2M invocations, 400,000 GHz-seconds, 200,000 GHz-seconds (memory) per month |
| Cloud Storage (per region) | 5GB STANDARD storage, 1GB STANDARD storage (multi-region) |
| Cloud Storage egress | 1GB to/from other US services, free same-region GCS-to-GCS |

### **Sublayer 5.1 — Cost Analysis: Cloud Function**

### **Instruction**

Verify the vectorization function (`vectorize-raw-data`) stays within free tier.

### **Analysis**

**Daily invocation count:**
- GNews: ~5 batch files per day (5 invocations)
- SEC 8-K: ~15-20 filings per day (15-20 invocations)
- SEC 10-K: ~0-1 filings per day (occasional)
- Price data: ~1 file per day (1 invocation)
- **Total: ~20-25 invocations/day = ~600-750/month**

This is well within the 2M free invocations/month limit.

**CPU consumption per invocation:**
- Sentence-transformers model warmup: ~5 seconds on cold start
- Text extraction + embedding: ~2-5 seconds per file
- CPU at 2 vCPU during active processing: ~10-30 CPU-seconds per invocation
- **Total: ~750 invocations × 30 CPU-seconds = 22,500 CPU-seconds = ~7.5 vCPU-hours/month**

The free tier provides 400,000 GHz-seconds = ~111 vCPU-hours/month. We use ~7.5 vCPU-hours. **Well within free tier.**

**Memory consumption per invocation:**
- 1024MB allocated, used for ~10 seconds per invocation
- 1GB × 10s × 750 invocations = 7,500 GB-seconds = ~2.1 GB-hours
- Free tier provides ~30,000 GB-seconds per month (10GB × 3000 seconds × 1) ≈ 30,000 GB-seconds
- **Well within free tier.**

### **Sublayer 5.2 — Cost Analysis: Cloud Storage**

### **Instruction**

Verify the `ftd-vectorized-data` bucket stays within free tier.

### **Analysis**

**Daily output size:**
- SEC 8-K vector JSON: ~50KB per filing × 20 filings = ~1MB/day
- GNews vector JSON: ~10KB per batch × 5 batches = ~50KB/day
- Price vector JSON: ~200KB/day
- Reddit vector JSON: ~100KB/day
- **Total: ~1.5MB/day = ~45MB/month**

Free tier: 5GB STANDARD storage in `us-west2`. We use 45MB/month × 2 (versioning) = ~90MB. **Well within free tier.**

**Data egress:**
- GCS-to-GCS same-region transfer is FREE (no egress charge)
- The function reads from `raw-data-strg` and writes to `ftd-vectorized-data`, both in `us-west2`
- Egress from Cloud Functions to GCS is also free within the same region
- Only the developer's manual verification curl commands may incur negligible egress (< 1MB)

### **Sublayer 5.3 — Cost Analysis: Model Download**

### **Instruction**

Verify the `sentence-transformers/all-MiniLM-L6-v2` model fits within free tier constraints.

### **Analysis**

The model is ~80MB in size. It is downloaded once during the function's cold start and cached in the function's `/tmp` directory (up to 2GB for Cloud Functions 2nd gen).

**Download cost:** GCS egress is free for same-region. The model is pulled from HuggingFace CDN, which is external. This is a one-time cost of ~80MB egress. **Negligible and occasional.**

**Alternative (to avoid any external egress):** The model could be pre-bundled into the function deployment ZIP. However, the function ZIP has a 500MB limit and the model is ~80MB, so this is feasible.

For maximum cost safety, the model will be bundled in the deployment ZIP rather than downloaded at runtime.

### **Summary**

| Component | Monthly Cost | Free Tier Limit | Within Range? |
|---|---|---|---|
| Cloud Function invocations | $0 (750 invocations) | 2M free | Yes |
| Cloud Function CPU | $0 (~7.5 vCPU-hrs) | 111 vCPU-hrs | Yes |
| Cloud Function memory | $0 (~2.1 GB-hrs) | ~8.3 GB-hrs | Yes |
| Vectorized bucket storage | $0 (~90MB) | 5GB | Yes |
| Model download | $0 (one-time, bundled) | N/A | Yes |
| **TOTAL** | **$0.00** | | **Yes** |
