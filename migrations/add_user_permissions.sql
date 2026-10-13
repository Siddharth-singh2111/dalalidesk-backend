-- Per-user permissions (Oct 2026). The permissions table is role-based
-- (role, resource, CRUD). To let an admin grant feature access per individual
-- user from the admin panel, this adds a per-user matrix. A row overrides the
-- role default for that user+resource; User.has_permission prefers these rows
-- when a user has any, and admins always have full access regardless.
-- Run once:
--   psql -U ... -d ... -f migrations/add_user_permissions.sql

CREATE TABLE IF NOT EXISTS user_permissions (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource    TEXT NOT NULL,
    can_create  BOOLEAN DEFAULT FALSE,
    can_read    BOOLEAN DEFAULT FALSE,
    can_update  BOOLEAN DEFAULT FALSE,
    can_delete  BOOLEAN DEFAULT FALSE,
    UNIQUE (user_id, resource),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      BIGINT REFERENCES users(id),
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_by BIGINT REFERENCES users(id)
);

-- If the table already existed from an earlier run without created_by, add it.
ALTER TABLE user_permissions ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id);

COMMENT ON TABLE user_permissions IS 'Per-user feature permissions, managed from the admin panel (Oct 2026).';

-- The users table has last_updated_by but no created_by, which the execute_query
-- audit layer expects on INSERT — so creating a user through the API failed.
-- Add it for consistency with the other tables.
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id);
