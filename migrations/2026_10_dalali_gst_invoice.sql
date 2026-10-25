-- Dalali bill = GST tax invoice (DM, Oct 2026).
--
-- 1. Firms keep several phone numbers ("Tel: 0512 2357579, Mob: 9336116215")
--    and an email. The 20-character phone column made firm edits with two
--    numbers fail (DM sheet row 13), so the masters' phone columns are widened.
-- 2. A firm bank carries the details printed on the invoice: account number,
--    account type, IFSC and branch.
-- 3. A dalali entry names the firm + bank it is billed from (no more ₹1
--    receiver payment just to declare them), the bill date, the invoice
--    number, and the GST block worked out when it was saved (an issued
--    invoice never changes when a memo is edited later).
--
-- SQLAlchemy create_all does not add columns to existing tables, so run this
-- before deploying the matching code. Idempotent.

BEGIN;

ALTER TABLE firm      ALTER COLUMN phone_number TYPE VARCHAR(255);
ALTER TABLE firm_bank ALTER COLUMN phone_number TYPE VARCHAR(255);
ALTER TABLE bank      ALTER COLUMN phone_number TYPE VARCHAR(255);
ALTER TABLE party     ALTER COLUMN phone_number TYPE VARCHAR(255);

ALTER TABLE firm ADD COLUMN IF NOT EXISTS email VARCHAR(120) DEFAULT NULL;
-- SAC printed on the firm's dalali bills; NULL = 996111 (commission on wholesale trade).
ALTER TABLE firm ADD COLUMN IF NOT EXISTS sac_code VARCHAR(8) DEFAULT NULL;

ALTER TABLE firm_bank ADD COLUMN IF NOT EXISTS account_number VARCHAR(40)  DEFAULT NULL;
ALTER TABLE firm_bank ADD COLUMN IF NOT EXISTS account_type   VARCHAR(30)  DEFAULT NULL;
ALTER TABLE firm_bank ADD COLUMN IF NOT EXISTS ifsc           VARCHAR(15)  DEFAULT NULL;
ALTER TABLE firm_bank ADD COLUMN IF NOT EXISTS branch         VARCHAR(120) DEFAULT NULL;

ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS billing_firm_id      INTEGER REFERENCES firm(id);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS billing_firm_bank_id INTEGER REFERENCES firm_bank(id);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS bill_date            DATE;
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS invoice_number       VARCHAR(30);
-- NULL = an old bill whose GST was typed in by hand (gst_addition); 0 = no GST.
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS gst_rate             NUMERIC(5,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS place_of_supply      VARCHAR(2);   -- GST state code, e.g. '24'
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS taxable_amount       NUMERIC(14,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS cgst_amount          NUMERIC(14,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS sgst_amount          NUMERIC(14,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS igst_amount          NUMERIC(14,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS round_off            NUMERIC(8,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS grand_total          NUMERIC(14,2);
ALTER TABLE dalali_entry ADD COLUMN IF NOT EXISTS sac_code             VARCHAR(8);

CREATE INDEX IF NOT EXISTS ix_dalali_entry_billing_firm ON dalali_entry (billing_firm_id, bill_date);

COMMENT ON COLUMN firm.email                     IS 'Printed on the dalali tax invoice; optional';
COMMENT ON COLUMN firm_bank.account_number       IS 'Printed under Bank Details on the dalali tax invoice';
COMMENT ON COLUMN dalali_entry.billing_firm_id   IS 'Firm the dalali bill is raised from (replaces the ₹1 receiver payment)';
COMMENT ON COLUMN dalali_entry.gst_rate          IS 'GST % chosen on the bill (18 / 5 / 0); NULL = legacy manual gst_addition';
COMMENT ON COLUMN dalali_entry.grand_total       IS 'Invoice grand total, frozen when the entry was saved';

COMMIT;
