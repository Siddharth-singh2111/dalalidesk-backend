-- Scheme bills (Sept 2026): when a supplier denies a scheme the party had
-- deducted, the scheme amount is raised as its own bill so dalali is earned on
-- it and the party's separate cheque can settle it. A scheme bill is a normal
-- register_entry, flagged and linked back to the original bill.
-- Run once against your PostgreSQL database:
--   psql -U ... -d ... -f migrations/add_register_entry_scheme.sql

ALTER TABLE register_entry ADD COLUMN IF NOT EXISTS is_scheme BOOLEAN DEFAULT FALSE;
ALTER TABLE register_entry ADD COLUMN IF NOT EXISTS scheme_source_bill_id INT REFERENCES register_entry(id);

COMMENT ON COLUMN register_entry.is_scheme IS 'TRUE when this bill is a denied-scheme amount raised as a bill';
COMMENT ON COLUMN register_entry.scheme_source_bill_id IS 'The original bill this scheme was deducted from (for reference)';
