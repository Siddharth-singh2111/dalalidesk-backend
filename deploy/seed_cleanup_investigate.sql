-- ============================================================
-- STEP 1 — INVESTIGATE (100% read-only, safe to run anytime)
-- Run on the production server:
--   psql "$DATABASE_URL" -f seed_cleanup_investigate.sql
-- (or psql -h <host> -U <user> -d <db> -f seed_cleanup_investigate.sql)
--
-- Goal: find the line between pre-seeded demo data and the
-- client's real entries, so we can pick a safe cutoff timestamp.
-- ============================================================

\echo '=== Register entries grouped by creator and month ==='
SELECT created_by,
       u.username,
       date_trunc('month', re.created_at) AS created_month,
       count(*)                           AS entries,
       min(re.created_at)                 AS first_created,
       max(re.created_at)                 AS last_created
FROM register_entry re
LEFT JOIN users u ON u.id = re.created_by
GROUP BY created_by, u.username, date_trunc('month', re.created_at)
ORDER BY created_month, created_by;

\echo '=== Same for memo entries ==='
SELECT created_by, date_trunc('month', created_at) AS created_month, count(*)
FROM memo_entry GROUP BY 1, 2 ORDER BY 2, 1;

\echo '=== Same for dalali entries ==='
SELECT created_by, date_trunc('month', created_at) AS created_month, count(*)
FROM dalali_entry GROUP BY 1, 2 ORDER BY 2, 1;

\echo '=== Same for order forms ==='
SELECT created_by, date_trunc('month', created_at) AS created_month, count(*)
FROM order_form GROUP BY 1, 2 ORDER BY 2, 1;

\echo '=== The specific conflicting entry the client hit ==='
SELECT re.id, re.bill_number, s.name AS supplier, p.name AS party,
       re.register_date, re.amount, re.status, re.created_at, re.created_by
FROM register_entry re
LEFT JOIN supplier s ON s.id = re.supplier_id
LEFT JOIN party p    ON p.id = re.party_id
WHERE re.bill_number = 526;

\echo '=== Totals per table (to know the blast radius) ==='
SELECT 'register_entry' AS tbl, count(*) FROM register_entry
UNION ALL SELECT 'memo_entry', count(*) FROM memo_entry
UNION ALL SELECT 'memo_bills', count(*) FROM memo_bills
UNION ALL SELECT 'memo_payments', count(*) FROM memo_payments
UNION ALL SELECT 'part_payments', count(*) FROM part_payments
UNION ALL SELECT 'item_entry', count(*) FROM item_entry
UNION ALL SELECT 'order_form', count(*) FROM order_form
UNION ALL SELECT 'dalali_entry', count(*) FROM dalali_entry
UNION ALL SELECT 'dalali_bills', count(*) FROM dalali_bills
UNION ALL SELECT 'supplier', count(*) FROM supplier
UNION ALL SELECT 'party', count(*) FROM party;
