#!/bin/bash

DB_USER="postgres"
DB_NAME="hca_v2"
BACKUP_FILE="/Users/vaibhavholani/development/business/global_holani_tradelink/backups/backup_17_Apr_2025.sql"

psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
psql -U "$DB_USER" "$DB_NAME" < "$BACKUP_FILE"

echo "Database $DB_NAME restored successfully from $BACKUP_FILE."
