-- Add gst_default column to supplier table with default value of 5.0
ALTER TABLE supplier ADD COLUMN IF NOT EXISTS gst_default DECIMAL DEFAULT 5.0;

-- Update comment to explain the purpose of this change
-- COMMENT ON COLUMN supplier.gst_default IS 'Default GST percentage value for the supplier (5%, 12%, or other values like 4.762)';

-- Add new columns to memo_entry table
ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS parent_dalali_id INT REFERENCES dalali_entry(id);
ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS parent_memo_id INT REFERENCES memo_entry(id);
ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS memo_type VARCHAR(20) CHECK (memo_type IN ('Full', 'Part', 'Payment Settlement', 'Dalali Settlement'));

ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS less_gst_percentage DECIMAL;
ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS less_gst INT DEFAULT 0;
ALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS commision INT DEFAULT 0;

-- Add comments to explain the purpose of these new columns
-- COMMENT ON COLUMN memo_entry.parent_dalali_id IS 'To be a foreign key in the future, references dalali entry';
-- COMMENT ON COLUMN memo_entry.parent_memo_id IS 'References parent memo entry for linked memos';
-- COMMENT ON COLUMN memo_entry.memo_type IS 'Type of memo: Full, Part, Payment Settlement, Dalali Settlement';
-- COMMENT ON COLUMN memo_entry.less_gst IS 'Amount with GST removed';
-- COMMENT ON COLUMN memo_entry.commision IS 'Commission amount calculated from less_gst';



