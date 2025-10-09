"""
Elite AI Receptionist - Logger Utility
--------------------------------------
Provides structured, color-coded, multi-destination logging.
- Console (with colors)
- File logs
- Optional SQLite logging
- JSON formatting for external log systems
"""

import logging
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# -------------------------------
# Setup file logging directory
# -------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# -------------------------------
# Color codes for console logs
# -------------------------------
COLORS = {
    "INFO": "\033[94m",    # Blue
    "SUCCESS": "\033[92m", # Green
    "WARNING": "\033[93m", # Yellow
    "ERROR": "\033[91m",   # Red
    "ENDC": "\033[0m"      # Reset
}

class EliteLogger:
    def __init__(self, db_path="receptionist.db", log_file="logs/receptionist.log"):
        # File handler setup
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Optional DB logging
        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_db()
        except Exception as e:
            self.conn = None
            print(f"[Logger] DB logging disabled: {e}")

    # -------------------------------
    # Init SQLite table for logs
    # -------------------------------
    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY,
                level TEXT,
                message TEXT,
                client_id TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    # -------------------------------
    # Core logging method
    # -------------------------------
    def _log(self, level, message, client_id=None, context=None):
        # Timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Console with color
        color = COLORS.get(level, COLORS["INFO"])
        print(f"{color}{timestamp} | {level} | {message}{COLORS['ENDC']}")

        # File logging
        logging.log(getattr(logging, level, logging.INFO), message)

        # DB logging
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO system_logs (level, message, client_id, context) VALUES (?, ?, ?, ?)",
                (level, message, client_id, json.dumps(context) if context else None)
            )
            self.conn.commit()

        # JSON log output (for external systems)
        return {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "client_id": client_id,
            "context": context
        }

    # -------------------------------
    # Public methods
    # -------------------------------
    def info(self, message, client_id=None, context=None):
        return self._log("INFO", message, client_id, context)

    def success(self, message, client_id=None, context=None):
        return self._log("SUCCESS", message, client_id, context)

    def warning(self, message, client_id=None, context=None):
        return self._log("WARNING", message, client_id, context)

    def error(self, message, client_id=None, context=None):
        return self._log("ERROR", message, client_id, context)


# -------------------------------
# Example usage
# -------------------------------
if __name__ == "__main__":
    logger = EliteLogger()

    logger.info("System initialized")
    logger.success("Lead captured successfully", client_id="demo_dentist", context={"lead_value": 5000})
    logger.warning("Email inbox delayed", client_id="demo_realtor")
    logger.error("Twilio call failed", client_id="demo_dentist", context={"error_code": 401})
