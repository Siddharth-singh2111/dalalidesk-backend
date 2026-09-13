-- Credit/Debit Note entity (Sept 2026 batch #2, item 5).
-- A standalone note recorded against a supplier<->party account (not tied to a
-- single bill). A Credit note reduces the party's outstanding; a Debit note
-- increases it. Shown in the Khata report.
-- Run once against your PostgreSQL database, e.g.:
--   psql -U ... -d ... -f migrations/add_credit_debit_note.sql

CREATE TABLE IF NOT EXISTS credit_debit_note (
    id               SERIAL PRIMARY KEY,
    note_type        VARCHAR(6) NOT NULL CHECK (note_type IN ('Credit', 'Debit')),
    note_number      INT,
    note_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    amount           INT NOT NULL,
    supplier_id      INT NOT NULL REFERENCES supplier(id),
    party_id         INT NOT NULL REFERENCES party(id),
    remark           VARCHAR(300),
    created_by       BIGINT REFERENCES users(id),
    last_updated_by  BIGINT REFERENCES users(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE credit_debit_note IS 'Standalone credit/debit notes against a supplier-party account (Sept 2026).';

-- Access control: without these rows every credit_debit_note route returns 403.
INSERT INTO permissions (role, resource, can_create, can_read, can_update, can_delete) VALUES
    ('admin', 'credit_debit_note', TRUE, TRUE, TRUE, TRUE),
    ('user',  'credit_debit_note', TRUE, TRUE, TRUE, FALSE)
ON CONFLICT (role, resource) DO NOTHING;
