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

-- Add foreign key constraints for audit fields
ALTER TABLE firm ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE firm ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);
ALTER TABLE firm_bank ADD FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE firm_bank ADD FOREIGN KEY (last_updated_by) REFERENCES users(id);

-- Add permission entries for the new entities
INSERT INTO permissions (role, resource, can_create, can_read, can_update, can_delete)
VALUES 
('admin', 'firm', TRUE, TRUE, TRUE, TRUE),
('admin', 'firm_bank', TRUE, TRUE, TRUE, TRUE),
('user', 'firm', FALSE, TRUE, FALSE, FALSE),
('user', 'firm_bank', FALSE, TRUE, FALSE, FALSE),
('admin', 'dalali_entry', TRUE, TRUE, TRUE, TRUE),
('user', 'dalali_entry', FALSE, TRUE, FALSE, FALSE)
ON CONFLICT (role, resource) DO NOTHING;
