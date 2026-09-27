-- Out-station memo series (Sept 2026): memos for suppliers NOT based in Surat
-- get their own independent numbering, shown with an "OS-" prefix (OS-1, OS-2,
-- ...). Surat suppliers keep the existing normal series unchanged.
--
-- A memo is flagged out-station at creation time from the supplier's city, so
-- past memos are unaffected (all default to FALSE = normal series) and the OS-
-- series starts fresh from OS-1 going forward.
--
-- Run once against your PostgreSQL database:
--   psql -U ... -d ... -f migrations/add_memo_out_station.sql

ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS is_out_station BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN memo_entry.is_out_station IS 'TRUE for memos of non-Surat (out-station) suppliers; they use a separate OS- numbering series';
