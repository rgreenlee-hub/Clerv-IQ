"""
Migration script for Elite Receptionist DB
- Creates base + multi-client schema
- Adds client_id to legacy log tables (if missing)
"""

import sqlite3

DB_PATH = "receptionist.db"

def add_column_if_not_exists(cursor, table, column, col_type="TEXT"):
    """Adds a column to a table if it does not already exist"""
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [info[1] for info in cursor.fetchall()]
    if column not in columns:
        print(f"Adding {column} to {table}...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
    else:
        print(f"{column} already exists in {table}.")

def create_base_tables(cursor):
    """Create legacy tables if they don’t exist yet"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        timestamp DATETIME,
        content TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        timestamp DATETIME,
        subject TEXT,
        body TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sms_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        timestamp DATETIME,
        content TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        name TEXT,
        email TEXT,
        phone TEXT,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pipeline_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        stage TEXT,
        lead_id INTEGER,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )
    """)

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- Base legacy tables ---
    create_base_tables(cursor)

    # --- New schema for multi-client ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        stripe_customer_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS twilio_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        account_sid TEXT NOT NULL,
        auth_token TEXT NOT NULL,
        phone_number TEXT NOT NULL UNIQUE,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ghl_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        location_id TEXT NOT NULL,
        api_key TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analytics_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        leads_captured INTEGER DEFAULT 0,
        calls_handled INTEGER DEFAULT 0,
        sms_handled INTEGER DEFAULT 0,
        report_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
    )
    """)

    # --- Ensure client_id exists on legacy tables ---
    legacy_tables = ["call_logs", "email_logs", "sms_logs", "leads", "pipeline_leads"]
    for table in legacy_tables:
        add_column_if_not_exists(cursor, table, "client_id")

    conn.commit()
    conn.close()
    print("✅ Migration complete — DB is ready for multi-client support.")

if __name__ == "__main__":
    migrate()
    print("Database created at:", DB_PATH)
