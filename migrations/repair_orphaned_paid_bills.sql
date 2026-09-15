-- Fix #8 DATA CORRECTION (Sept 2026): reopen imported bills the client
-- confirmed are NOT actually paid.
--
-- Scope: register_entry rows with status='F' but NO memo_bills row (imported
-- historical bills marked settled with no memo behind them — 111 bills across
-- SUR SHYAM FASHION / LIFESTYLE SAREES -> VIJAI BROTHERS & KAILASH NATH).
-- The client explicitly asked for these to be marked UNPAID, so this resets
-- them to status='N' and clears gr_amount/deduction/partial_amount.
--
-- SAFETY:
--   * Runs in one transaction — all-or-nothing.
--   * Backs the exact rows up first; the CREATE TABLE fails (aborting the whole
--     script) if a prior run's backup already exists, so it can't double-run.
--   * Reversible — see the restore query at the bottom.
--
-- PREVIEW FIRST (read-only) to re-confirm the rows before running this file:
--   SELECT re.id, re.bill_number, s.name AS supplier, p.name AS party, re.amount
--   FROM register_entry re
--   LEFT JOIN supplier s ON s.id = re.supplier_id
--   LEFT JOIN party   p ON p.id = re.party_id
--   WHERE re.status = 'F'
--     AND NOT EXISTS (SELECT 1 FROM memo_bills mb WHERE mb.bill_id = re.id)
--   ORDER BY re.id;
--
-- RUN: psql -U ... -d ... -f migrations/repair_orphaned_paid_bills.sql

BEGIN;

-- 1. Snapshot the exact rows about to change (aborts if backup already exists).
CREATE TABLE register_entry_orphan_bak_20260915 AS
SELECT re.*
FROM register_entry re
WHERE re.status = 'F'
  AND NOT EXISTS (SELECT 1 FROM memo_bills mb WHERE mb.bill_id = re.id);

-- 2. Reset the backed-up bills to unpaid, clearing memo-derived amounts.
UPDATE register_entry
SET status = 'N', gr_amount = 0, deduction = 0, partial_amount = 0
WHERE id IN (SELECT id FROM register_entry_orphan_bak_20260915);

-- 3. Report: rows changed, and remaining 'F'-with-no-memo bills (must be 0).
SELECT (SELECT count(*) FROM register_entry_orphan_bak_20260915) AS reopened,
       (SELECT count(*) FROM register_entry re
          WHERE re.status = 'F'
            AND NOT EXISTS (SELECT 1 FROM memo_bills mb WHERE mb.bill_id = re.id)
       ) AS remaining;

COMMIT;

-- TO UNDO (restore the original status/amounts from the backup):
--   UPDATE register_entry re
--   SET status = b.status, gr_amount = b.gr_amount,
--       deduction = b.deduction, partial_amount = b.partial_amount
--   FROM register_entry_orphan_bak_20260915 b
--   WHERE re.id = b.id;
