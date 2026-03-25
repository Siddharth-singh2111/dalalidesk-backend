-- Add GSTIN to party for OCR / Miracle integration matching.
-- Run once against your PostgreSQL database, e.g.:
--   psql -U ... -d ... -f migrations/add_party_gstin.sql

ALTER TABLE party ADD COLUMN IF NOT EXISTS gstin VARCHAR(20) DEFAULT NULL;

COMMENT ON COLUMN party.gstin IS 'GST Identification Number (India, 15 chars); optional; unique when set';

-- Prevent duplicate parties with same GSTIN when populated
CREATE UNIQUE INDEX IF NOT EXISTS party_gstin_unique
  ON party (gstin)
  WHERE gstin IS NOT NULL AND btrim(gstin) <> '';
