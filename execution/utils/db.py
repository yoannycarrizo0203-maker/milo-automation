import sqlite3
import os
from execution.config import DATABASE_PATH
from execution.utils.logging import logger

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(os.path.dirname(DATABASE_PATH)):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tables
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        thread_id TEXT,
        in_reply_to_id TEXT,
        sender TEXT,
        receiver TEXT,
        body TEXT,
        media TEXT,
        status TEXT,
        type TEXT,
        timestamp DATETIME,
        draft_version INTEGER DEFAULT 1
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        draft_id TEXT,
        reviewer_phone TEXT,
        action TEXT,
        notes TEXT,
        timestamp DATETIME,
        FOREIGN KEY(draft_id) REFERENCES messages(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        event TEXT,
        actor TEXT,
        metadata TEXT,
        timestamp DATETIME
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS thread_controls (
        thread_id TEXT PRIMARY KEY,
        paused BOOLEAN,
        paused_reason TEXT,
        last_updated DATETIME
    )''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized at " + DATABASE_PATH)
