-- Optional dispatch fields on register_entry: an L.R. number and transport name
-- captured directly when a bill is entered. Bills with these set are picked up
-- by the Local Dispatch Summary report (alongside Dispatch Pad slips).
--
-- Adding columns to an EXISTING table is NOT handled by SQLAlchemy create_all,
-- so this must be run on the server. Idempotent.

ALTER TABLE register_entry ADD COLUMN IF NOT EXISTS lr_number      VARCHAR(50);
ALTER TABLE register_entry ADD COLUMN IF NOT EXISTS transport_name VARCHAR(100);
