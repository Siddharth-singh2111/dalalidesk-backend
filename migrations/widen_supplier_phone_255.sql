-- Supplier phone is now a tagged list stored as
--   "Owner: +91 98390 33575, Accounts: +91 95321 51391"
-- The type labels make the value longer, so widen the column from 100 to 255.
-- Run once:
--   psql -U ... -d ... -f migrations/widen_supplier_phone_255.sql

ALTER TABLE supplier ALTER COLUMN phone_number TYPE VARCHAR(255);
