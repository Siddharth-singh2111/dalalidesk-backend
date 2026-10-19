-- Optional GSTIN on dalali firms, and optional PAN on firms, suppliers and
-- parties (DM sheet item: "GST no optional in dalali firm entry, PAN no in all").
-- Adding columns to EXISTING tables is not handled by SQLAlchemy create_all,
-- so run this on the server before deploying the matching code. Idempotent.

ALTER TABLE firm     ADD COLUMN IF NOT EXISTS gstin VARCHAR(20) DEFAULT NULL;
ALTER TABLE firm     ADD COLUMN IF NOT EXISTS pan   VARCHAR(10) DEFAULT NULL;
ALTER TABLE supplier ADD COLUMN IF NOT EXISTS pan   VARCHAR(10) DEFAULT NULL;
ALTER TABLE party    ADD COLUMN IF NOT EXISTS pan   VARCHAR(10) DEFAULT NULL;

COMMENT ON COLUMN firm.gstin    IS 'GST Identification Number (15 chars); optional';
COMMENT ON COLUMN firm.pan      IS 'PAN (ABCDE1234F); optional';
COMMENT ON COLUMN supplier.pan  IS 'PAN (ABCDE1234F); optional';
COMMENT ON COLUMN party.pan     IS 'PAN (ABCDE1234F); optional';
