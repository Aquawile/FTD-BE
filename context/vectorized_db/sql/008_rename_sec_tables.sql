-- Migration 008: Rename deprecated SEC PostgreSQL tables
--
-- After migration, these tables are no longer queried for SEC filing data.
-- They are renamed (not dropped) to preserve data for rollback.
--
-- PREREQUISITE: Run after 24h of zero counter values (all SEC endpoints
-- confirmed using GCS).
--
-- Gate: db_access_counters all at 0 for 24h continuous

-- Rename staging_sec → staging_sec_archive
ALTER INDEX IF EXISTS idx_staging_sec_accession_number RENAME TO idx_staging_sec_archive_accession_number;
ALTER INDEX IF EXISTS idx_staging_sec_ticker RENAME TO idx_staging_sec_archive_ticker;
ALTER INDEX IF EXISTS idx_staging_sec_cik RENAME TO idx_staging_sec_archive_cik;
ALTER TABLE staging_sec RENAME TO staging_sec_archive;

-- Rename unified_staging → unified_staging_archive
ALTER INDEX IF EXISTS idx_unified_staging_ticker RENAME TO idx_unified_staging_archive_ticker;
ALTER INDEX IF EXISTS idx_unified_staging_date RENAME TO idx_unified_staging_archive_date;
ALTER INDEX IF EXISTS idx_unified_staging_source RENAME TO idx_unified_staging_archive_source;
ALTER TABLE unified_staging RENAME TO unified_staging_archive;

-- Create views for backward compatibility (return empty result set)
CREATE OR REPLACE VIEW staging_sec AS
    SELECT * FROM staging_sec_archive WHERE FALSE;

CREATE OR REPLACE VIEW unified_staging AS
    SELECT * FROM unified_staging_archive WHERE FALSE;

-- Grant SELECT on views to app user (views return empty results)
GRANT SELECT ON staging_sec, unified_staging TO ftd_app;

-- Comment documenting the rename
COMMENT ON TABLE staging_sec_archive IS 'Renamed from staging_sec during Layer 11 decommission (2026-10-12)';
COMMENT ON TABLE unified_staging_archive IS 'Renamed from unified_staging during Layer 11 decommission (2026-10-12)';
