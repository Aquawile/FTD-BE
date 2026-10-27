-- Extra rows for the browser tests, applied after tests/schema/seed.sql.
-- Dates are relative to today so the news presets (30 days / 90 days / 1 year / all) stay meaningful.

INSERT INTO tickers (symbol, name, sector, current_price, evidence_score, hype_score, change_percent, updated_at, price_as_of) VALUES
  ('TGT', 'Target Corporation', 'Retail',  118.40, 50, 50,  6.25, now(), now() - interval '1 day'),
  ('EA',  'Electronic Arts',    'Gaming',  209.70, 50, 50, -0.10, now(), '2026-08-04 20:00'),
  ('KO',  'Coca-Cola',          'Beverage',  71.10, 50, 50, -3.40, now(), now() - interval '1 day')
ON CONFLICT DO NOTHING;

-- A real company name on every seeded ticker, the same way staging has them.
INSERT INTO ticker_company_names (symbol, company_name, source) VALUES
  ('TGT', 'Target', 'e2e'), ('EA', 'Electronic Arts', 'e2e'), ('KO', 'Coca-Cola', 'e2e')
ON CONFLICT DO NOTHING;

-- Recent quotes for the new tickers (EA stays stale on purpose: its last quote is August).
INSERT INTO staging_finnhub (target_ticker, target_cik, element_type, content_body, normalized_calendar_date,
                             ingest_date, symbol, "timestamp", "current", change, percent_change, high, low, open, previous_close)
SELECT s.sym, s.cik, 'quantitative', '', d::date, d::date + interval '22 hours', s.sym, d::date + interval '20 hours',
       s.base + (extract(day FROM d)::numeric / 10), 1.0, s.pct, s.base + 3, s.base - 3, s.base, s.base - 1
FROM (VALUES ('TGT', '0000027419', 112.0, 6.2517), ('KO', '0000021344', 70.0, -3.4)) AS s(sym, cik, base, pct)
CROSS JOIN generate_series(current_date - 20, current_date - 1, interval '1 day') AS d;

INSERT INTO staging_finnhub (target_ticker, target_cik, element_type, content_body, normalized_calendar_date,
                             ingest_date, symbol, "timestamp", "current", change, percent_change, high, low, open, previous_close)
SELECT 'EA', '0000712515', 'quantitative', '', d::date, d::date + interval '22 hours', 'EA', d::date + interval '20 hours',
       205 + extract(day FROM d)::numeric / 10, 0.1, -0.1, 210, 200, 206, 206
FROM generate_series('2026-07-20'::date, '2026-08-04'::date, interval '1 day') AS d;

-- NVDA news spread over time, with every attribution label: all of them must show on the ticker page.
INSERT INTO staging_gnews (target_ticker, target_cik, element_type, content_body, normalized_calendar_date, ingest_date, url, attributed_by)
SELECT 'NVDA', '0001045810', 'narrative',
       'E2E NVDA article ' || n || '. Synthetic text long enough to be a real article body for the list view.',
       current_date - age_days, current_date - age_days + 1, 'https://example.com/e2e-nvda-' || n,
       (ARRAY['name', 'batch', 'none', NULL, 'dollar'])[1 + n % 5]
FROM (
  SELECT n, CASE WHEN n <= 25 THEN n % 10 + 1          -- 25 articles in the last 30 days
                 WHEN n <= 55 THEN 40 + n % 40         -- 30 more between 40 and 79 days
                 WHEN n <= 65 THEN 200 + n             -- 10 more in the last year
                 ELSE 450 + n END AS age_days          -- 5 older than a year
  FROM generate_series(1, 70) AS n
) x;

-- A few articles for the other tickers.
INSERT INTO staging_gnews (target_ticker, target_cik, element_type, content_body, normalized_calendar_date, ingest_date, url, attributed_by)
SELECT t, NULL, 'narrative', 'E2E ' || t || ' article ' || n || '. Synthetic text for the list view.', current_date - n, current_date - n + 1,
       'https://example.com/e2e-' || lower(t) || '-' || n, 'batch'
FROM unnest(ARRAY['AAPL', 'TGT', 'KO']) AS t CROSS JOIN generate_series(1, 4) AS n;

-- An account that existed before email verification was required: a Firebase user created in the past
-- (see support/emulator.ts importLegacyUser) whose application row is also old.
INSERT INTO users (email, firebase_uid, created_at) VALUES ('legacy.unverified@example.test', 'e2e-legacy-uid', '2026-09-01 10:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_permissions (user_id, permission_id)
SELECT u.id, p.id FROM users u CROSS JOIN permissions p WHERE u.email = 'legacy.unverified@example.test' ON CONFLICT DO NOTHING;
INSERT INTO user_permissions_index (user_id, permission_name)
SELECT u.id, p.name FROM users u CROSS JOIN permissions p WHERE u.email = 'legacy.unverified@example.test' ON CONFLICT DO NOTHING;
