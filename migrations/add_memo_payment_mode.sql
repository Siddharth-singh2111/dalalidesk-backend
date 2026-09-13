-- Add payment_mode to memo_payments (Sept 2026 batch #3).
-- Lets a memo payment record how it was paid: Cheque / Cash / RTGS / NEFT.
-- Existing rows and older clients default to 'Cheque'.
-- Run once against your PostgreSQL database, e.g.:
--   psql -U ... -d ... -f migrations/add_memo_payment_mode.sql

ALTER TABLE memo_payments ADD COLUMN IF NOT EXISTS payment_mode VARCHAR(20) DEFAULT 'Cheque';

COMMENT ON COLUMN memo_payments.payment_mode IS 'How the payment was made: Cheque / Cash / RTGS / NEFT (default Cheque)';
