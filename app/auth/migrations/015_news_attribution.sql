-- 015: which stored news rows are really about the ticker they are filed under.
-- A GNews batch covers ~5 companies and every article it returned was stored once
-- per company, so most rows are about a different company (or about nothing: "ABT"
-- body kits, "ARE", "ALL"). attributed_by holds the rule that ties the article to
-- the ticker ('name', 'exchange', 'dollar'; see scripts/sync_recent_relational.py)
-- or 'none'. NULL = not labelled yet. Nothing is deleted: the API and the alert
-- evaluator skip 'none' rows, and scripts/attribute_news.py labels existing rows.
ALTER TABLE staging_gnews ADD COLUMN IF NOT EXISTS attributed_by TEXT;
