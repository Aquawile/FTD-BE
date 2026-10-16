# Part Four — Vectorized Data Pipeline Creation

## Overview

This part introduces a vectorized data storage layer that runs alongside (not parallel to) the existing data ingestion pipeline. The goal is to capture **future** incoming raw data, vectorize it, and store the vectors in a dedicated GCS bucket — all within GCP's free tier. The existing raw-data ingestion pipeline remains completely untouched: data continues flowing into `raw-data-strg` via the same cron jobs and Cloud Functions. No bulk migration of existing raw data is performed. No PostgreSQL writes occur during this phase.

## Architecture Constraints

| Property | Value |
|---|---|
| GCP Project | `ftd2026` (project number `767713105`) |
| Region | `us-west2` |
| Raw data bucket | `raw-data-strg` (existing, untouched) |
| Processed layer (existing) | `processed-layer-one` (existing, untouched) |
| Vectorized data bucket | `ftd-vectorized-data` (new, created in this phase) |
| Billing account | `012D3E-0648EB-F8C9E8` (enabled) |
| Free tier | Must be entirely free-tier capable |

## Data Access Rules

- **The new vectorized pipeline must only process data that arrives in `raw-data-strg` AFTER the pipeline is activated.** All existing objects in `raw-data-strg` remain where they are and are never bulk-processed.
- **Existing cron jobs and data ingestion must continue unmodified.** The `gnews-daily-ingestion`, `sec-8k-daily-start`, `start-price-vm-scheduler`, and `lakehouse-daily-pipeline` schedulers all keep running and writing to `raw-data-strg` exactly as before.
- **No PostgreSQL writes during this phase.** Vector data lives only in the new GCS bucket. PostgreSQL integration comes after vectorized data storage is verified.
- **Vectorization must be lightweight.** The approach must fit within Cloud Run free-tier limits (2M requests/month, 360K vCPU-seconds, 180GB egress) or Cloud Functions free-tier limits (2M invocations, 1M GB-seconds, 400K GHz-seconds).
- **No bulk operations.** No scheduled "bulk backfill" job runs against existing raw data. Each vectorization trigger processes one file at a time, on arrival.

## What This Part Does NOT Include

- No modifications to existing cron jobs, Cloud Functions, or VMs in the current pipeline
- No bulk migration of existing raw data to the vectorized bucket
- No PostgreSQL integration or writes (deferred to a later phase)
- No BigQuery dataset creation (free tier has 1TB scanned/month, but we defer to verify first)
- No changes to the existing data-ingest VM startup script or lakehouse pipeline
- No new paid APIs or services (Vertex AI is NOT enabled; we use free alternatives)

## Layer Map

| Layer | Title | Scope |
|---|---|---|
| One | Raw Data Source Analysis & Preservation | Document existing data sources, bucket structure, and verify they remain untouched |
| Two | Vectorized Data Bucket Creation | Plan and specify the new bucket creation (naming, IAM, lifecycle, location) |
| Three | Vectorization Function Design | Design the serverless function that vectorizes incoming data |
| Four | Cron Stalling & Pipeline Activation | Plan how existing cron jobs stay running while new pipeline stays stalled until verified |
| Five | Free-Tier Cost Management | Verify all components fit within GCP free tier allocations |
| Six | Safety, Verification & Rollback | Define verification steps, health checks, and rollback procedures |
| Seven | Incremental Implementation Checklist | Ordered steps to execute sublayer by sublayer with verification gates |
| High-Level | High-Level Vectorized Data Architecture | Summary of the full plan |
| Eight | API Migration to Vectorized Data | Migrate API endpoints from PostgreSQL to GCS-backed vectorized data |
| Nine | UI-to-API-to-Data Source Trace | End-to-end trace of every UI data binding through API to data source |
| Ten | Audit Logging, User Fingerprinting & Log Files | Dual logging to PostgreSQL and file-based logs, user fingerprinting |
| Eleven | Counter Monitoring & Table Decommission | In-memory counters for DB access, PostgreSQL table rename procedure |
| Twelve | UI Validation & Production Cutover | Endpoint-by-endpoint validation, cutover checklist, rollback procedures |

## Global Operating Rules

1. **Preserve existing infrastructure.** No existing bucket, function, VM, cron job, or service account is modified or deleted during this phase. Only new resources are created.
2. **No execution without planning.** All steps are documented first. Code execution only begins after all layer documents are complete and the developer approves the plan.
3. **Free tier only.** Every component must fit within GCP's always-free or free-tier limits. No paid tier resources are provisioned.
4. **Incremental activation.** The vectorization pipeline is created but NOT activated until verified. Activation is a deliberate, separate step.
5. **One file at a time.** The vectorization trigger fires per-object. No batch processing of multiple files in a single invocation.
6. **Verification gates.** Each sublayer has a clear verification criterion. Execution stops and escalates if a gate cannot be met.
