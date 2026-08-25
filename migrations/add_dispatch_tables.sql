-- Digitises the physical Dispatch Pad (G. Das & Company / D.M. Agency).
-- dispatch      = one pad slip (party + date + serial), recorded by a user
-- dispatch_bill = one row on the slip (a bill + L.R. No. + transport)
--
-- Local dev creates these automatically via SQLAlchemy db.create_all(); this
-- file is for applying the same schema to production. Idempotent.

CREATE TABLE IF NOT EXISTS dispatch (
    id               SERIAL PRIMARY KEY,
    serial_number    INT,
    party_id         INT NOT NULL REFERENCES party(id),
    dispatch_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    notes            VARCHAR(300),
    created_by       BIGINT REFERENCES users(id),
    last_updated_by  BIGINT REFERENCES users(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dispatch_bill (
    id                SERIAL PRIMARY KEY,
    dispatch_id       INT NOT NULL REFERENCES dispatch(id) ON DELETE CASCADE,
    register_entry_id INT REFERENCES register_entry(id),
    bill_number       INT,
    bill_date         DATE,
    supplier_id       INT REFERENCES supplier(id),
    lr_number         VARCHAR(50),
    transport_name    VARCHAR(100),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispatch_date ON dispatch(dispatch_date);
CREATE INDEX IF NOT EXISTS idx_dispatch_party ON dispatch(party_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_bill_dispatch ON dispatch_bill(dispatch_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_bill_transport ON dispatch_bill(transport_name);
