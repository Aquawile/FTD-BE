# Lakehouse Staging Pipeline

First-layer processing for Option 1: Relational-Analytical Lakehouse Staging.

## Run

```bash
cd /Users/isabellabutera/gcloud-bucket-data
PYTHONPATH=/Users/isabellabutera/gcloud-bucket-data:/Users/isabellabutera/gcloud-bucket-data/sec /Users/isabellabutera/gcloud-bucket-data/.venv/bin/python3 -m lakehouse.orchestrator
```

## Output (GCS)

Parquet files under `gs://raw-data-strg/lakehouse/staging/`:
- `staging_finnhub.parquet` — ~4,957 price rows
- `staging_gnews.parquet` — ~73,980 sentiment article rows
- `staging_sec.parquet` — ~767,808 narrative/quantitative elements from 8-Ks and 10-Ks
- `fiscal_parameters.parquet` — ~197 fiscal year-end parameters extracted from 10-K cover pages

## Notes

- Runs locally using pandas + pyarrow + google-cloud-storage.
- Reuses Fortune 500 roster and SEC client from `sec/src/`.
- 10-K HTML is parsed with BeautifulSoup; tables are converted to Markdown matrices.
- Fiscal year-end extraction uses regex on visible text and inline XBRL tags.
