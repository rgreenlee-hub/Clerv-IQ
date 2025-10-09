"""
__init__.py (FIXED)
Package initialization with consistent imports
"""

import os
from Config import CLIENTS
from Analytics import Analytics
from brain import ReceptionistBrain

# Database path at root level
DB_PATH = os.path.join(os.path.dirname(__file__), "receptionist.db")

# Initialize global analytics instance
analytics = Analytics(db_path=DB_PATH)

__all__ = [
    "CLIENTS",
    "Analytics",
    "ReceptionistBrain",
    "analytics",
    "DB_PATH"
]