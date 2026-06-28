# FTD Reddit Ingestion Pipeline

Ingests Reddit posts mentioning tracked tickers into GCS via a Devvit app + GCP Cloud Function bridge.

## Architecture

```
Devvit (Reddit-hosted)
  │  1. Search for ticker posts in target subreddits
  │  2. Sanitize + batch
  │  3. POST JSON to GCP Cloud Function (with X-API-Key auth)
  ▼
Cloud Function: reddit-ingest  (GCP)
  │  1. Validate API key
  │  2. Write each post to GCS
  ▼
GCS: gs://raw-data-strg/reddit/YYYY-MM-DD/{post_id}.json
```

## Project Layout

```
reddit/
├── devvit-app/           # TypeScript app deployed to Reddit via Devvit
│   ├── src/
│   │   └── main.ts       # Scheduler entrypoint, search, fetch bridge
│   ├── devvit.json       # Declares "reddit" + "scheduler" permissions
│   ├── package.json
│   └── .env.example
│
├── cloud-function/       # Python Cloud Function deployed to GCP
│   ├── main.py           # Flask HTTP endpoint
│   ├── requirements.txt
│   └── .env.example
│
└── scripts/
    └── deploy_function.sh   # gcloud functions deploy wrapper
```

## Prerequisites

- Node.js 20+ and `npm`
- `devvit` CLI (`npm install -g devvit`)
- GCP project with `gcloud` authenticated
- Cloud Functions / Cloud Build APIs enabled on the project
- A GCS bucket with `raw-data-strg` (or override via `.env`)
- GCS default service account needs `roles/storage.objectCreator` on the bucket

## Setup

### 1. Deploy the Cloud Function

```bash
cd reddit
cp cloud-function/.env.example cloud-function/.env
# Edit .env and set a strong INGESTION_API_KEY

bash scripts/deploy_function.sh
# Outputs the function URL — save it
```

### 2. Seed the Devvit App config

```bash
cd reddit/devvit-app
cp .env.example .env

# Set INGESTION_ENDPOINT to the URL from step 1
# Set INGESTION_API_KEY to the SAME value used in the Cloud Function
```

### 3. Deploy the Devvit App

```bash
npm install
npx devvit deploy
```

## Data Layout in GCS

```
reddit/
├── YYYY-MM-DD/
│   ├── abc123.json
│   ├── def456.json
│   └── ...
```

Each JSON file is a single Reddit post or comment with fields:
- `id` — `t3_abc123` or `t1_xyz789`
- `content` — title + body text (for posts)
- `timestamp` — UTC ISO 8601
- `author` — Reddit username (null if deleted)
- `score`, `numComments`
- `permalink`, `ticker`, `subreddit`, `type`

## Reuse from SEC Pipeline

The following components from `sec/` can be directly reused:
- `gcs_storage.py` pattern (generic GCS read/write)
- `error_logger.py` (for local development logging)
- VM lifecycle / monitoring scripts (when scaling to heavier workloads)
- Config loading pattern (`Settings.from_env()`)

## Next Steps

- [ ] Add 10-K / earnings call transcript fetching
- [ ] Normalize metadata into BigQuery for agent queries
- [ ] Hype-vs-Evidence scoring on ingested content
