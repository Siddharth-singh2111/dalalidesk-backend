-- Supplier master (Oct 2026): allow more than one phone number in the supplier
-- phone field. The column was VARCHAR(20) (one 10-digit number); widen it to hold
-- several numbers entered together (e.g. "9839033575, 9532151391").
-- Run once:
--   psql -U ... -d ... -f migrations/widen_supplier_phone.sql

ALTER TABLE supplier ALTER COLUMN phone_number TYPE VARCHAR(100);
