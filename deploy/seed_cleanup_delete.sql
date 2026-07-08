-- ============================================================
-- STEP 2 — DELETE PRE-SEEDED TRANSACTIONAL DATA
--
-- !!! TAKE A BACKUP FIRST — NON-NEGOTIABLE !!!
--   pg_dump "$DATABASE_URL" -Fc -f backup_before_seed_cleanup.dump
--
-- Deletes register entries, memos, dalali entries, order forms and
-- all their payments/bills created BEFORE the cutoff timestamp.
-- KEEPS: suppliers, parties, banks, firms, items, users, permissions.
--
-- Run with an explicit cutoff (the handover moment — everything
-- created before it is seed data, everything after is the client's):
--   psql "$DATABASE_URL" -v cutoff='2026-06-11 00:00:00' -f seed_cleanup_delete.sql
--
-- The script ABORTS (nothing deleted) if any post-cutoff (client)
-- record references a pre-cutoff (seed) entry, so it cannot
-- silently break client data.
-- ============================================================

\set ON_ERROR_STOP on

BEGIN;

-- Make the cutoff visible inside DO blocks (psql :variables don't
-- interpolate there); local to this transaction only.
SELECT set_config('cleanup.cutoff', :'cutoff', true);

-- Seed id sets, based on the cutoff
CREATE TEMP TABLE seed_re AS SELECT id FROM register_entry WHERE created_at < :'cutoff'::timestamptz;
CREATE TEMP TABLE seed_me AS SELECT id FROM memo_entry     WHERE created_at < :'cutoff'::timestamptz;
CREATE TEMP TABLE seed_de AS SELECT id FROM dalali_entry   WHERE created_at < :'cutoff'::timestamptz;
CREATE TEMP TABLE seed_of AS SELECT id FROM order_form     WHERE created_at < :'cutoff'::timestamptz;

-- ---- SAFETY CHECKS: abort if client data points at seed data ----
DO $$
DECLARE n bigint;
BEGIN
    SELECT count(*) INTO n FROM memo_bills mb
    WHERE mb.bill_id IN (SELECT id FROM seed_re)
      AND mb.memo_id NOT IN (SELECT id FROM seed_me);
    IF n > 0 THEN RAISE EXCEPTION 'ABORT: % client memo_bills reference seed register entries — manual review needed', n; END IF;

    SELECT count(*) INTO n FROM memo_entry me
    WHERE me.parent_memo_id IN (SELECT id FROM seed_me)
      AND me.id NOT IN (SELECT id FROM seed_me);
    IF n > 0 THEN RAISE EXCEPTION 'ABORT: % client memos have a seed parent memo — manual review needed', n; END IF;

    SELECT count(*) INTO n FROM part_payments pp
    WHERE (pp.memo_id IN (SELECT id FROM seed_me) OR pp.use_memo_id IN (SELECT id FROM seed_me))
      AND pp.created_at >= current_setting('cleanup.cutoff')::timestamptz;
    IF n > 0 THEN RAISE EXCEPTION 'ABORT: % client part_payments reference seed memos — manual review needed', n; END IF;

    SELECT count(*) INTO n FROM dalali_bills db
    WHERE db.dalali_id IN (SELECT id FROM seed_de)
      AND db.memo_id NOT IN (SELECT id FROM seed_me);
    IF n > 0 THEN RAISE EXCEPTION 'ABORT: % client dalali_bills reference seed dalali entries — manual review needed', n; END IF;

    SELECT count(*) INTO n FROM part_dalali pd
    WHERE (pd.dalali_id IN (SELECT id FROM seed_de) OR pd.use_dalali_id IN (SELECT id FROM seed_de))
      AND pd.created_at >= current_setting('cleanup.cutoff')::timestamptz;
    IF n > 0 THEN RAISE EXCEPTION 'ABORT: % client part_dalali reference seed dalali entries — manual review needed', n; END IF;
END $$;

-- ---- DELETE, children first (FK-safe order) ----
DELETE FROM tds_details              WHERE dalali_id IN (SELECT id FROM seed_de);
DELETE FROM dalali_receiver_payments WHERE dalali_id IN (SELECT id FROM seed_de);
DELETE FROM dalali_sender_payments   WHERE dalali_id IN (SELECT id FROM seed_de);
DELETE FROM part_dalali              WHERE dalali_id IN (SELECT id FROM seed_de) OR use_dalali_id IN (SELECT id FROM seed_de);
DELETE FROM dalali_bills             WHERE dalali_id IN (SELECT id FROM seed_de) OR memo_id IN (SELECT id FROM seed_me);
DELETE FROM memo_dalali_payments     WHERE memo_id   IN (SELECT id FROM seed_me);
DELETE FROM part_payments            WHERE memo_id   IN (SELECT id FROM seed_me) OR use_memo_id IN (SELECT id FROM seed_me);
DELETE FROM memo_payments            WHERE memo_id   IN (SELECT id FROM seed_me);
DELETE FROM memo_bills               WHERE memo_id   IN (SELECT id FROM seed_me) OR bill_id IN (SELECT id FROM seed_re);
DELETE FROM item_entry               WHERE register_entry_id IN (SELECT id FROM seed_re);
DELETE FROM memo_entry               WHERE id IN (SELECT id FROM seed_me);
DELETE FROM dalali_entry             WHERE id IN (SELECT id FROM seed_de);
DELETE FROM register_entry           WHERE id IN (SELECT id FROM seed_re);
DELETE FROM order_form               WHERE id IN (SELECT id FROM seed_of);

-- ---- REPORT what remains ----
\echo '=== Remaining rows after cleanup ==='
SELECT 'register_entry' AS tbl, count(*) FROM register_entry
UNION ALL SELECT 'memo_entry', count(*) FROM memo_entry
UNION ALL SELECT 'dalali_entry', count(*) FROM dalali_entry
UNION ALL SELECT 'order_form', count(*) FROM order_form;

COMMIT;
\echo 'Seed data cleanup committed.'
