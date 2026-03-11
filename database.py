# database.py
# PURF Utopia — Trillion-Request Audit Grade

import sqlite3
import json
import uuid
from datetime import datetime

DB_NAME = "purf_utopia.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Submissions Table (Raw Input)
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id TEXT PRIMARY KEY, founder_id TEXT, text TEXT, timestamp TEXT)''')
    
    # 2. Snapshots Table (The Audit Trail)
    # We use a try/except block to handle schema migration (adding the new column)
    # in case you have an old DB file lying around.
    c.execute('''CREATE TABLE IF NOT EXISTS snapshots
                 (submission_id TEXT, 
                  normalized TEXT, 
                  canonical TEXT, 
                  mapped TEXT, 
                  verdict TEXT, 
                  ruleset_version TEXT,
                  explanation_version TEXT, 
                  timestamp TEXT)''')
                  
    # Migration check: Ensure explanation_version column exists
    try:
        c.execute("ALTER TABLE snapshots ADD COLUMN explanation_version TEXT")
    except sqlite3.OperationalError:
        pass # Column likely already exists

    conn.commit()
    conn.close()

def save_submission(founder_id, text):
    submission_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO submissions VALUES (?, ?, ?, ?)", 
              (submission_id, founder_id, text, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return submission_id

def save_snapshot(submission_id, normalized, canonical, mapped, verdict, ruleset_version, explanation_version=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # We store the dicts as JSON strings so they are queryable text later
    c.execute("INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (submission_id, 
               json.dumps(normalized), 
               json.dumps(canonical), 
               json.dumps(mapped), 
               json.dumps(verdict), 
               ruleset_version,
               explanation_version,
               datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Initialize on module load
init_db()
