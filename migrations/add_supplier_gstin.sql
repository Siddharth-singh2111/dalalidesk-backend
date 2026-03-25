-- Add GSTIN to supplier for OCR / Miracle integration matching.
-- Run once against your PostgreSQL database, e.g.:
--   psql -U ... -d ... -f migrations/add_supplier_gstin.sql

ALTER TABLE supplier ADD COLUMN IF NOT EXISTS gstin VARCHAR(20) DEFAULT NULL;

COMMENT ON COLUMN supplier.gstin IS 'GST Identification Number (India, 15 chars); optional; unique when set';

-- Prevent duplicate suppliers with same GSTIN when populated
CREATE UNIQUE INDEX IF NOT EXISTS supplier_gstin_unique
  ON supplier (gstin)
  WHERE gstin IS NOT NULL AND btrim(gstin) <> '';
