-- 016: profile photo kept with the account, so it follows the user to any browser or device.
-- A small JPEG data URL (the web app shrinks it to ~160 px before upload); NULL = no photo.
-- Additive only: nothing existing is changed.
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar TEXT;
