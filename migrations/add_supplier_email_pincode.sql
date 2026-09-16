-- Supplier master: add Email ID and PIN code (Sept 2026).
-- City already exists on supplier. Run once against your PostgreSQL database:
--   psql -U ... -d ... -f migrations/add_supplier_email_pincode.sql

ALTER TABLE supplier ADD COLUMN IF NOT EXISTS email VARCHAR(120);
ALTER TABLE supplier ADD COLUMN IF NOT EXISTS pin_code VARCHAR(10);

COMMENT ON COLUMN supplier.email IS 'Supplier email address (optional)';
COMMENT ON COLUMN supplier.pin_code IS 'Supplier PIN code (optional, string to preserve leading zeros)';
