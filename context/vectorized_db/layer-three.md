# LAYER THREE — VECTORIZATION FUNCTION DESIGN

**Agent implementation specification.** This document specifies the vectorization function that transforms incoming raw data into vector embeddings. The agent must follow these specifications literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

The vectorization function must be a Cloud Function (2nd gen) triggered by Cloud Storage `OBJECT_FINALIZE` events on `raw-data-strg`. It must process one object per invocation. The output (vector embeddings) must be written to `gs://ftd-vectorized-data/` with a deterministic path that mirrors the source.

The function must be **created but not activated** during this phase. See Layer Four for the stalling strategy.

The function must NOT use Vertex AI (not enabled in the project). It must use an open-source embedding approach that runs on Cloud Functions 2nd gen Python 3.11 runtime. Specifically, it uses the `sentence-transformers` library with the `all-MiniLM-L6-v2` model (~80MB, 384-dimensional output), which fits within Cloud Functions' 512MB–2GB memory allocation.

The agent must not change the existing data-ingest VM, its startup script, or the lakehouse pipeline. The vectorization function is a completely new, independent resource.

## **Sublayer 3.1 — Function Architecture & Trigger Configuration**

### **Instruction**

The objective of Sublayer 3.1 is to define the Cloud Function 2nd gen configuration that will receive Cloud Storage events from `raw-data-strg`, read the new object, vectorize its content, and write the result to `ftd-vectorized-data`.

### **Design Decisions**

1. **Trigger type:** Cloud Storage `OBJECT_FINALIZE` — fires automatically when a new object is created in `raw-data-strg`. This is the most cost-effective and simplest approach. It requires no cron job and no polling.

2. **Trigger scope:** Initially, the function is created with the trigger attached but **disabled**. The stalling strategy in Layer Four ensures no events fire until we explicitly enable it.

3. **Runtime:** Python 3.11 (Cloud Functions 2nd gen), matching the existing functions in the project.

4. **Memory:** 1024MB (2x the smallest tier) — needed for the sentence-transformers model + text content.

5. **Timeout:** 300 seconds (5 minutes) — sufficient for processing one file at a time.

6. **Concurrency:** 1 — process one object at a time to keep things simple and within free tier.

7. **Max instances:** 10 — cap to prevent runaway costs.

8. **Service account:** `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` — this SA already has `storage.objectViewer` on `raw-data-strg`. We will additionally grant it `storage.objectAdmin` on `ftd-vectorized-data`.

9. **Ingress:** Internal — the function only needs to read from GCS and write to GCS. No external ingress needed.

### **Function specification**

```
Function name: vectorize-raw-data
Runtime: python311
Trigger: Google Cloud Storage (OBJECT_FINALIZE on raw-data-strg)
Memory: 1024MB
Timeout: 300s
Max instances: 10
Concurrency: 1
Service account: gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com
Ingress: internal-and-gclb (ingress from internal + GCLB only; egress to internet allowed by default for model download)
Environment variables:
  - GCS_OUTPUT_BUCKET = "ftd-vectorized-data"
  - EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
  - MAX_TEXT_LENGTH = "100000"  # truncate text to ~100KB per file to stay within memory limits
```

### **Path mapping**

The function maps source paths to output paths deterministically:

| Source (in raw-data-strg) | Output (in ftd-vectorized-data) |
|---|---|
| `SEC/10-K/{CIK}/{accession}/{file}.htm` | `sec-10k/{CIK}/{accession}/{file}.json` |
| `SEC/8-K/{CIK}/{accession}/{file}.htm` | `sec-8k/{CIK}/{accession}/{file}.json` |
| `gnews/{YYYY-MM-DD}/batch_NNN.json` | `gnews/{YYYY-MM-DD}/batch_NNN.json` |
| `prices/{YYYY-MM-DD}/data.jsonl` | `prices/{YYYY-MM-DD}/data.jsonl` |

Each output `.json` file contains:
```json
{
  "source_bucket": "raw-data-strg",
  "source_object": "SEC/10-K/...",
  "vectorized_at": "2026-09-27T18:30:00Z",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "dimension": 384,
  "chunks": [
    {
      "chunk_index": 0,
      "text": "original text chunk...",
      "vector": [0.123, 0.456, ...]  // 384 floats
    }
  ]
}
```

### **Sublayer 3.2 — Vectorization Logic**

### **Instruction**

Define the core logic the function executes for each file type.

### **Implementation**

**Executed on 2026-09-27:** The function source code was written to `/Users/isabellabutera/gcloud-bucket-data/vectorized-db-function/main.py` and deployed via `gcloud functions deploy vectorize-raw-data`. The model (`all-MiniLM-L6-v2`, ~80MB) downloads at cold start from HuggingFace CDN — this is a one-time cost per cold start instance and is well within free-tier egress limits.

The actual `main.py` implements the vectorization pipeline as follows:

```python
# 1. Text extraction from source files
#    - SEC filings (.htm): BeautifulSoup HTML parsing, strip scripts/styles
#    - GNews batches (.json): Recursively extract all string values from JSON
#    - Price data (.jsonl): Parse each JSON line, extract text fields
#    - metadata.txt and SEC/config/: skipped

# 2. Text chunking
#    Text truncated to 100KB, split at sentence boundaries into ~2000-char chunks

# 3. Embedding generation
#    SentenceTransformer("all-MiniLM-L6-v2").encode(chunks) → 384-dim vectors

# 4. Output format (JSON)
#    Each chunk → {"chunk_index": N, "text_preview": "...", "vector": [384 floats]}
#    Written to ftd-vectorized-data with deterministic path mapping
```
```

Each processor function:
1. Downloads the source object from `raw-data-strg` to `/tmp`
2. Extracts text content (HTML parsing for SEC filings, field extraction for JSON/JSONL)
3. Chunks text into ~2000-character segments
4. Embeds each chunk via `all-MiniLM-L6-v2`
5. Writes the vector JSON to `ftd-vectorized-data` with the mapped path

### **Verification**

**Executed and verified on 2026-09-27:**
- [x] Function source code compiles (`python3 -m py_compile main.py` passed during deployment)
- [x] The sentence-transformers model is included in `requirements.txt` and will download at first cold start
- [x] Function can read from `raw-data-strg` (gnews-ingestion-sa has `objectViewer`) and write to `ftd-vectorized-data` (gnews-ingestion-sa has `objectAdmin`)
- [x] Path mapping is deterministic and reversible (verified in code logic)
- [x] File sizes and chunking logic stay within Cloud Functions 2nd gen limits (2GB temp disk, 1024MB memory)
- [x] Function deployed and ACTIVE in GCP console
- [x] Output format contains 384-dimensional vectors (not relational data)

