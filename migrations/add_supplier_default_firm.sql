-- Optional default firm for a supplier. Pre-fills the receiver firm when a
-- dalali entry is created for the supplier (the user can still change it there).
-- Run once:
--   psql -U ... -d ... -f migrations/add_supplier_default_firm.sql

ALTER TABLE supplier ADD COLUMN IF NOT EXISTS default_firm_id INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'supplier_default_firm_id_fkey'
          AND table_name = 'supplier'
    ) THEN
        ALTER TABLE supplier
            ADD CONSTRAINT supplier_default_firm_id_fkey
            FOREIGN KEY (default_firm_id) REFERENCES firm(id);
    END IF;
END$$;
