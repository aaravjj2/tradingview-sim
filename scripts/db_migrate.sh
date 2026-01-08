#!/bin/bash
#
# Database Migration Script
#
# Applies all migrations in db/migrations/ to the trading database.
#
# Usage:
#   ./scripts/db_migrate.sh [--db-path=trading_data.db]
#

set -e

# Parse arguments
DB_PATH="trading_data.db"
for arg in "$@"; do
    case $arg in
        --db-path=*)
            DB_PATH="${arg#*=}"
            ;;
    esac
done

echo "=========================================="
echo "Database Migration"
echo "=========================================="
echo "Database: $DB_PATH"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MIGRATIONS_DIR="$PROJECT_ROOT/db/migrations"

# Run migrations using Python sqlite3 module
python3 << EOF
import sqlite3
import os
from pathlib import Path

db_path = "$DB_PATH"
migrations_dir = "$MIGRATIONS_DIR"

# Create database connection
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create migrations tracking table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TEXT DEFAULT (datetime('now'))
    )
""")
conn.commit()

print()
print("Checking for pending migrations...")
print()

# Get list of migration files
migrations_path = Path(migrations_dir)
if not migrations_path.exists():
    print(f"ERROR: Migrations directory not found: {migrations_dir}")
    exit(1)

migration_files = sorted(migrations_path.glob("*.sql"))

if not migration_files:
    print("No migration files found.")
    exit(0)

applied_count = 0

for migration_file in migration_files:
    version = migration_file.stem  # filename without extension
    
    # Check if already applied
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=?", (version,))
    already_applied = cursor.fetchone()[0]
    
    if already_applied == 0:
        print(f"Applying migration: {migration_file.name}")
        
        try:
            # Read and execute migration
            sql = migration_file.read_text()
            cursor.executescript(sql)
            
            # Record migration
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            conn.commit()
            
            print("  ✓ Applied successfully")
            applied_count += 1
        except Exception as e:
            print(f"  ✗ Migration failed: {e}")
            exit(1)
    else:
        print(f"Skipping: {migration_file.name} (already applied)")

print()
print("==========================================")
print("Migration complete!")
print(f"Applied: {applied_count} new migration(s)")
print("==========================================")

# Show current schema versions
print()
print("Current schema versions:")
cursor.execute("SELECT version, applied_at FROM schema_migrations ORDER BY version")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
EOF
