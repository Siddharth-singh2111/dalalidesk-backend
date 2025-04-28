-- Original tables and sequences with audit fields
CREATE SEQUENCE supplier_seq;

CREATE TABLE supplier (
    id INT DEFAULT NEXTVAL ('supplier_seq') PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(300),
    phone_number VARCHAR(20),
    city VARCHAR(20) CHECK (city IN ('Bangalore', 'Jaipur', 'Kolkata', 'Surat', 'Varanasi', 'Belgaum', 'Mumbai', 'Delhi', 'Mau')),
    gst_default DECIMAL DEFAULT 5.0,
    UNIQUE (name),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE party_seq;

CREATE TABLE party (
    id INT DEFAULT NEXTVAL ('party_seq') PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(300),
    phone_number VARCHAR(20),
    UNIQUE (name),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE bank_seq;

CREATE TABLE bank (
    id INT DEFAULT NEXTVAL ('bank_seq') PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(300),
    phone_number VARCHAR(20),
    UNIQUE (name),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE Transport_seq;

CREATE TABLE Transport (
    id INT DEFAULT NEXTVAL ('Transport_seq') PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(300),
    phone_number VARCHAR(20),
    UNIQUE (name),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE register_entry_seq;

CREATE TABLE register_entry (
    id INT DEFAULT NEXTVAL ('register_entry_seq') PRIMARY KEY,
    supplier_id INT,
    party_id INT, 
    register_date TIMESTAMP(0),
    amount INT,
    bill_number INT,
    gr_amount INT DEFAULT 0,
    deduction INT DEFAULT 0,
    status VARCHAR(2) DEFAULT 'N',
    partial_amount INT DEFAULT 0,
    UNIQUE (bill_number, supplier_id, party_id, register_date),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (party_id) REFERENCES party(id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(id)
);

CREATE SEQUENCE memo_entry_seq;

CREATE TABLE memo_entry(
    id INT DEFAULT NEXTVAL ('memo_entry_seq') PRIMARY KEY,
    memo_number INT,
    supplier_id INT,
    party_id INT, 
    register_date TIMESTAMP(0),
    amount INT default 0,
    gr_amount INT default 0,
    deduction INT default 0,
    discount INT DEFAULT 0,
    other_deduction INT DEFAULT 0,
    rate_difference INT DEFAULT 0,
    gr_amount_details TEXT,
    discount_details TEXT,
    other_deduction_details TEXT,
    rate_difference_details TEXT,
    notes TEXT,
    parent_dalali_id INT,
    parent_memo_id INT,
    memo_type VARCHAR(20) CHECK (memo_type IN ('Full', 'Part', 'Payment Settlement', 'Dalali Settlement')) DEFAULT 'Full',
    less_gst_percentage DECIMAL,
    less_gst INT DEFAULT 0,
    commision INT DEFAULT 0,
    UNIQUE (memo_number, party_id, supplier_id, register_date),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (party_id) REFERENCES party(id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(id),
    FOREIGN KEY (parent_memo_id) REFERENCES memo_entry(id)
);

CREATE SEQUENCE memo_payments_seq;

CREATE TABLE memo_payments(
    id INT DEFAULT NEXTVAL ('memo_payments_seq') PRIMARY KEY,
    memo_id INT, 
    bank_id INT,
    cheque_number INT,
    amount INT DEFAULT 0,
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (memo_id) REFERENCES memo_entry(id),
    FOREIGN KEY (bank_id) REFERENCES bank(id)
);

CREATE SEQUENCE memo_bills_seq;

CREATE TABLE memo_bills (
    id INT DEFAULT NEXTVAL ('memo_bills_seq') PRIMARY KEY,
    memo_id INT, 
    bill_id INT,
    type VARCHAR(2),
    amount INT,
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (memo_id) REFERENCES memo_entry(id),
    FOREIGN KEY (bill_id) REFERENCES register_entry(id)
);

CREATE SEQUENCE part_payment_seq;

CREATE TABLE part_payments(
    id INT DEFAULT nextval('part_payment_seq') PRIMARY KEY,
    supplier_id INT,
    party_id INT,
    memo_id INT,
    used boolean DEFAULT false,
    use_memo_id INT,
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (party_id) REFERENCES party(id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(id),
    FOREIGN KEY (memo_id) REFERENCES memo_entry(id),
    FOREIGN KEY (use_memo_id) REFERENCES memo_entry(id)
);

CREATE SEQUENCE order_form_seq;

CREATE TABLE order_form(
    id INT DEFAULT nextval('order_form_seq') PRIMARY KEY,
    supplier_id INT,
    party_id INT,
    order_form_number INT,
    register_date TIMESTAMP(0),
    status VARCHAR,
    delivered boolean DEFAULT false,
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (party_id) REFERENCES party(id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(id)
);

CREATE SEQUENCE item_seq;

CREATE TABLE item (
    id INT DEFAULT nextval('item_seq') PRIMARY KEY,
    supplier_id INT,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(255) DEFAULT 'N/A',
    UNIQUE (supplier_id, name, color),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (supplier_id) REFERENCES supplier(id)
);

CREATE SEQUENCE item_entry_seq;

CREATE TABLE item_entry (
    id INT DEFAULT nextval('item_entry_seq') PRIMARY KEY,
    register_entry_id INT,
    item_id INT,
    quantity INT,
    rate INT,
    UNIQUE(register_entry_id, item_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (register_entry_id) REFERENCES register_entry(id),
    FOREIGN KEY (item_id) REFERENCES item(id)
);

CREATE SEQUENCE remote_query_logs_seq;

CREATE TABLE remote_query_logs (
    id INT DEFAULT nextval('remote_query_logs_seq') PRIMARY KEY,
    query_text TEXT NOT NULL,
    http_response_status INTEGER,
    query_status VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE TABLE last_update(
    updated_at TIMESTAMP(0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE TABLE stack(
    query VARCHAR(500),
    val VARCHAR(500),
    updated_at TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

-- Add sequences and tables for Firms and Firm Banks
CREATE SEQUENCE firm_seq;

CREATE TABLE firm (
    id INT DEFAULT NEXTVAL ('firm_seq') PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(300),
    phone_number VARCHAR(20),
    UNIQUE (name),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE firm_bank_seq;

CREATE TABLE firm_bank (
    id INT DEFAULT NEXTVAL ('firm_bank_seq') PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(300),
    phone_number VARCHAR(20),
    firm_id INT NOT NULL,
    UNIQUE (name, firm_id),
    last_update TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    FOREIGN KEY (firm_id) REFERENCES firm(id)
);

-- Audit trail schemaALTER TABLE memo_entry ADD COLUMN IF NOT EXISTS less_gst_percentage DECIMAL;
CREATE SEQUENCE IF NOT EXISTS users_seq;
CREATE TABLE IF NOT EXISTS users (
    id BIGINT DEFAULT NEXTVAL('users_seq') PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE IF NOT EXISTS permissions_seq;
CREATE TABLE IF NOT EXISTS permissions (
    id BIGINT DEFAULT NEXTVAL('permissions_seq') PRIMARY KEY,
    role TEXT NOT NULL,
    resource TEXT NOT NULL,
    can_create BOOLEAN DEFAULT FALSE,
    can_read BOOLEAN DEFAULT TRUE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    UNIQUE(role, resource),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT
);

CREATE SEQUENCE IF NOT EXISTS audit_log_seq;
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT DEFAULT NEXTVAL('audit_log_seq') PRIMARY KEY,
    user_id BIGINT,
    table_name TEXT NOT NULL,
    record_id BIGINT NOT NULL,
    action TEXT NOT NULL, -- INSERT, UPDATE, DELETE
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changes JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Add foreign key constraints for audit fields
ALTER TABLE supplier ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE supplier ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE party ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE party ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE bank ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE bank ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE Transport ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE Transport ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE register_entry ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE register_entry ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE memo_entry ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE memo_entry ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE memo_payments ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE memo_payments ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE memo_bills ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE memo_bills ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE part_payments ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE part_payments ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE order_form ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE order_form ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE item ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE item ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE item_entry ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE item_entry ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE remote_query_logs ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE remote_query_logs ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE last_update ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE last_update ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE stack ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE stack ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE firm ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE firm ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE firm_bank ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE firm_bank ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE permissions ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE permissions ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);

-- Memo dalali payments table
CREATE TABLE IF NOT EXISTS memo_dalali_payments (
    id SERIAL PRIMARY KEY,
    memo_id INTEGER NOT NULL REFERENCES memo_entry(id),
    is_paid BOOLEAN DEFAULT FALSE,
    paid_amount NUMERIC(10, 2) DEFAULT 0,
    remark TEXT,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT,
    UNIQUE(memo_id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (last_updated_by) REFERENCES users(id)
);

-- Default admin user
INSERT INTO users (username, password_hash, full_name, role, is_active)
SELECT 'admin', '$2b$12$1xxxxxxxxxxxxxxxxxxxxuZLbwxnpY0o58unSvIPxddLxGystU.', 'Administrator', 'admin', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'admin'
);

-- Default permissions
INSERT INTO permissions (role, resource, can_create, can_read, can_update, can_delete)
VALUES 
('admin', 'users', TRUE, TRUE, TRUE, TRUE),
('admin', 'supplier', TRUE, TRUE, TRUE, TRUE),
('admin', 'party', TRUE, TRUE, TRUE, TRUE),
('admin', 'bank', TRUE, TRUE, TRUE, TRUE),
('admin', 'transport', TRUE, TRUE, TRUE, TRUE),
('admin', 'register_entry', TRUE, TRUE, TRUE, TRUE),
('admin', 'memo_entry', TRUE, TRUE, TRUE, TRUE),
('admin', 'order_form', TRUE, TRUE, TRUE, TRUE),
('admin', 'item', TRUE, TRUE, TRUE, TRUE),
('admin', 'item_entry', TRUE, TRUE, TRUE, TRUE),
('admin', 'audit_log', FALSE, TRUE, FALSE, FALSE),
('admin', 'firm', TRUE, TRUE, TRUE, TRUE),
('admin', 'firm_bank', TRUE, TRUE, TRUE, TRUE),
('user', 'supplier', FALSE, TRUE, FALSE, FALSE),
('user', 'party', FALSE, TRUE, FALSE, FALSE),
('user', 'bank', FALSE, TRUE, FALSE, FALSE),
('user', 'transport', FALSE, TRUE, FALSE, FALSE),
('user', 'register_entry', TRUE, TRUE, TRUE, FALSE),
('user', 'memo_entry', TRUE, TRUE, TRUE, FALSE),
('user', 'order_form', TRUE, TRUE, TRUE, FALSE),
('user', 'item', FALSE, TRUE, FALSE, FALSE),
('user', 'item_entry', TRUE, TRUE, TRUE, FALSE),
('user', 'firm', FALSE, TRUE, FALSE, FALSE),
('user', 'firm_bank', FALSE, TRUE, FALSE, FALSE)
ON CONFLICT (role, resource) DO NOTHING;
